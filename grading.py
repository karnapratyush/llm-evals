"""
Everything needed to judge one answer: pull the SQL out of a model reply, run it safely,
and compare its result to the gold result.
"""

import json
import re
import sqlite3
import time

import pandas as pd

from config import DB_PATH, MAX_RESULT_ROWS, SQL_TIMEOUT_S


# ---------- running SQL ----------
def run_sql(sql, db_path=DB_PATH):
    """Run SQL on a read-only connection with a timeout. Returns (DataFrame or None, error message)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    deadline = time.monotonic() + SQL_TIMEOUT_S
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)  # non-zero return aborts
    try:
        return pd.read_sql_query(sql, conn), ""
    except Exception as e:
        return None, "timeout" if time.monotonic() > deadline else str(e)
    finally:
        conn.close()


def result_json(df):
    """Serialise a result (first MAX_RESULT_ROWS rows) for the results CSV."""
    if df is None:
        return ""
    rows = df.head(MAX_RESULT_ROWS).values.tolist()
    return json.dumps({"columns": list(df.columns), "rows": rows}, default=str, ensure_ascii=False)


# ---------- reading the model reply ----------
def extract_sql(raw):
    """Pull the SQL out of a model reply: prefer a ```sql block, else start at SELECT/WITH."""
    if not raw:
        return ""
    text = raw.strip()
    fence = re.search(r"```(?:sql|sqlite)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    m = re.search(r"\b(SELECT|WITH)\b", text, re.IGNORECASE)
    if m:
        text = text[m.start():]
    return text.strip().rstrip(";").strip()


# ---------- comparison (value-based, ignores column names) ----------
def _canon(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "NULL"
    try:
        f = float(v)
        return f"n:{int(f)}" if f.is_integer() else f"n:{round(f, 4)}"
    except (TypeError, ValueError):
        return f"s:{str(v).strip()}"


def compare(gold_df, model_df, ordered=False):
    """
    Returns (correct, reason). Correct when the model returned the same data as gold:
    - column names and column order are ignored; numbers compare numerically (4 decimals)
    - row order is ignored unless the question is ordered
    - one extra or one missing column is tolerated (e.g. name only vs name + count)
    """
    if model_df is None:
        return False, "sql_error"
    if len(gold_df) != len(model_df):
        return False, f"row_count {len(model_df)} vs gold {len(gold_df)}"
    if abs(gold_df.shape[1] - model_df.shape[1]) > 1:
        return False, f"col_count {model_df.shape[1]} vs gold {gold_df.shape[1]}"

    def rows(df):   # each row -> sorted list of canonical values (column order no longer matters)
        return [sorted(_canon(v) for v in r) for r in df.values.tolist()]

    g, m = rows(gold_df), rows(model_df)
    if gold_df.shape[1] == model_df.shape[1]:
        ok = g == m if ordered else sorted(g) == sorted(m)
    else:
        small, large = (g, m) if gold_df.shape[1] < model_df.shape[1] else (m, g)
        if ordered:
            ok = all(set(s) <= set(l) for s, l in zip(small, large))
        else:   # every smaller row must fit inside a different larger row
            unused = list(large)
            ok = True
            for s in small:
                hit = next((l for l in unused if set(s) <= set(l)), None)
                if hit is None:
                    ok = False
                    break
                unused.remove(hit)
    return ok, "match" if ok else "value_mismatch"
