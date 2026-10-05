"""
Run OpenRouter models on the golden questions and grade them against the gold answers.

Flow:
  1. run every gold SQL ONCE on the DB -> the correct answers
  2. for each model, one after another (questions in parallel):
       send the prompt (prompt.py) -> extract its SQL -> run it read-only -> compare (grading.py)
  3. save the results CSV after every model, and rebuild the Excel report (make_report.py)
  4. print a scoreboard

Settings, models and question sets live in config.py.

Run:
  uv run python run_models.py --print-prompt 56                # show the exact prompt, no API call
  uv run python run_models.py --models luna --ids 1 25 56      # cheap test run
  uv run python run_models.py --set hardest20 --workers 10     # all models, hardest 20 questions
  uv run python run_models.py --selected                       # only config.SELECTED_MODEL
  uv run python run_models.py                                  # all models, all questions
"""

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from config import (API_KEY, DEFAULT_WORKERS, MODELS, QUESTION_SETS, REPORT_PATH, RESULTS_PATH,
                    SELECTED_MODEL)
from golden_dataset_generator import GOLDEN
from grading import compare, extract_sql, result_json, run_sql
from make_report import build_report, scoreboard
from openrouter import OpenRouter, OutOfCredits
from prompt import SYSTEM_PROMPT, PromptBuilder

NO_USAGE = dict(finish_reason=None, prompt_tokens=None, completion_tokens=None,
                reasoning_tokens=None, cost_usd=None)


def run_gold(questions):
    """Execute every gold query once. Returns {id: {"df", "sql", "json"}}."""
    gold = {}
    for g in questions:
        df, err = run_sql(g["sql"])
        if df is None:
            raise SystemExit(f"Gold SQL for question {g['id']} failed: {err}")
        gold[g["id"]] = dict(df=df, sql=" ".join(g["sql"].split()), json=result_json(df))
    print(f"Ran {len(gold)} gold queries")
    return gold


def answer_one(api, slug, g, gold_df, prompts):
    """Ask one model one question, run its SQL and grade it. Returns the model part of a result row."""
    t0 = time.monotonic()
    try:
        raw, usage = api.chat(slug, SYSTEM_PROMPT, prompts.user_prompt(g["q"]))
    except OutOfCredits:
        raise   # not the model's fault - must not be scored as a wrong answer
    except Exception as e:
        return dict(model_sql="", model_result="", model_n_rows=None, correct=False,
                    reason="api_error", error=f"{type(e).__name__}: {e}"[:300],
                    latency_s=round(time.monotonic() - t0, 2), **NO_USAGE)
    latency = round(time.monotonic() - t0, 2)

    sql = extract_sql(raw)
    if not sql:
        # finish_reason == 'length' means the model ran out of tokens (often while reasoning)
        return dict(model_sql="", model_result="", model_n_rows=None, correct=False,
                    reason="no_sql_in_reply", error=raw[:300], latency_s=latency, **usage)

    df, err = run_sql(sql)
    ok, reason = compare(gold_df, df, ordered=g.get("ordered", False))
    return dict(model_sql=sql, model_result=result_json(df),
                model_n_rows=None if df is None else len(df),
                correct=ok, reason=reason, error=err, latency_s=latency, **usage)


def run_model(api, name, slug, questions, gold, prompts, workers):
    """All questions for one model, printing each result as it finishes. Returns rows in id order."""
    print(f"\n{'=' * 60}\nMODEL: {name}  ({slug})\n{'=' * 60}", flush=True)
    outs, n_ok, t_start = {}, 0, time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(answer_one, api, slug, g, gold[g["id"]]["df"], prompts): g
                   for g in questions}
        for done, fut in enumerate(as_completed(futures), start=1):
            g = futures[fut]
            try:
                out = fut.result()
            except OutOfCredits:
                pool.shutdown(wait=False, cancel_futures=True)
                raise
            outs[g["id"]] = out
            n_ok += out["correct"]
            mark = "OK" if out["correct"] else "XX"
            print(f"  [{done:3}/{len(questions)}  {n_ok} ok  {time.monotonic() - t_start:5.0f}s]"
                  f"  #{g['id']:3} [{g['diff']:6}] {mark}  {out['reason']}"
                  + (f"  ({out['error'][:70]})" if out["error"] else ""), flush=True)

    print(f"\n  SCORE: {n_ok}/{len(questions)} = {100 * n_ok / len(questions):.1f}%")
    return [dict(model=name, slug=slug, id=g["id"], difficulty=g["diff"], categories=",".join(g["cat"]),
                 question=g["q"], gold_sql=gold[g["id"]]["sql"], gold_result=gold[g["id"]]["json"],
                 gold_n_rows=len(gold[g["id"]]["df"]), **outs[g["id"]])
            for g in questions]


def save(rows, results_path, report_path):
    """Write the CSV, then the report. A report bug must never cost a paid-for run."""
    Path(results_path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(results_path, index=False)
    try:
        build_report(results_path, report_path)
    except Exception as e:
        print(f"  (report not built: {e} - rerun `uv run python make_report.py` later)")


def print_scoreboard(rows):
    board = scoreboard(pd.DataFrame(rows))
    cols = [c for c in ["rank", "model", "overall_%", "correct", "total", "easy_%", "medium_%", "hard_%",
                        "brutal_%", "avg_latency_s", "total_cost_usd"] if c in board.columns]
    print(f"\n{'=' * 70}\nSCOREBOARD (execution accuracy)\n{'=' * 70}")
    print(board[cols].to_string(index=False))


def main(models, questions, workers, results_path=RESULTS_PATH, report_path=REPORT_PATH):
    prompts = PromptBuilder()
    gold = run_gold(questions)                                    # 1. correct answers, once
    api = OpenRouter()
    rows = []
    for name, slug in models:                                     # 2. models one by one
        try:
            rows += run_model(api, name, slug, questions, gold, prompts, workers)
        except OutOfCredits as e:
            print(f"\n!! OUT OF CREDITS during {name}: {e}\n"
                  f"!! {name}'s partial answers are discarded so scores stay comparable.\n"
                  f"!! Add credits at https://openrouter.ai/settings/credits, or lower MAX_TOKENS / --workers\n"
                  f"!! (OpenRouter reserves max_tokens x price for every call in flight).", flush=True)
            if rows:
                save(rows, results_path, report_path)
                print(f"!! Finished models kept in {results_path} / {report_path}")
            raise SystemExit(1)
        save(rows, results_path, report_path)                     # 3. after every model

    print_scoreboard(rows)                                        # 4. scoreboard
    print(f"\nAll queries and results saved -> {results_path}\nExcel report -> {report_path}")


def parse_args():
    p = argparse.ArgumentParser(description="Run OpenRouter models on the IPL golden questions")
    p.add_argument("--models", nargs="*", help="substring(s) of model name or slug to run")
    p.add_argument("--selected", action="store_true", help=f"run only the selected model ({SELECTED_MODEL})")
    p.add_argument("--ids", nargs="*", type=int, help="question ids to run")
    p.add_argument("--set", choices=sorted(QUESTION_SETS), help="named question subset to run")
    p.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    p.add_argument("--print-prompt", type=int, metavar="ID", help="print the prompt for one question and exit")
    p.add_argument("--results", default=RESULTS_PATH, help="CSV to write (default: %(default)s)")
    p.add_argument("--report", default=REPORT_PATH, help="Excel report to write (default: %(default)s)")
    return p.parse_args()


def select(args):
    """Apply the CLI filters to GOLDEN and MODELS."""
    wanted = set(args.ids or []) | set(QUESTION_SETS.get(args.set, []))
    questions = [g for g in GOLDEN if not wanted or g["id"] in wanted]
    if args.selected:
        models = [(n, s) for n, s in MODELS if s == SELECTED_MODEL]
    else:
        models = [(n, s) for n, s in MODELS
                  if not args.models or any(k.lower() in (n + s).lower() for k in args.models)]
    return models, questions


if __name__ == "__main__":
    args = parse_args()
    models, questions = select(args)

    if args.print_prompt:
        g = next(g for g in GOLDEN if g["id"] == args.print_prompt)
        print("=== SYSTEM ===\n" + SYSTEM_PROMPT)
        print("\n=== USER ===\n" + PromptBuilder().user_prompt(g["q"]))
    elif not API_KEY:
        print("Missing OPENROUTER_API_KEY - add it to your .env file")
    elif not models or not questions:
        print("Nothing to run - check --models / --ids / --set")
    else:
        print(f"Running {len(questions)} questions x {len(models)} models")
        main(models, questions, args.workers, args.results, args.report)
