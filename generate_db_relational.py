"""
Build a RELATIONAL version of the IPL 2026 data: real primary keys, real foreign keys,
and cleaned join keys, so every relationship can be joined with a plain `=`.

Output: ipl_2026_relational.db   (generate_db.py's raw DB is left untouched)

Raw-CSV problems this fixes (each one breaks a join in the raw DB):
  - teams are abbreviations in some files, full names in others, misspelled in squads
  - player names: trailing spaces, typos and short forms ("Rahul" = "KL Rahul")
  - venue names: 3 different spellings of the same stadium across files; Raipur missing
  - matches.csv has only 39 of the 74 matches that deliveries.csv covers
  - deliveries.fielder packs several players into one string ("A/B", "(sub)X")

Table layout (PK = primary key, FK -> referenced table):

  teams            PK team_code
  venues           PK venue_id         FK home_team -> teams
  players          PK player_id        FK team_code -> teams
  matches          PK match_id         FK venue_id -> venues, bat_first_team / bowl_first_team -> teams
  match_results    PK match_id (1:1)   FK match_id -> matches, toss_winner / match_winner -> teams,
                                          player_of_the_match_id / top_scorer_id / best_bowler_id -> players
  deliveries       PK delivery_id      FK match_id -> matches, batting_team / bowling_team -> teams,
                                          striker_id / bowler_id / player_dismissed_id -> players
  delivery_fielders  PK (delivery_id, player_id)  - many-to-many: one delivery, 1-2 fielders
  batting_stats / bowling_stats / fielding_stats   PK player_id FK -> players, team_code -> teams
  points_table     PK team_code        FK -> teams

Run:  uv run python generate_db_relational.py
"""

import re
import sqlite3
from pathlib import Path

import pandas as pd

from config import DATA_DIR, DB_PATH

# ---------- lookup maps (built by inspecting the raw data) ----------
TEAMS = {
    "MI": "Mumbai Indians",
    "CSK": "Chennai Super Kings",
    "KKR": "Kolkata Knight Riders",
    "RCB": "Royal Challengers Bengaluru",
    "GT": "Gujarat Titans",
    "RR": "Rajasthan Royals",
    "SRH": "Sunrisers Hyderabad",
    "PBKS": "Punjab Kings",
    "DC": "Delhi Capitals",
    "LSG": "Lucknow Super Giants",
}
# squads.csv misspells two team names
TEAM_NAME_FIXES = {"Kolkata Night Riders": "Kolkata Knight Riders", "Gujrat Titans": "Gujarat Titans"}

# spelling used in matches.csv / deliveries.csv -> venues.venue_stadium
VENUE_ALIASES = {
    "Arun Jaitley Stadium, Delhi": "Arun Jaitley Stadium",
    "Barsapara Cricket Stadium, Guwahati": "Barsapara Stadium",
    "Barsapara Stadium, Guwahati": "Barsapara Stadium",
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow": "Ekana Cricket Stadium",
    "Ekana Cricket Stadium, Lucknow": "Ekana Cricket Stadium",
    "Eden Gardens, Kolkata": "Eden Gardens",
    "Himachal Pradesh Cricket Association Stadium, Dharamsala": "HPCA Stadium",
    "M.Chinnaswamy Stadium, Bengaluru": "M. Chinnaswamy Stadium",
    "M. Chinnaswamy Stadium, Bangalore": "M. Chinnaswamy Stadium",
    "MA Chidambaram Stadium, Chennai": "MA Chidambaram Stadium",
    "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur, New Chandigarh": "New PCA Cricket Stadium",
    "New PCA Cricket Stadium, Mullanpur": "New PCA Cricket Stadium",
    "Narendra Modi Stadium, Ahmedabad": "Narendra Modi Stadium",
    "Rajiv Gandhi International Stadium, Hyderabad": "Rajiv Gandhi International Stadium",
    "Sawai Mansingh Stadium, Jaipur": "Sawai Mansingh Stadium",
    "Wankhede Stadium, Mumbai": "Wankhede Stadium",
    "Shaheed Veer Narayan Singh International Stadium, Raipur": "Shaheed Veer Narayan Singh International Stadium",
}
# used in deliveries but missing from venues.csv (capacity / home team unknown -> NULL)
EXTRA_VENUES = [dict(venue_stadium="Shaheed Veer Narayan Singh International Stadium",
                     city="Raipur", state="Chhattisgarh", capacity=None, home_team=None)]

# name used in other files -> name in squads.csv
PLAYER_ALIASES = {
    "Abishek Porel": "Abhishek Porel",
    "Akshat Raghuwanshi": "Akshat Raghuvanshi",
    "Ayush Mhatre": "Ayush Matre",
    "Bishnoi": "Ravi Bishnoi",
    "David Ferreira": "Donovan Ferreira",
    "Devdutt Padikkal": "Devdutt Padikal",
    "Digvesh Singh Rathi": "Digvesh Rathi",
    "Jaiswal": "Yashasvi Jaiswal",
    "Natarajan": "T Natrajan",
    "Nitish Reddy": "Nitish Kumar Reddy",
    "Rahul": "KL Rahul",
    "Rasikh Salam Dar": "Rasikh Salam",
    "Ravindra Jadeka": "Ravindra Jadeja",
    "Sai Sudarshan": "Sai Sudharsan",
    "Shivam Dube": "Shivam Dubey",
    "Smaran Ravichandran": "Ravichandran Smaran",
    "Varun Chakaravarthy": "Varun Chakravarthy",
}
# played this season but not in squads.csv (nationality / role unknown -> NULL)
EXTRA_PLAYERS = [("Dilshan Madushanka", "SRH"), ("George Linde", "LSG"), ("Krish Bhagat", "MI")]

# ---------- DDL: this is where the keys live ----------
DDL = """
CREATE TABLE teams (
    team_code   TEXT PRIMARY KEY,
    team_name   TEXT NOT NULL UNIQUE
);

CREATE TABLE venues (
    venue_id      INTEGER PRIMARY KEY,
    venue_stadium TEXT NOT NULL UNIQUE,
    city          TEXT,
    state         TEXT,
    capacity      INTEGER,
    home_team     TEXT REFERENCES teams(team_code)
);

CREATE TABLE players (
    player_id   INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL UNIQUE,
    team_code   TEXT NOT NULL REFERENCES teams(team_code),
    nationality TEXT,
    role        TEXT,
    is_captain  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE matches (
    match_id        INTEGER PRIMARY KEY,
    date            TEXT NOT NULL,
    stage           TEXT NOT NULL,
    venue_id        INTEGER NOT NULL REFERENCES venues(venue_id),
    bat_first_team  TEXT NOT NULL REFERENCES teams(team_code),
    bowl_first_team TEXT NOT NULL REFERENCES teams(team_code)
);

CREATE TABLE match_results (
    match_id               INTEGER PRIMARY KEY REFERENCES matches(match_id),
    home_team              TEXT NOT NULL REFERENCES teams(team_code),
    away_team              TEXT NOT NULL REFERENCES teams(team_code),
    toss_winner            TEXT REFERENCES teams(team_code),
    toss_decision          TEXT,
    first_ings_score       INTEGER,
    first_ings_wkts        INTEGER,
    second_ings_score      INTEGER,
    second_ings_wkts       INTEGER,
    match_result           TEXT,
    match_winner           TEXT REFERENCES teams(team_code),
    wb_runs                INTEGER,
    wb_wickets             INTEGER,
    balls_left             INTEGER,
    player_of_the_match_id INTEGER REFERENCES players(player_id),
    top_scorer_id          INTEGER REFERENCES players(player_id),
    highscore              INTEGER,
    best_bowler_id         INTEGER REFERENCES players(player_id),
    best_bowling_figure    TEXT,
    super_over_match       TEXT
);

CREATE TABLE deliveries (
    delivery_id         INTEGER PRIMARY KEY,
    match_id            INTEGER NOT NULL REFERENCES matches(match_id),
    innings             INTEGER NOT NULL,
    "over"              REAL NOT NULL,
    over_no             INTEGER NOT NULL,
    ball_no             INTEGER NOT NULL,
    batting_team        TEXT NOT NULL REFERENCES teams(team_code),
    bowling_team        TEXT NOT NULL REFERENCES teams(team_code),
    striker_id          INTEGER NOT NULL REFERENCES players(player_id),
    bowler_id           INTEGER NOT NULL REFERENCES players(player_id),
    runs_of_bat         INTEGER NOT NULL,
    extras              INTEGER NOT NULL,
    wide                INTEGER NOT NULL,
    legbyes             INTEGER NOT NULL,
    byes                INTEGER NOT NULL,
    noballs             INTEGER NOT NULL,
    wicket_type         TEXT,
    player_dismissed_id INTEGER REFERENCES players(player_id)
);

CREATE TABLE delivery_fielders (
    delivery_id   INTEGER NOT NULL REFERENCES deliveries(delivery_id),
    player_id     INTEGER NOT NULL REFERENCES players(player_id),
    is_substitute INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (delivery_id, player_id)
);

CREATE TABLE batting_stats (
    player_id   INTEGER PRIMARY KEY REFERENCES players(player_id),
    team_code   TEXT NOT NULL REFERENCES teams(team_code),
    position INTEGER, matches INTEGER, innings INTEGER, runs INTEGER, impact REAL,
    average REAL, strike_rate REAL, not_outs INTEGER, high_score INTEGER, balls_faced INTEGER,
    hundreds INTEGER, fifties INTEGER, ducks INTEGER, fours INTEGER, sixes INTEGER
);

CREATE TABLE bowling_stats (
    player_id   INTEGER PRIMARY KEY REFERENCES players(player_id),
    team_code   TEXT NOT NULL REFERENCES teams(team_code),
    position INTEGER, matches INTEGER, innings INTEGER, wickets INTEGER, economy REAL,
    impact REAL, bbi TEXT, overs REAL, balls INTEGER, dot_balls INTEGER, maiden_overs INTEGER,
    runs INTEGER, avg REAL, "4wh" INTEGER, "5wh" INTEGER
);

CREATE TABLE fielding_stats (
    player_id   INTEGER PRIMARY KEY REFERENCES players(player_id),
    team_code   TEXT NOT NULL REFERENCES teams(team_code),
    rank INTEGER, matches INTEGER, catches INTEGER, cpm REAL
);

CREATE TABLE points_table (
    team_code TEXT PRIMARY KEY REFERENCES teams(team_code),
    position INTEGER, matches INTEGER, wins INTEGER, defeats INTEGER, ties INTEGER,
    abandoned INTEGER, points INTEGER, nrr REAL
);

CREATE INDEX idx_deliveries_match   ON deliveries(match_id);
CREATE INDEX idx_deliveries_striker ON deliveries(striker_id);
CREATE INDEX idx_deliveries_bowler  ON deliveries(bowler_id);
CREATE INDEX idx_fielders_player    ON delivery_fielders(player_id);
"""


def read(name):
    return pd.read_csv(DATA_DIR / f"{name}.csv")


def iso_date(series):
    """'March 28, 2026' / 'Mar 28, 2026' -> '2026-03-28'"""
    return pd.to_datetime(series, format="mixed").dt.strftime("%Y-%m-%d")


def nullable_int(series):
    return series.astype("Int64")


def insert(conn, table, df):
    """Insert a DataFrame into an already-created table (keeps our DDL and its keys)."""
    df = df.astype(object).where(df.notna(), None)   # NaN / <NA> -> SQL NULL
    cols = ", ".join(f'"{c}"' for c in df.columns)
    marks = ", ".join("?" * len(df.columns))
    conn.executemany(f"INSERT INTO {table} ({cols}) VALUES ({marks})", df.values.tolist())
    print(f"  {table:18} {len(df):>6} rows")


class PlayerResolver:
    """Turns any raw player name into a players.player_id; fails loudly on unknown names."""

    def __init__(self, players):
        self.ids = dict(zip(players["player_name"], players["player_id"]))
        self.team_of = dict(zip(players["player_id"], players["team_code"]))
        self.unknown = set()
        self.team_mismatch = set()

    def __call__(self, name, team=None):
        if name is None or pd.isna(name):
            return None
        clean = PLAYER_ALIASES.get(name.strip(), name.strip())
        pid = self.ids.get(clean)
        if pid is None:
            self.unknown.add(name)
        elif team is not None and self.team_of[pid] != team:
            self.team_mismatch.add((name, team, self.team_of[pid]))
        return pid


def build():
    Path(DB_PATH).unlink(missing_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")   # make SQLite reject any broken reference
    conn.executescript(DDL)
    team_code_of = {v: k for k, v in TEAMS.items()}
    print("Loading tables:")

    # ---- teams ----
    insert(conn, "teams", pd.DataFrame(list(TEAMS.items()), columns=["team_code", "team_name"]))

    # ---- venues ----
    venues = pd.concat([read("venues"), pd.DataFrame(EXTRA_VENUES)], ignore_index=True)
    venues.insert(0, "venue_id", range(1, len(venues) + 1))
    venues["capacity"] = nullable_int(venues["capacity"])
    insert(conn, "venues", venues)
    venue_id_of = dict(zip(venues["venue_stadium"], venues["venue_id"]))

    # ---- players (squads + replacement players) ----
    sq = read("squads")
    players = pd.DataFrame({
        "player_name": sq["player"].str.strip(),
        "team_code": sq["team_name"].replace(TEAM_NAME_FIXES).map(team_code_of),
        "nationality": sq["nationality"],
        "role": sq["role"],
        "is_captain": (sq["designation"] == "Captain").astype(int),
    })
    extra = pd.DataFrame([dict(player_name=n, team_code=t, nationality=None, role=None, is_captain=0)
                          for n, t in EXTRA_PLAYERS])
    players = pd.concat([players, extra], ignore_index=True)
    players.insert(0, "player_id", range(1, len(players) + 1))
    insert(conn, "players", players)
    pid = PlayerResolver(players)

    # ---- matches: one row per match in deliveries (all 74) ----
    dl = read("deliveries")
    dl["date"] = iso_date(dl["date"])
    first = dl[dl["innings"] == 1].groupby("match_no").first()
    matches = pd.DataFrame({
        "match_id": first.index,
        "date": first["date"].values,
        "stage": first["stage"].values,
        "venue_id": first["venue"].map(VENUE_ALIASES).map(venue_id_of).values,
        "bat_first_team": first["batting_team"].values,
        "bowl_first_team": first["bowling_team"].values,
    })
    insert(conn, "matches", matches)

    # ---- match_results: the 39 matches matches.csv has results for ----
    m = read("matches")
    int_cols = ["first_ings_score", "first_ings_wkts", "second_ings_score", "second_ings_wkts",
                "wb_runs", "wb_wickets", "balls_left", "highscore"]
    results = pd.DataFrame({
        "match_id": m["match_id"],
        "home_team": m["team1"],
        "away_team": m["team2"],
        "toss_winner": m["toss_winner"],
        "toss_decision": m["toss_decision"],
        **{c: nullable_int(m[c]) for c in int_cols},
        "match_result": m["match_result"],
        "match_winner": m["match_winner"],
        "player_of_the_match_id": m["player_of_the_match"].map(pid),
        "top_scorer_id": m["top_scorer"].map(pid),
        "best_bowler_id": m["best_bowling"].map(pid),
        "best_bowling_figure": m["best_bowling_figure"],
        "super_over_match": m["super_over_match"],
    })
    insert(conn, "match_results", results)

    # ---- deliveries + delivery_fielders ----
    dl["delivery_id"] = range(1, len(dl) + 1)
    deliveries = pd.DataFrame({
        "delivery_id": dl["delivery_id"],
        "match_id": dl["match_no"],
        "innings": dl["innings"],
        "over": dl["over"],
        "over_no": dl["over"].astype(int),
        "ball_no": (dl["over"] * 10).round().astype(int) % 10,
        "batting_team": dl["batting_team"],
        "bowling_team": dl["bowling_team"],
        "striker_id": [pid(n, t) for n, t in zip(dl["striker"], dl["batting_team"])],
        "bowler_id": [pid(n, t) for n, t in zip(dl["bowler"], dl["bowling_team"])],
        "runs_of_bat": dl["runs_of_bat"],
        "extras": dl["extras"],
        "wide": dl["wide"],
        "legbyes": dl["legbyes"],
        "byes": dl["byes"],
        "noballs": dl["noballs"],
        # one spelling per dismissal type; a wicket_type with no dismissed player is a data error
        "wicket_type": dl["wicket_type"].replace({"hitwicket": "hit wicket", "runout": "run out"})
                                       .where(dl["player_dismissed"].notna()),
        "player_dismissed_id": [pid(n, t) for n, t in zip(dl["player_dismissed"], dl["batting_team"])],
    })
    insert(conn, "deliveries", deliveries)

    fielder_rows = []
    for did, raw, team in dl.loc[dl["fielder"].notna(), ["delivery_id", "fielder", "bowling_team"]].values:
        for part in raw.split("/"):
            is_sub = part.strip().startswith("(sub)")
            name = re.sub(r"^\(sub\)", "", part.strip()).strip()
            fielder_rows.append(dict(delivery_id=did, player_id=pid(name, team), is_substitute=int(is_sub)))
    insert(conn, "delivery_fielders", pd.DataFrame(fielder_rows).drop_duplicates(["delivery_id", "player_id"]))

    # ---- stats tables: swap the name column for player_id ----
    for table, name_col in [("batting_stats", "batsman"), ("bowling_stats", "bowler"),
                            ("fielding_stats", "player")]:
        s = read(table)
        s.insert(0, "player_id", [pid(n, t) for n, t in zip(s[name_col], s["team"])])
        s = s.drop(columns=[name_col]).rename(columns={"team": "team_code"})
        insert(conn, table, s)

    # ---- points_table: full team name -> team_code ----
    pt = read("points_table")
    pt.insert(0, "team_code", pt.pop("team").map(team_code_of))
    insert(conn, "points_table", pt)

    # ---- fail loudly if any name could not be resolved ----
    if pid.unknown:
        conn.close()
        raise SystemExit(f"Unresolved player names (add to PLAYER_ALIASES / EXTRA_PLAYERS): "
                         f"{sorted(pid.unknown)}")
    conn.commit()
    return conn, pid


def verify(conn, pid):
    print("\n--- Verification ---")
    broken = conn.execute("PRAGMA foreign_key_check").fetchall()
    print("foreign key violations (should be 0):", len(broken))
    if pid.team_mismatch:
        print("players seen for a team other than their squad team:", sorted(pid.team_mismatch))

    # cross-check against the dataset README: same answers as the raw data, now via id joins
    checks = {
        "most runs (README: Sooryavanshi 776)": """
            SELECT p.player_name, SUM(d.runs_of_bat) FROM deliveries d
            JOIN players p ON p.player_id = d.striker_id
            GROUP BY p.player_id ORDER BY 2 DESC LIMIT 1""",
        "highest score (README: KL Rahul 152)": """
            SELECT p.player_name, SUM(d.runs_of_bat) FROM deliveries d
            JOIN players p ON p.player_id = d.striker_id
            GROUP BY d.match_id, p.player_id ORDER BY 2 DESC LIMIT 1""",
        "matches with no venue_id (should be 0)":
            "SELECT COUNT(*) FROM matches WHERE venue_id IS NULL",
        "matches with results / total":
            "SELECT (SELECT COUNT(*) FROM match_results) || ' / ' || (SELECT COUNT(*) FROM matches)",
    }
    for label, sql in checks.items():
        print(f"{label:42} -> {conn.execute(sql).fetchall()}")


if __name__ == "__main__":
    conn, pid = build()
    verify(conn, pid)
    conn.close()
    print(f"\nDone. Wrote {DB_PATH}")
