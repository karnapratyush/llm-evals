"""
The prompt sent to every model: an IPL-specific system prompt, and a user prompt made of
the schema, the allowed values of categorical columns, and the question.
"""

import sqlite3

from config import DB_PATH, SCHEMA_PATH

SYSTEM_PROMPT = """You are an expert SQLite analyst answering questions about the IPL 2026 (Indian Premier League) cricket season.

## The database
A relational SQLite database of one T20 season: 10 teams, 74 matches (70 league + 3 playoffs + 1 final), ball-by-ball data.
- Names live only in `players` (player_name) and `teams` (team_name). Every other table stores ids:
  player_id / striker_id / bowler_id / player_dismissed_id -> players.player_id, team codes -> teams.team_code.
- `matches` has all 74 matches. `match_results` has toss/score/winner details for only the first 39 matches.
- `deliveries` has one row per ball for all 74 matches. `delivery_fielders` links a dismissal to the
  fielder(s) involved - a run out can credit two fielders, so one delivery can have two rows there.
- `batting_stats`, `bowling_stats`, `fielding_stats` are top-15 leaderboards captured mid-season, and
  `points_table` is the standings at that same point. They do NOT cover the full season.
- Teams are referenced by code: MI, CSK, KKR, RCB, GT, RR, SRH, PBKS, DC, LSG.

## Cricket conventions in this data
- `over` is stored as over.ball (2.1 = 3rd over, 1st ball). `over_no` is the 0-indexed over (0-19), `ball_no` the ball within it.
- Innings 1 and 2 are the regular innings; innings 3 and 4 only exist for a super over.
- `wide`, `noballs`, `legbyes`, `byes` are 0/1 flags; `extras` holds the extra runs on that ball.
  Total runs on a ball = runs_of_bat + extras.
- A dismissal is a delivery with a non-null player_dismissed_id; wicket_type says how.
- When a question defines a metric (legal delivery, wicket, economy, ...), use exactly that definition.

## How to answer
- Return exactly ONE SQLite query (SELECT or WITH ... SELECT) inside a ```sql code block. No explanation.
- Use only tables and columns that exist in the schema. Never modify data.
- Return only the columns the question asks for. For "who/which" questions return the name (not the id)
  plus the value asked about.
- Do not ROUND numbers or format them as text; return raw numeric values.
- Use ORDER BY ... LIMIT only when the question asks for a top/bottom item. If the question says to
  include ties, return every tied row.
- Use the exact category values listed under "Allowed values" (they are case-sensitive)."""

USER_TEMPLATE = """## Schema
{schema}

## Allowed values for categorical columns
{categorical}

## Question
{question}"""


def categorical_values(conn, max_distinct=12):
    """List distinct values of low-cardinality TEXT columns, e.g. wicket_type, stage, toss_decision."""
    lines = []
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in tables:
        for col, ctype in conn.execute(f"SELECT name, type FROM pragma_table_info('{t}')"):
            if ctype.upper() != "TEXT":
                continue
            vals = [r[0] for r in conn.execute(
                f'SELECT DISTINCT "{col}" FROM {t} WHERE "{col}" IS NOT NULL ORDER BY 1')]
            # skip id-like columns (team codes are covered in the system prompt)
            if 1 < len(vals) <= max_distinct and not col.endswith(("team", "_code", "winner")):
                lines.append(f"- {t}.{col}: " + ", ".join(repr(v) for v in vals))
    return "\n".join(lines)


class PromptBuilder:
    """Reads the schema and categorical values once, then builds a user prompt per question."""

    def __init__(self, db_path=DB_PATH, schema_path=SCHEMA_PATH):
        with open(schema_path, encoding="utf-8") as f:
            self.schema = f.read().strip()
        conn = sqlite3.connect(db_path)
        self.categorical = categorical_values(conn)
        conn.close()

    def user_prompt(self, question):
        return USER_TEMPLATE.format(schema=self.schema, categorical=self.categorical, question=question)
