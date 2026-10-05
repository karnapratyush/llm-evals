-- Schema for Text-to-SQL generation prompt
-- Source DB: ipl_2026_relational.db (SQLite)

-- ========== RELATIONSHIPS (join paths) ==========
-- venues.home_team -> teams.team_code   (many-to-one)
-- players.team_code -> teams.team_code   (many-to-one)
-- matches.bowl_first_team -> teams.team_code   (many-to-one)
-- matches.bat_first_team -> teams.team_code   (many-to-one)
-- matches.venue_id -> venues.venue_id   (many-to-one)
-- match_results.best_bowler_id -> players.player_id   (many-to-one)
-- match_results.top_scorer_id -> players.player_id   (many-to-one)
-- match_results.player_of_the_match_id -> players.player_id   (many-to-one)
-- match_results.match_winner -> teams.team_code   (many-to-one)
-- match_results.toss_winner -> teams.team_code   (many-to-one)
-- match_results.away_team -> teams.team_code   (many-to-one)
-- match_results.home_team -> teams.team_code   (many-to-one)
-- match_results.match_id -> matches.match_id   (one-to-one)
-- deliveries.player_dismissed_id -> players.player_id   (many-to-one)
-- deliveries.bowler_id -> players.player_id   (many-to-one)
-- deliveries.striker_id -> players.player_id   (many-to-one)
-- deliveries.bowling_team -> teams.team_code   (many-to-one)
-- deliveries.batting_team -> teams.team_code   (many-to-one)
-- deliveries.match_id -> matches.match_id   (many-to-one)
-- delivery_fielders.player_id -> players.player_id   (many-to-many (via junction))
-- delivery_fielders.delivery_id -> deliveries.delivery_id   (many-to-many (via junction))
-- batting_stats.team_code -> teams.team_code   (many-to-one)
-- batting_stats.player_id -> players.player_id   (one-to-one)
-- bowling_stats.team_code -> teams.team_code   (many-to-one)
-- bowling_stats.player_id -> players.player_id   (one-to-one)
-- fielding_stats.team_code -> teams.team_code   (many-to-one)
-- fielding_stats.player_id -> players.player_id   (one-to-one)
-- points_table.team_code -> teams.team_code   (one-to-one)

-- ========== teams (10 rows) ==========
CREATE TABLE teams (
    team_code   TEXT PRIMARY KEY,
    team_name   TEXT NOT NULL UNIQUE
);
-- sample rows:
-- team_code | team_name
-- MI | Mumbai Indians
-- CSK | Chennai Super Kings
-- KKR | Kolkata Knight Riders

-- ========== venues (13 rows) ==========
CREATE TABLE venues (
    venue_id      INTEGER PRIMARY KEY,
    venue_stadium TEXT NOT NULL UNIQUE,
    city          TEXT,
    state         TEXT,
    capacity      INTEGER,
    home_team     TEXT REFERENCES teams(team_code)
);
-- sample rows:
-- venue_id | venue_stadium | city | state | capacity | home_team
-- 1 | Narendra Modi Stadium | Ahmedabad | Gujrat | 132000 | GT
-- 2 | Wankhede Stadium | Mumbai | Maharashtra | 33108 | MI
-- 3 | Eden Gardens | Kolkata | West Bengal | 68000 | KKR

-- ========== players (260 rows) ==========
CREATE TABLE players (
    player_id   INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL UNIQUE,
    team_code   TEXT NOT NULL REFERENCES teams(team_code),
    nationality TEXT,
    role        TEXT,
    is_captain  INTEGER NOT NULL DEFAULT 0
);
-- sample rows:
-- player_id | player_name | team_code | nationality | role | is_captain
-- 1 | Hardik Pandya | MI | Indian | All Rounder | 1
-- 2 | Rohit Sharma | MI | Indian | Batter | 0
-- 3 | Suryakumar Yadav | MI | Indian | Batter | 0

-- ========== matches (74 rows) ==========
CREATE TABLE matches (
    match_id        INTEGER PRIMARY KEY,
    date            TEXT NOT NULL,
    stage           TEXT NOT NULL,
    venue_id        INTEGER NOT NULL REFERENCES venues(venue_id),
    bat_first_team  TEXT NOT NULL REFERENCES teams(team_code),
    bowl_first_team TEXT NOT NULL REFERENCES teams(team_code)
);
-- sample rows:
-- match_id | date | stage | venue_id | bat_first_team | bowl_first_team
-- 1 | 2026-03-28 | League stage | 9 | SRH | RCB
-- 2 | 2026-03-29 | League stage | 2 | KKR | MI
-- 3 | 2026-03-30 | League stage | 10 | CSK | RR

-- ========== match_results (39 rows) ==========
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
-- sample rows:
-- match_id | home_team | away_team | toss_winner | toss_decision | first_ings_score | first_ings_wkts | second_ings_score | second_ings_wkts | match_result | match_winner | wb_runs | wb_wickets | balls_left | player_of_the_match_id | top_scorer_id | highscore | best_bowler_id | best_bowling_figure | super_over_match
-- 1 | RCB | SRH | RCB | Bowl | 201 | 9 | 203 | 4 | completed | RCB | NULL | 6 | 26 | 94 | 157 | 80 | 94 | 3--22 | No
-- 2 | MI | KKR | MI | Bowl | 220 | 4 | 224 | 4 | completed | MI | NULL | 6 | 5 | 9 | 5 | 81 | 9 | 3--39 | No
-- 3 | RR | CSK | RR | Bowl | 127 | 10 | 128 | 2 | completed | RR | NULL | 8 | 47 | 145 | 137 | 52 | 144 | 2--19 | No

-- ========== deliveries (17477 rows) ==========
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
-- sample rows:
-- delivery_id | match_id | innings | over | over_no | ball_no | batting_team | bowling_team | striker_id | bowler_id | runs_of_bat | extras | wide | legbyes | byes | noballs | wicket_type | player_dismissed_id
-- 1 | 1 | 1 | 0.1 | 0 | 1 | SRH | RCB | 158 | 94 | 0 | 0 | 0 | 0 | 0 | 0 | NULL | NULL
-- 2 | 1 | 1 | 0.2 | 0 | 2 | SRH | RCB | 158 | 94 | 1 | 0 | 0 | 0 | 0 | 0 | NULL | NULL
-- 3 | 1 | 1 | 0.3 | 0 | 3 | SRH | RCB | 163 | 94 | 0 | 0 | 0 | 0 | 0 | 0 | NULL | NULL

-- ========== delivery_fielders (700 rows) ==========
CREATE TABLE delivery_fielders (
    delivery_id   INTEGER NOT NULL REFERENCES deliveries(delivery_id),
    player_id     INTEGER NOT NULL REFERENCES players(player_id),
    is_substitute INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (delivery_id, player_id)
);
-- sample rows:
-- delivery_id | player_id | is_substitute
-- 15 | 85 | 0
-- 22 | 84 | 0
-- 30 | 104 | 0

-- ========== batting_stats (15 rows) ==========
CREATE TABLE batting_stats (
    player_id   INTEGER PRIMARY KEY REFERENCES players(player_id),
    team_code   TEXT NOT NULL REFERENCES teams(team_code),
    position INTEGER, matches INTEGER, innings INTEGER, runs INTEGER, impact REAL,
    average REAL, strike_rate REAL, not_outs INTEGER, high_score INTEGER, balls_faced INTEGER,
    hundreds INTEGER, fifties INTEGER, ducks INTEGER, fours INTEGER, sixes INTEGER
);
-- sample rows:
-- player_id | team_code | position | matches | innings | runs | impact | average | strike_rate | not_outs | high_score | balls_faced | hundreds | fifties | ducks | fours | sixes
-- 33 | CSK | 9 | 8 | 8 | 304 | 369.4 | 50.66 | 169.83 | 2 | 115 | 179 | 2 | 0 | 0 | 33 | 15
-- 81 | RCB | 4 | 8 | 8 | 351 | 282.2 | 58.5 | 162.5 | 2 | 81 | 216 | 0 | 3 | 0 | 37 | 14
-- 83 | RCB | 15 | 8 | 7 | 242 | 245.0 | 40.33 | 192.06 | 1 | 61 | 126 | 0 | 3 | 0 | 22 | 16

-- ========== bowling_stats (15 rows) ==========
CREATE TABLE bowling_stats (
    player_id   INTEGER PRIMARY KEY REFERENCES players(player_id),
    team_code   TEXT NOT NULL REFERENCES teams(team_code),
    position INTEGER, matches INTEGER, innings INTEGER, wickets INTEGER, economy REAL,
    impact REAL, bbi TEXT, overs REAL, balls INTEGER, dot_balls INTEGER, maiden_overs INTEGER,
    runs INTEGER, avg REAL, "4wh" INTEGER, "5wh" INTEGER
);
-- sample rows:
-- player_id | team_code | position | matches | innings | wickets | economy | impact | bbi | overs | balls | dot_balls | maiden_overs | runs | avg | 4wh | 5wh
-- 38 | CSK | 2 | 8 | 8 | 14 | 8.56 | 284.8 | 3--22 | 27.4 | 166 | 75 | 0 | 237 | 16.92 | 0 | 0
-- 39 | CSK | 12 | 7 | 7 | 9 | 9.73 | 188.2 | 4--18 | 19.0 | 114 | 37 | 0 | 185 | 20.55 | 1 | 0
-- 68 | KKR | 13 | 8 | 7 | 9 | 10.28 | 225.2 | 2--24 | 28.0 | 168 | 60 | 0 | 288 | 32.0 | 0 | 0

-- ========== fielding_stats (15 rows) ==========
CREATE TABLE fielding_stats (
    player_id   INTEGER PRIMARY KEY REFERENCES players(player_id),
    team_code   TEXT NOT NULL REFERENCES teams(team_code),
    rank INTEGER, matches INTEGER, catches INTEGER, cpm REAL
);
-- sample rows:
-- player_id | team_code | rank | matches | catches | cpm
-- 7 | MI | 13 | 7 | 5 | 0.714
-- 13 | MI | 6 | 7 | 7 | 1.0
-- 27 | CSK | 3 | 5 | 8 | 1.6

-- ========== points_table (10 rows) ==========
CREATE TABLE points_table (
    team_code TEXT PRIMARY KEY REFERENCES teams(team_code),
    position INTEGER, matches INTEGER, wins INTEGER, defeats INTEGER, ties INTEGER,
    abandoned INTEGER, points INTEGER, nrr REAL
);
-- sample rows:
-- team_code | position | matches | wins | defeats | ties | abandoned | points | nrr
-- PBKS | 1 | 7 | 6 | 0 | 0 | 1 | 13 | 1.333
-- RCB | 2 | 8 | 6 | 2 | 0 | 0 | 12 | 1.919
-- SRH | 3 | 8 | 5 | 3 | 0 | 0 | 10 | 0.815

