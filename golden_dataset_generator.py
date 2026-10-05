# Golden dataset (100 questions) for the IPL 2026 Text-to-SQL eval - RELATIONAL schema.
# DB is built by generate_db_relational.py -> ipl_2026_relational.db (PKs + FKs, clean join keys).
# The previous raw-schema question set is kept in golden_dataset_generator_raw.py.
#
# Path A convention: "who/which" questions include name + value in gold; the
# evaluator tolerates name-only OR name+value.
#
# Difficulty gradient:
#   easy    : #1-20   - single table, one filter / aggregate
#   medium  : #21-55  - 2-3 table joins (id -> name lookups), LEFT/anti joins, GROUP BY on joins
#   hard    : #56-85  - same table joined twice, self-joins, many-to-many, multi-hop, CROSS/FULL joins, windows
#   brutal  : #86-100 - joins + CTEs + windows + cricket rules + NULL / coverage traps stacked
#
# `cat` tags the SQL skills each question exercises:
#   filter, aggregate, group, having, order, case, null, date, string, ratio, tie, domain,
#   join, multi-join, left-join, anti-join, semi-join, self-join, role-join (same table twice),
#   many-to-many, cross-join, full-join, set-op, subquery, cte, window
#
# Join traps in this schema (what separates models):
#   - names live ONLY in players / teams: every "who" question needs an id -> name join
#   - deliveries references players 3 ways (striker_id, bowler_id, player_dismissed_id):
#     questions about batter vs bowler need players joined twice under different aliases
#   - delivery_fielders is many-to-many: a run out can credit 2 fielders, so joining it and
#     counting rows double-counts dismissals
#   - matches has all 74 games; match_results only the first 39 (inner join silently drops 35)
#   - match_results.home_team is the home side, matches.bat_first_team is who batted first
#   - match 12 is abandoned (in match_results) yet has 22 balls in deliveries
#   - match 38 had a super over: deliveries innings 3 and 4
#   - NULLs: 3 players have unknown nationality/role, Raipur venue has no capacity/home_team,
#     abandoned match has NULL winner
#   - RR and PBKS each have two home venues
#
# Shared cricket definitions used in the questions:
#   total runs on a ball   = runs_of_bat + extras
#   legal delivery         = wide = 0 AND noballs = 0
#   ball faced by batter   = wide = 0
#   runs conceded (bowler) = runs_of_bat + extras on wides/no-balls (byes/leg-byes not charged)
#   bowler's wicket        = player_dismissed_id IS NOT NULL AND wicket_type NOT IN
#                            ('run out','retired hurt','obstructing the field')
#   regular innings        = innings 1 or 2 (3 and 4 are the super over)
#   over number            = over_no (0-indexed); powerplay 0-5, death 15-19

RUNS = "d.runs_of_bat + d.extras"
LEGAL = "CASE WHEN d.wide = 0 AND d.noballs = 0 THEN 1 ELSE 0 END"
CONCEDED = "d.runs_of_bat + CASE WHEN d.wide = 1 OR d.noballs = 1 THEN d.extras ELSE 0 END"
BOWLER_WKT = ("d.player_dismissed_id IS NOT NULL AND d.wicket_type NOT IN "
              "('run out','retired hurt','obstructing the field')")
NOT_ABANDONED = ("d.match_id NOT IN (SELECT match_id FROM match_results "
                 "WHERE match_result = 'abandoned')")

GOLDEN = [
 # ================= EASY (single table) =================
 dict(id=1, diff="easy", cat=["aggregate"],
   q="How many matches were played this season?",
   sql="SELECT COUNT(*) FROM matches"),

 dict(id=2, diff="easy", cat=["filter", "aggregate"],
   q="How many matches in match_results were abandoned?",
   sql="SELECT COUNT(*) FROM match_results WHERE match_result = 'abandoned'"),

 dict(id=3, diff="easy", cat=["order"],
   q="Which stadium has the largest capacity? Give the stadium and capacity.",
   sql="SELECT venue_stadium, capacity FROM venues ORDER BY capacity DESC LIMIT 1"),

 dict(id=4, diff="easy", cat=["filter", "aggregate"],
   q="How many overseas players are there across all teams?",
   sql="SELECT COUNT(*) FROM players WHERE nationality = 'Overseas'"),

 dict(id=5, diff="easy", cat=["null", "aggregate"],
   q="How many players have an unknown (missing) nationality?",
   sql="SELECT COUNT(*) FROM players WHERE nationality IS NULL"),

 dict(id=6, diff="easy", cat=["order"],
   q="Which team code is in position 1 of the points table, and how many points does it have?",
   sql="SELECT team_code, points FROM points_table WHERE position = 1"),

 dict(id=7, diff="easy", cat=["aggregate", "domain"],
   q="How many wides were bowled in the whole season?",
   sql="SELECT SUM(wide) FROM deliveries"),

 dict(id=8, diff="easy", cat=["aggregate"],
   q="What is the highest first-innings score recorded in match_results?",
   sql="SELECT MAX(first_ings_score) FROM match_results"),

 dict(id=9, diff="easy", cat=["filter", "aggregate"],
   q="How many matches were played in the Playoffs stage?",
   sql="SELECT COUNT(*) FROM matches WHERE stage = 'Playoffs'"),

 dict(id=10, diff="easy", cat=["filter", "aggregate"],
   q="How many sixes were hit in the whole season?",
   sql="SELECT COUNT(*) FROM deliveries WHERE runs_of_bat = 6"),

 dict(id=11, diff="easy", cat=["filter", "aggregate", "domain"],
   q="How many deliveries were bowled in super overs (innings 3 and 4)?",
   sql="SELECT COUNT(*) FROM deliveries WHERE innings > 2"),

 dict(id=12, diff="easy", cat=["null", "aggregate"],
   q="How many venues have an unknown capacity?",
   sql="SELECT COUNT(*) FROM venues WHERE capacity IS NULL"),

 dict(id=13, diff="easy", cat=["filter", "aggregate"],
   q="How many players are listed as Wicket Keeper?",
   sql="SELECT COUNT(*) FROM players WHERE role = 'Wicket Keeper'"),

 dict(id=14, diff="easy", cat=["aggregate"],
   q="How many different bowlers bowled at least one delivery this season?",
   sql="SELECT COUNT(DISTINCT bowler_id) FROM deliveries"),

 dict(id=15, diff="easy", cat=["filter", "aggregate"],
   q="How many batters in batting_stats have a strike rate above 180?",
   sql="SELECT COUNT(*) FROM batting_stats WHERE strike_rate > 180"),

 dict(id=16, diff="easy", cat=["date", "aggregate"],
   q="How many matches were played in May?",
   sql="SELECT COUNT(*) FROM matches WHERE strftime('%m', date) = '05'"),

 dict(id=17, diff="easy", cat=["aggregate"],
   q="What is the total number of runs (runs off the bat plus extras) scored in the whole season?",
   sql="SELECT SUM(runs_of_bat + extras) FROM deliveries"),

 dict(id=18, diff="easy", cat=["filter", "aggregate"],
   q="How many teams in the points table have a positive net run rate?",
   sql="SELECT COUNT(*) FROM points_table WHERE nrr > 0"),

 dict(id=19, diff="easy", cat=["filter", "aggregate"],
   q="How many deliveries were bowled in the 20th (last) over of an innings? Over numbers start at 0.",
   sql="SELECT COUNT(*) FROM deliveries WHERE over_no = 19"),

 dict(id=20, diff="easy", cat=["aggregate"],
   q="How many fielding credits went to substitute fielders?",
   sql="SELECT SUM(is_substitute) FROM delivery_fielders"),

 # ================= MEDIUM (2-3 table joins) =================
 dict(id=21, diff="medium", cat=["join", "order"],
   q="According to batting_stats, which player scored the most runs? Give the player's name and runs.",
   sql="""SELECT p.player_name, b.runs FROM batting_stats b
          JOIN players p ON p.player_id = b.player_id ORDER BY b.runs DESC LIMIT 1"""),

 dict(id=22, diff="medium", cat=["join", "order"],
   q="According to bowling_stats, which bowler has the best (lowest) economy? Give the name and economy.",
   sql="""SELECT p.player_name, s.economy FROM bowling_stats s
          JOIN players p ON p.player_id = s.player_id ORDER BY s.economy ASC LIMIT 1"""),

 dict(id=23, diff="medium", cat=["join"],
   q="What is the full name of the team at position 1 of the points table, and how many points does it have?",
   sql="""SELECT t.team_name, pt.points FROM points_table pt
          JOIN teams t ON t.team_code = pt.team_code WHERE pt.position = 1"""),

 dict(id=24, diff="medium", cat=["join", "filter"],
   q="List every captain's name together with the full name of their team.",
   sql="""SELECT p.player_name, t.team_name FROM players p
          JOIN teams t ON t.team_code = p.team_code WHERE p.is_captain = 1"""),

 dict(id=25, diff="medium", cat=["join", "group", "order"],
   q="Which batter scored the most runs off the bat this season? Give the name and runs.",
   sql="""SELECT p.player_name, SUM(d.runs_of_bat) AS r FROM deliveries d
          JOIN players p ON p.player_id = d.striker_id
          GROUP BY p.player_id ORDER BY r DESC LIMIT 1"""),

 dict(id=26, diff="medium", cat=["join", "group", "order"],
   q="Which batter hit the most sixes this season? Give the name and number of sixes.",
   sql="""SELECT p.player_name, COUNT(*) AS n FROM deliveries d
          JOIN players p ON p.player_id = d.striker_id WHERE d.runs_of_bat = 6
          GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=27, diff="medium", cat=["join", "group", "order"],
   q="Which batter hit the most fours this season? Give the name and number of fours.",
   sql="""SELECT p.player_name, COUNT(*) AS n FROM deliveries d
          JOIN players p ON p.player_id = d.striker_id WHERE d.runs_of_bat = 4
          GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=28, diff="medium", cat=["join", "group", "order", "domain"],
   q="Which bowler bowled the most dot balls (legal deliveries with zero total runs)? Give the name and count.",
   sql="""SELECT p.player_name, COUNT(*) AS n FROM deliveries d
          JOIN players p ON p.player_id = d.bowler_id
          WHERE d.wide = 0 AND d.noballs = 0 AND d.runs_of_bat = 0 AND d.extras = 0
          GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=29, diff="medium", cat=["join", "group", "order"],
   q="Which bowler bowled the most wides? Give the name and number of wides.",
   sql="""SELECT p.player_name, SUM(d.wide) AS n FROM deliveries d
          JOIN players p ON p.player_id = d.bowler_id
          GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=30, diff="medium", cat=["multi-join", "many-to-many", "group", "order"],
   q="Which fielder took the most catches this season? Give the name and number of catches.",
   sql="""SELECT p.player_name, COUNT(*) AS n FROM delivery_fielders f
          JOIN deliveries d ON d.delivery_id = f.delivery_id
          JOIN players p ON p.player_id = f.player_id
          WHERE d.wicket_type = 'caught' GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=31, diff="medium", cat=["join", "filter"],
   q="In which stadium and city was the Final played?",
   sql="""SELECT v.venue_stadium, v.city FROM matches m
          JOIN venues v ON v.venue_id = m.venue_id WHERE m.stage = 'Final'"""),

 dict(id=32, diff="medium", cat=["join", "group", "order"],
   q="Which city hosted the most matches this season? Give the city and match count.",
   sql="""SELECT v.city, COUNT(*) AS n FROM matches m
          JOIN venues v ON v.venue_id = m.venue_id GROUP BY v.city ORDER BY n DESC LIMIT 1"""),

 dict(id=33, diff="medium", cat=["join", "group", "having", "subquery", "tie"],
   q="Which player(s) won the most Player of the Match awards? Return all tied players with their award count.",
   sql="""SELECT p.player_name, COUNT(*) AS n FROM match_results r
          JOIN players p ON p.player_id = r.player_of_the_match_id
          GROUP BY p.player_id
          HAVING COUNT(*) = (SELECT MAX(c) FROM (SELECT COUNT(*) AS c FROM match_results
                             WHERE player_of_the_match_id IS NOT NULL GROUP BY player_of_the_match_id))"""),

 dict(id=34, diff="medium", cat=["join", "aggregate", "domain"],
   q="In how many matches with a result did the team that batted first win?",
   sql="""SELECT COUNT(*) FROM match_results r JOIN matches m ON m.match_id = r.match_id
          WHERE r.match_winner = m.bat_first_team"""),

 dict(id=35, diff="medium", cat=["left-join", "group"],
   q="For every team (full name), how many matches did it win according to match_results? Include teams with zero wins.",
   sql="""SELECT t.team_name, COUNT(r.match_id) FROM teams t
          LEFT JOIN match_results r ON r.match_winner = t.team_code GROUP BY t.team_code"""),

 dict(id=36, diff="medium", cat=["join", "group"],
   q="How many overseas players does each team have? Give the full team name and count.",
   sql="""SELECT t.team_name, COUNT(*) FROM players p JOIN teams t ON t.team_code = p.team_code
          WHERE p.nationality = 'Overseas' GROUP BY t.team_code"""),

 dict(id=37, diff="medium", cat=["anti-join", "multi-join"],
   q="Which venues did not host any of the matches that have an entry in match_results?",
   sql="""SELECT v.venue_stadium FROM venues v
          WHERE NOT EXISTS (SELECT 1 FROM matches m JOIN match_results r ON r.match_id = m.match_id
                            WHERE m.venue_id = v.venue_id)"""),

 dict(id=38, diff="medium", cat=["multi-join", "filter"],
   q="What is the full name of the home team of the venue where match 35 was played?",
   sql="""SELECT t.team_name FROM matches m JOIN venues v ON v.venue_id = m.venue_id
          JOIN teams t ON t.team_code = v.home_team WHERE m.match_id = 35"""),

 dict(id=39, diff="medium", cat=["join", "aggregate", "domain"],
   q="How many matches were played at a venue that is the home ground of one of the two teams playing?",
   sql="""SELECT COUNT(*) FROM matches m JOIN venues v ON v.venue_id = m.venue_id
          WHERE v.home_team IN (m.bat_first_team, m.bowl_first_team)"""),

 dict(id=40, diff="medium", cat=["join", "group", "order"],
   q="Which bowler took the most wickets with the dismissal type 'bowled'? Give the name and count.",
   sql="""SELECT p.player_name, COUNT(*) AS n FROM deliveries d
          JOIN players p ON p.player_id = d.bowler_id WHERE d.wicket_type = 'bowled'
          GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=41, diff="medium", cat=["join", "group", "order"],
   q="Which player was dismissed the most times this season (any dismissal type)? Give the name and count.",
   sql="""SELECT p.player_name, COUNT(*) AS n FROM deliveries d
          JOIN players p ON p.player_id = d.player_dismissed_id
          GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=42, diff="medium", cat=["group", "null"],
   q="How many dismissals were there of each dismissal type?",
   sql="""SELECT wicket_type, COUNT(*) FROM deliveries
          WHERE player_dismissed_id IS NOT NULL GROUP BY wicket_type"""),

 dict(id=43, diff="medium", cat=["join"],
   q="For every player in fielding_stats, give the player's name and squad role.",
   sql="""SELECT p.player_name, p.role FROM fielding_stats f
          JOIN players p ON p.player_id = f.player_id"""),

 dict(id=44, diff="medium", cat=["join"],
   q="Which players appear in both batting_stats and fielding_stats? Give their names.",
   sql="""SELECT p.player_name FROM batting_stats b
          JOIN fielding_stats f ON f.player_id = b.player_id
          JOIN players p ON p.player_id = b.player_id"""),

 dict(id=45, diff="medium", cat=["set-op", "subquery"],
   q="How many distinct players appear in at least one of batting_stats, bowling_stats, or fielding_stats?",
   sql="""SELECT COUNT(*) FROM (SELECT player_id FROM batting_stats UNION SELECT player_id FROM bowling_stats
                                UNION SELECT player_id FROM fielding_stats)"""),

 dict(id=46, diff="medium", cat=["join", "filter", "aggregate"],
   q="How many catches were taken by substitute fielders?",
   sql="""SELECT COUNT(*) FROM delivery_fielders f JOIN deliveries d ON d.delivery_id = f.delivery_id
          WHERE f.is_substitute = 1 AND d.wicket_type = 'caught'"""),

 dict(id=47, diff="medium", cat=["join", "group", "null"],
   q="How many runs off the bat were scored by players of each nationality? Players with unknown nationality form their own (NULL) group.",
   sql="""SELECT p.nationality, SUM(d.runs_of_bat) FROM deliveries d
          JOIN players p ON p.player_id = d.striker_id GROUP BY p.nationality"""),

 dict(id=48, diff="medium", cat=["join", "group", "order"],
   q="Which captain scored the most runs off the bat this season? Give the name and runs.",
   sql="""SELECT p.player_name, SUM(d.runs_of_bat) AS r FROM deliveries d
          JOIN players p ON p.player_id = d.striker_id WHERE p.is_captain = 1
          GROUP BY p.player_id ORDER BY r DESC LIMIT 1"""),

 dict(id=49, diff="medium", cat=["join", "group", "order"],
   q="Which team hit the most sixes this season? Give the full team name and number of sixes.",
   sql="""SELECT t.team_name, COUNT(*) AS n FROM deliveries d
          JOIN teams t ON t.team_code = d.batting_team WHERE d.runs_of_bat = 6
          GROUP BY t.team_code ORDER BY n DESC LIMIT 1"""),

 dict(id=50, diff="medium", cat=["multi-join", "group", "order"],
   q="Using match_results, which city has the highest average first-innings score? Give the city and the average.",
   sql="""SELECT v.city, AVG(r.first_ings_score) AS a FROM match_results r
          JOIN matches m ON m.match_id = r.match_id JOIN venues v ON v.venue_id = m.venue_id
          WHERE r.first_ings_score IS NOT NULL GROUP BY v.city ORDER BY a DESC LIMIT 1"""),

 dict(id=51, diff="medium", cat=["case", "ratio"],
   q="Among completed matches in match_results, what percentage were won by the toss winner?",
   sql="""SELECT 100.0 * SUM(CASE WHEN toss_winner = match_winner THEN 1 ELSE 0 END) / COUNT(*)
          FROM match_results WHERE match_result = 'completed'"""),

 dict(id=52, diff="medium", cat=["filter", "aggregate"],
   q="In how many matches in match_results did the home team win?",
   sql="SELECT COUNT(*) FROM match_results WHERE match_winner = home_team"),

 dict(id=53, diff="medium", cat=["join", "domain"],
   q="How many 'caught and bowled' dismissals were there (the catch was taken by the bowler who bowled the ball)?",
   sql="""SELECT COUNT(*) FROM deliveries d
          JOIN delivery_fielders f ON f.delivery_id = d.delivery_id AND f.player_id = d.bowler_id
          WHERE d.wicket_type = 'caught'"""),

 dict(id=54, diff="medium", cat=["join", "filter", "aggregate"],
   q="In how many completed matches was the Player of the Match from the losing team?",
   sql="""SELECT COUNT(*) FROM match_results r JOIN players p ON p.player_id = r.player_of_the_match_id
          WHERE r.match_result = 'completed' AND p.team_code != r.match_winner"""),

 dict(id=55, diff="medium", cat=["multi-join", "many-to-many", "aggregate"],
   q="How many stumpings were effected by players whose role is Wicket Keeper?",
   sql="""SELECT COUNT(*) FROM delivery_fielders f
          JOIN deliveries d ON d.delivery_id = f.delivery_id
          JOIN players p ON p.player_id = f.player_id
          WHERE d.wicket_type = 'stumped' AND p.role = 'Wicket Keeper'"""),

 # ================= HARD (role joins, self joins, many-to-many, windows) =================
 dict(id=56, diff="hard", cat=["role-join", "group", "order", "domain"],
   q="Which overseas bowler took the most bowler-credited wickets of Indian batters? Wickets exclude run outs, retired hurt and obstructing the field. Give the bowler's name and count.",
   sql=f"""SELECT b.player_name, COUNT(*) AS n FROM deliveries d
           JOIN players b ON b.player_id = d.bowler_id
           JOIN players x ON x.player_id = d.player_dismissed_id
           WHERE b.nationality = 'Overseas' AND x.nationality = 'Indian' AND {BOWLER_WKT}
           GROUP BY b.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=57, diff="hard", cat=["role-join", "aggregate", "null", "domain"],
   q="How many bowler-credited wickets were taken by a bowler of the same nationality as the dismissed batter? Only count cases where both nationalities are known.",
   sql=f"""SELECT COUNT(*) FROM deliveries d
           JOIN players b ON b.player_id = d.bowler_id
           JOIN players x ON x.player_id = d.player_dismissed_id
           WHERE {BOWLER_WKT} AND b.nationality = x.nationality"""),

 dict(id=58, diff="hard", cat=["many-to-many", "window", "cte", "tie"],
   q="Which fielder(s) were involved in the most run outs (a run out can credit more than one fielder)? Return all tied players with their count.",
   sql="""WITH c AS (SELECT f.player_id, COUNT(*) AS n,
                            RANK() OVER (ORDER BY COUNT(*) DESC) AS rk
                     FROM delivery_fielders f JOIN deliveries d ON d.delivery_id = f.delivery_id
                     WHERE d.wicket_type = 'run out' GROUP BY f.player_id)
          SELECT p.player_name, c.n FROM c JOIN players p ON p.player_id = c.player_id WHERE c.rk = 1"""),

 dict(id=59, diff="hard", cat=["semi-join", "many-to-many"],
   q="How many dismissals involved at least one fielder? Count each dismissal once even when two fielders were involved.",
   sql="""SELECT COUNT(*) FROM deliveries d WHERE d.player_dismissed_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM delivery_fielders f WHERE f.delivery_id = d.delivery_id)"""),

 dict(id=60, diff="hard", cat=["self-join", "date"],
   q="How many pairs of matches were played on the same date?",
   sql="""SELECT COUNT(*) FROM matches a JOIN matches b
          ON a.date = b.date AND a.match_id < b.match_id"""),

 dict(id=61, diff="hard", cat=["self-join", "domain"],
   q="How many times did a bowler take bowler-credited wickets on two consecutive deliveries (delivery_id and delivery_id + 1, same match, innings and bowler)?",
   sql=f"""SELECT COUNT(*) FROM deliveries d
           JOIN deliveries n ON n.delivery_id = d.delivery_id + 1
                            AND n.match_id = d.match_id AND n.innings = d.innings
                            AND n.bowler_id = d.bowler_id
           WHERE {BOWLER_WKT}
             AND n.player_dismissed_id IS NOT NULL
             AND n.wicket_type NOT IN ('run out','retired hurt','obstructing the field')"""),

 dict(id=62, diff="hard", cat=["multi-join", "group", "order"],
   q="In which state were the most sixes hit this season? Give the state and number of sixes.",
   sql="""SELECT v.state, COUNT(*) AS n FROM deliveries d
          JOIN matches m ON m.match_id = d.match_id JOIN venues v ON v.venue_id = m.venue_id
          WHERE d.runs_of_bat = 6 GROUP BY v.state ORDER BY n DESC LIMIT 1"""),

 dict(id=63, diff="hard", cat=["multi-join", "subquery", "window", "cte", "tie"],
   q="For the season's top run scorer (runs off the bat), in which city or cities did they score the most runs? Return all tied cities with the runs.",
   sql="""WITH c AS (SELECT v.city, SUM(d.runs_of_bat) AS r,
                            RANK() OVER (ORDER BY SUM(d.runs_of_bat) DESC) AS rk
                     FROM deliveries d
                     JOIN matches m ON m.match_id = d.match_id JOIN venues v ON v.venue_id = m.venue_id
                     WHERE d.striker_id = (SELECT striker_id FROM deliveries GROUP BY striker_id
                                           ORDER BY SUM(runs_of_bat) DESC LIMIT 1)
                     GROUP BY v.city)
          SELECT city, r FROM c WHERE rk = 1"""),

 dict(id=64, diff="hard", cat=["multi-join", "cte", "case", "domain"],
   q="Compare the average team innings total (runs off the bat plus extras, regular innings) when a team bats at one of its own home venues versus anywhere else. Ignore matches marked abandoned in match_results. Return labels 'home' and 'away' with the averages.",
   sql=f"""WITH t AS (SELECT d.match_id, d.batting_team, SUM({RUNS}) AS r FROM deliveries d
                      WHERE d.innings <= 2 AND {NOT_ABANDONED}
                      GROUP BY d.match_id, d.batting_team)
           SELECT CASE WHEN v.home_team = t.batting_team THEN 'home' ELSE 'away' END AS side, AVG(t.r)
           FROM t JOIN matches m ON m.match_id = t.match_id JOIN venues v ON v.venue_id = m.venue_id
           GROUP BY side"""),

 dict(id=65, diff="hard", cat=["window", "cte", "multi-join"],
   q="For each team (full name), who was its top run scorer this season (runs off the bat)? Give team name, player name and runs; include ties.",
   sql="""WITH r AS (SELECT d.batting_team, d.striker_id, SUM(d.runs_of_bat) AS runs,
                            RANK() OVER (PARTITION BY d.batting_team ORDER BY SUM(d.runs_of_bat) DESC) AS rk
                     FROM deliveries d GROUP BY d.batting_team, d.striker_id)
          SELECT t.team_name, p.player_name, r.runs FROM r
          JOIN teams t ON t.team_code = r.batting_team JOIN players p ON p.player_id = r.striker_id
          WHERE r.rk = 1"""),

 dict(id=66, diff="hard", cat=["window", "cte", "join", "domain"],
   q="Which venue has the highest average first-innings total (runs off the bat plus extras, computed from deliveries)? Ignore matches marked abandoned in match_results. Give the stadium and the average.",
   sql=f"""WITH t AS (SELECT d.match_id, SUM({RUNS}) AS r FROM deliveries d
                      WHERE d.innings = 1 AND {NOT_ABANDONED} GROUP BY d.match_id)
           SELECT v.venue_stadium, AVG(t.r) AS a FROM t
           JOIN matches m ON m.match_id = t.match_id JOIN venues v ON v.venue_id = m.venue_id
           GROUP BY v.venue_id ORDER BY a DESC LIMIT 1"""),

 dict(id=67, diff="hard", cat=["window", "join", "date"], ordered=True,
   q="For KL Rahul, list each match date, his runs off the bat in that match, and his cumulative runs so far, in date order.",
   sql="""SELECT m.date, SUM(d.runs_of_bat) AS runs,
                 SUM(SUM(d.runs_of_bat)) OVER (ORDER BY m.date, m.match_id) AS cumulative
          FROM deliveries d JOIN matches m ON m.match_id = d.match_id
          JOIN players p ON p.player_id = d.striker_id
          WHERE p.player_name = 'KL Rahul'
          GROUP BY m.match_id ORDER BY m.date, m.match_id"""),

 dict(id=68, diff="hard", cat=["multi-join", "group", "having", "domain"],
   q="List every century this season (100+ runs off the bat by one player in one match, regular innings): give the player name, the city, and the runs.",
   sql="""SELECT p.player_name, v.city, SUM(d.runs_of_bat) AS r FROM deliveries d
          JOIN players p ON p.player_id = d.striker_id
          JOIN matches m ON m.match_id = d.match_id JOIN venues v ON v.venue_id = m.venue_id
          WHERE d.innings <= 2 GROUP BY d.match_id, d.striker_id HAVING SUM(d.runs_of_bat) >= 100"""),

 dict(id=69, diff="hard", cat=["cte", "multi-join", "domain"],
   q="How many centuries (100+ runs off the bat in a match) were scored in a losing cause? Only matches with a completed result in match_results can be judged.",
   sql="""WITH c AS (SELECT d.match_id, d.batting_team FROM deliveries d WHERE d.innings <= 2
                     GROUP BY d.match_id, d.striker_id HAVING SUM(d.runs_of_bat) >= 100)
          SELECT COUNT(*) FROM c JOIN match_results r ON r.match_id = c.match_id
          WHERE r.match_result = 'completed' AND r.match_winner != c.batting_team"""),

 dict(id=70, diff="hard", cat=["join", "ratio", "having", "domain"],
   q="Among bowlers with at least 120 legal deliveries (regular innings), who has the best economy rate (runs conceded per 6 legal balls; byes and leg-byes are not charged)? Give the name and economy.",
   sql=f"""SELECT p.player_name, 6.0 * SUM({CONCEDED}) / SUM({LEGAL}) AS econ FROM deliveries d
           JOIN players p ON p.player_id = d.bowler_id WHERE d.innings <= 2
           GROUP BY p.player_id HAVING SUM({LEGAL}) >= 120 ORDER BY econ ASC LIMIT 1"""),

 dict(id=71, diff="hard", cat=["join", "ratio", "having", "domain"],
   q="Among batters who faced at least 200 balls (wides are not balls faced; regular innings), who has the highest strike rate (runs off the bat per 100 balls)? Give the name and strike rate.",
   sql="""SELECT p.player_name, 100.0 * SUM(d.runs_of_bat) / SUM(CASE WHEN d.wide = 0 THEN 1 ELSE 0 END) AS sr
          FROM deliveries d JOIN players p ON p.player_id = d.striker_id WHERE d.innings <= 2
          GROUP BY p.player_id HAVING SUM(CASE WHEN d.wide = 0 THEN 1 ELSE 0 END) >= 200
          ORDER BY sr DESC LIMIT 1"""),

 dict(id=72, diff="hard", cat=["join", "group", "order", "domain"],
   q="Which bowler took the most bowler-credited wickets this season (excluding run outs, retired hurt, obstructing the field)? Give the name and wickets.",
   sql=f"""SELECT p.player_name, COUNT(*) AS n FROM deliveries d
           JOIN players p ON p.player_id = d.bowler_id WHERE {BOWLER_WKT}
           GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=73, diff="hard", cat=["join", "group", "order", "domain"],
   q="Which bowler took the most bowler-credited wickets in the powerplay (over_no 0-5, i.e. the first six overs; regular innings)? Give the name and wickets.",
   sql=f"""SELECT p.player_name, COUNT(*) AS n FROM deliveries d
           JOIN players p ON p.player_id = d.bowler_id
           WHERE d.innings <= 2 AND d.over_no < 6 AND {BOWLER_WKT}
           GROUP BY p.player_id ORDER BY n DESC LIMIT 1"""),

 dict(id=74, diff="hard", cat=["join", "ratio", "group", "order", "domain"],
   q="Which bowling team had the best (lowest) economy in the death overs (over_no 15-19, i.e. the last five overs; regular innings)? Economy = runs conceded per 6 legal balls (byes and leg-byes not charged). Give the full team name and economy.",
   sql=f"""SELECT t.team_name, 6.0 * SUM({CONCEDED}) / SUM({LEGAL}) AS econ FROM deliveries d
           JOIN teams t ON t.team_code = d.bowling_team
           WHERE d.innings <= 2 AND d.over_no >= 15
           GROUP BY t.team_code ORDER BY econ ASC LIMIT 1"""),

 dict(id=75, diff="hard", cat=["window", "join", "group"],
   q="Rank all teams by total sixes hit this season with dense ranking (most sixes = rank 1). Give the full team name, sixes and rank.",
   sql="""SELECT t.team_name, COUNT(*) AS sixes, DENSE_RANK() OVER (ORDER BY COUNT(*) DESC) AS rk
          FROM deliveries d JOIN teams t ON t.team_code = d.batting_team
          WHERE d.runs_of_bat = 6 GROUP BY t.team_code"""),

 dict(id=76, diff="hard", cat=["cross-join", "left-join", "group"],
   q="For every combination of team (team code) and stage ('League stage', 'Playoffs', 'Final'), how many matches did the team play in that stage? Include combinations with zero matches.",
   sql="""SELECT t.team_code, s.stage, COUNT(m.match_id) FROM teams t
          CROSS JOIN (SELECT DISTINCT stage FROM matches) s
          LEFT JOIN matches m ON m.stage = s.stage
                             AND t.team_code IN (m.bat_first_team, m.bowl_first_team)
          GROUP BY t.team_code, s.stage"""),

 dict(id=77, diff="hard", cat=["full-join", "null", "aggregate"],
   q="How many players appear in exactly one of batting_stats and bowling_stats (in one but not the other)?",
   sql="""SELECT COUNT(*) FROM batting_stats b FULL OUTER JOIN bowling_stats s ON s.player_id = b.player_id
          WHERE b.player_id IS NULL OR s.player_id IS NULL"""),

 dict(id=78, diff="hard", cat=["semi-join", "subquery", "domain"],
   q="Which teams (full names) had at least one player score a century (100+ runs off the bat in one match, regular innings)?",
   sql="""SELECT t.team_name FROM teams t
          WHERE EXISTS (SELECT 1 FROM deliveries d WHERE d.batting_team = t.team_code AND d.innings <= 2
                        GROUP BY d.match_id, d.striker_id HAVING SUM(d.runs_of_bat) >= 100)"""),

 dict(id=79, diff="hard", cat=["anti-join", "semi-join", "domain"],
   q="How many players whose role is 'Bowler' bowled at least one delivery but never took a bowler-credited wicket?",
   sql=f"""SELECT COUNT(*) FROM players p WHERE p.role = 'Bowler'
           AND EXISTS (SELECT 1 FROM deliveries d WHERE d.bowler_id = p.player_id)
           AND NOT EXISTS (SELECT 1 FROM deliveries d WHERE d.bowler_id = p.player_id AND {BOWLER_WKT})"""),

 dict(id=80, diff="hard", cat=["anti-join", "multi-join", "null"],
   q="Which venues with a known home team never saw that home team win there, according to match_results? Give the stadium names.",
   sql="""SELECT v.venue_stadium FROM venues v WHERE v.home_team IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM matches m JOIN match_results r ON r.match_id = m.match_id
                          WHERE m.venue_id = v.venue_id AND r.match_winner = v.home_team)"""),

 dict(id=81, diff="hard", cat=["left-join", "subquery", "join"],
   q="For which teams (team code) does the number of wins in the points table differ from the number of wins recorded in match_results? Give the team code, points-table wins and match_results wins.",
   sql="""SELECT pt.team_code, pt.wins, COUNT(r.match_id) AS result_wins FROM points_table pt
          LEFT JOIN match_results r ON r.match_winner = pt.team_code
          GROUP BY pt.team_code HAVING pt.wins != COUNT(r.match_id)"""),

 dict(id=82, diff="hard", cat=["join", "cte", "domain"],
   q="In how many matches does match_results.highscore differ from the runs off the bat that the listed top scorer actually made in that match according to deliveries (regular innings only)?",
   sql="""WITH s AS (SELECT match_id, striker_id, SUM(runs_of_bat) AS r FROM deliveries
                     WHERE innings <= 2 GROUP BY match_id, striker_id)
          SELECT COUNT(*) FROM match_results mr
          JOIN s ON s.match_id = mr.match_id AND s.striker_id = mr.top_scorer_id
          WHERE mr.highscore != s.r"""),

 dict(id=83, diff="hard", cat=["multi-join", "group", "order", "domain"],
   q="What was the most expensive single over of the season (total runs in one over of one innings, regular innings)? Give the bowler's name, the city it was bowled in, and the runs.",
   sql=f"""SELECT p.player_name, v.city, SUM({RUNS}) AS r FROM deliveries d
           JOIN players p ON p.player_id = d.bowler_id
           JOIN matches m ON m.match_id = d.match_id JOIN venues v ON v.venue_id = m.venue_id
           WHERE d.innings <= 2 GROUP BY d.match_id, d.innings, d.over_no, d.bowler_id
           ORDER BY r DESC LIMIT 1"""),

 dict(id=84, diff="hard", cat=["role-join", "group", "having", "subquery"],
   q="How many distinct bowler-batter pairs are there where the bowler dismissed that batter two or more times (bowler-credited wickets only)?",
   sql=f"""SELECT COUNT(*) FROM (SELECT d.bowler_id, d.player_dismissed_id FROM deliveries d
                                 WHERE {BOWLER_WKT}
                                 GROUP BY d.bowler_id, d.player_dismissed_id HAVING COUNT(*) >= 2)"""),

 dict(id=85, diff="hard", cat=["set-op", "join", "cte", "window", "tie"],
   q="Which team(s) used the most different players this season (anyone who batted, bowled or fielded for it)? Return all tied teams (full names) with the number of players.",
   sql="""WITH used AS (SELECT batting_team AS team, striker_id AS pid FROM deliveries
                        UNION SELECT bowling_team, bowler_id FROM deliveries
                        UNION SELECT d.bowling_team, f.player_id FROM delivery_fielders f
                              JOIN deliveries d ON d.delivery_id = f.delivery_id),
               c AS (SELECT team, COUNT(*) AS n, RANK() OVER (ORDER BY COUNT(*) DESC) AS rk
                     FROM used GROUP BY team)
          SELECT t.team_name, c.n FROM c JOIN teams t ON t.team_code = c.team WHERE c.rk = 1"""),

 # ================= BRUTAL (stacked traps) =================
 dict(id=86, diff="brutal", cat=["window", "cte", "join", "date", "domain"],
   q="Which team had the biggest increase in its innings total (runs off the bat plus extras, regular innings) from one match to its next match in date order? Ignore matches marked abandoned in match_results. Give the full team name and the increase.",
   sql=f"""WITH t AS (SELECT d.match_id, d.batting_team, SUM({RUNS}) AS r FROM deliveries d
                      WHERE d.innings <= 2 AND {NOT_ABANDONED}
                      GROUP BY d.match_id, d.batting_team),
                g AS (SELECT t.batting_team,
                             t.r - LAG(t.r) OVER (PARTITION BY t.batting_team ORDER BY m.date, m.match_id) AS diff
                      FROM t JOIN matches m ON m.match_id = t.match_id)
           SELECT tm.team_name, g.diff FROM g JOIN teams tm ON tm.team_code = g.batting_team
           ORDER BY g.diff DESC LIMIT 1"""),

 dict(id=87, diff="brutal", cat=["window", "cte", "null"],
   q="What is the median first-innings score in match_results (ignore matches without a score)? With an even count, the median is the average of the two middle values.",
   sql="""WITH s AS (SELECT first_ings_score AS x,
                            ROW_NUMBER() OVER (ORDER BY first_ings_score) AS rn,
                            COUNT(*) OVER () AS n
                     FROM match_results WHERE first_ings_score IS NOT NULL)
          SELECT AVG(x) FROM s WHERE rn IN ((n + 1) / 2, (n + 2) / 2)"""),

 dict(id=88, diff="brutal", cat=["cte", "left-join", "null", "domain"],
   q="How many ducks were there this season? A duck is a player dismissed in a match (regular innings, excluding 'retired hurt') who scored zero runs off the bat in that match, including players dismissed without facing a ball.",
   sql="""WITH dis AS (SELECT DISTINCT match_id, player_dismissed_id AS pid FROM deliveries
                       WHERE player_dismissed_id IS NOT NULL AND wicket_type != 'retired hurt' AND innings <= 2),
               runs AS (SELECT match_id, striker_id AS pid, SUM(runs_of_bat) AS r FROM deliveries
                        WHERE innings <= 2 GROUP BY match_id, striker_id)
          SELECT COUNT(*) FROM dis LEFT JOIN runs ON runs.match_id = dis.match_id AND runs.pid = dis.pid
          WHERE COALESCE(runs.r, 0) = 0"""),

 dict(id=89, diff="brutal", cat=["cte", "anti-join", "join", "domain"],
   q="What is the highest score by a batter who was NOT dismissed in that match (a not-out innings, regular innings only)? Give the name and runs.",
   sql="""WITH s AS (SELECT match_id, striker_id, SUM(runs_of_bat) AS r FROM deliveries
                     WHERE innings <= 2 GROUP BY match_id, striker_id)
          SELECT p.player_name, s.r FROM s JOIN players p ON p.player_id = s.striker_id
          WHERE NOT EXISTS (SELECT 1 FROM deliveries d WHERE d.match_id = s.match_id
                            AND d.player_dismissed_id = s.striker_id AND d.innings <= 2)
          ORDER BY s.r DESC LIMIT 1"""),

 dict(id=90, diff="brutal", cat=["cte", "join", "having", "domain"],
   q="Which bowler bowled the most maiden overs? A maiden is an over (same match, innings, over number and bowler; regular innings) with exactly 6 legal deliveries and zero runs conceded (byes and leg-byes are not charged). Give the name and count.",
   sql=f"""WITH o AS (SELECT d.bowler_id, SUM({CONCEDED}) AS conceded, SUM({LEGAL}) AS legal
                      FROM deliveries d WHERE d.innings <= 2
                      GROUP BY d.match_id, d.innings, d.over_no, d.bowler_id)
           SELECT p.player_name, COUNT(*) AS maidens FROM o JOIN players p ON p.player_id = o.bowler_id
           WHERE o.conceded = 0 AND o.legal = 6 GROUP BY p.player_id ORDER BY maidens DESC LIMIT 1"""),

 dict(id=91, diff="brutal", cat=["cte", "role-join", "domain"],
   q="How many times did a player score at least 30 runs off the bat AND take at least 2 bowler-credited wickets in the same match (regular innings)?",
   sql=f"""WITH bat AS (SELECT match_id, striker_id AS pid, SUM(runs_of_bat) AS r FROM deliveries
                        WHERE innings <= 2 GROUP BY match_id, striker_id),
                bowl AS (SELECT d.match_id, d.bowler_id AS pid, COUNT(*) AS w FROM deliveries d
                         WHERE d.innings <= 2 AND {BOWLER_WKT} GROUP BY d.match_id, d.bowler_id)
           SELECT COUNT(*) FROM bat JOIN bowl ON bowl.match_id = bat.match_id AND bowl.pid = bat.pid
           WHERE bat.r >= 30 AND bowl.w >= 2"""),

 dict(id=92, diff="brutal", cat=["cte", "left-join", "ratio", "domain"],
   q="Among batters with at least 250 runs off the bat (regular innings), who has the highest batting average (runs divided by number of times dismissed, excluding 'retired hurt')? Give the name and the average.",
   sql="""WITH r AS (SELECT striker_id AS pid, SUM(runs_of_bat) AS runs FROM deliveries
                     WHERE innings <= 2 GROUP BY striker_id HAVING SUM(runs_of_bat) >= 250),
               o AS (SELECT player_dismissed_id AS pid, COUNT(*) AS outs FROM deliveries
                     WHERE player_dismissed_id IS NOT NULL AND wicket_type != 'retired hurt' AND innings <= 2
                     GROUP BY player_dismissed_id)
          SELECT p.player_name, r.runs * 1.0 / o.outs AS bat_avg
          FROM r JOIN o ON o.pid = r.pid JOIN players p ON p.player_id = r.pid
          ORDER BY bat_avg DESC LIMIT 1"""),

 dict(id=93, diff="brutal", cat=["join", "ratio", "having", "domain"],
   q="Among bowlers with at least 10 bowler-credited wickets (regular innings), who has the best bowling strike rate (legal deliveries bowled per wicket)? Give the name and the strike rate.",
   sql=f"""SELECT p.player_name, SUM({LEGAL}) * 1.0 / SUM(CASE WHEN {BOWLER_WKT} THEN 1 ELSE 0 END) AS sr
           FROM deliveries d JOIN players p ON p.player_id = d.bowler_id WHERE d.innings <= 2
           GROUP BY p.player_id HAVING SUM(CASE WHEN {BOWLER_WKT} THEN 1 ELSE 0 END) >= 10
           ORDER BY sr ASC LIMIT 1"""),

 dict(id=94, diff="brutal", cat=["cte", "join", "null", "domain"],
   q="What was the lowest team innings total (runs off the bat plus extras, regular innings) this season, ignoring matches marked abandoned in match_results? Give the full team name and the total.",
   sql=f"""WITH t AS (SELECT d.match_id, d.innings, d.batting_team, SUM({RUNS}) AS r FROM deliveries d
                      WHERE d.innings <= 2 AND {NOT_ABANDONED}
                      GROUP BY d.match_id, d.innings, d.batting_team)
           SELECT tm.team_name, t.r FROM t JOIN teams tm ON tm.team_code = t.batting_team
           ORDER BY t.r ASC LIMIT 1"""),

 dict(id=95, diff="brutal", cat=["cte", "left-join", "null"],
   q="For how many players in batting_stats does the runs column differ from the runs off the bat they scored in deliveries during the matches covered by match_results?",
   sql="""WITH s AS (SELECT striker_id AS pid, SUM(runs_of_bat) AS r FROM deliveries
                     WHERE match_id IN (SELECT match_id FROM match_results) GROUP BY striker_id)
          SELECT COUNT(*) FROM batting_stats b LEFT JOIN s ON s.pid = b.player_id
          WHERE COALESCE(s.r, 0) != b.runs"""),

 dict(id=96, diff="brutal", cat=["cte", "many-to-many", "join", "domain"],
   q="How many times did a player take at least one catch AND score at least 50 runs off the bat in the same match (regular innings)?",
   sql="""WITH bat AS (SELECT match_id, striker_id AS pid FROM deliveries WHERE innings <= 2
                       GROUP BY match_id, striker_id HAVING SUM(runs_of_bat) >= 50),
               ct AS (SELECT DISTINCT d.match_id, f.player_id AS pid FROM delivery_fielders f
                      JOIN deliveries d ON d.delivery_id = f.delivery_id
                      WHERE d.wicket_type = 'caught' AND d.innings <= 2)
          SELECT COUNT(*) FROM bat JOIN ct ON ct.match_id = bat.match_id AND ct.pid = bat.pid"""),

 dict(id=97, diff="brutal", cat=["multi-join", "subquery", "left-join"],
   q="Who is the captain of the team with the highest net run rate in the points table, and how many runs off the bat did that captain score this season?",
   sql="""SELECT p.player_name, COALESCE(SUM(d.runs_of_bat), 0) FROM players p
          LEFT JOIN deliveries d ON d.striker_id = p.player_id
          WHERE p.is_captain = 1
            AND p.team_code = (SELECT team_code FROM points_table ORDER BY nrr DESC LIMIT 1)
          GROUP BY p.player_id"""),

 dict(id=98, diff="brutal", cat=["multi-join", "case", "ratio", "domain"],
   q="Among completed matches in match_results played at a venue that is the home ground (venues.home_team) of one of the two teams, what percentage were won by that venue's home team?",
   sql="""SELECT 100.0 * SUM(CASE WHEN r.match_winner = v.home_team THEN 1 ELSE 0 END) / COUNT(*)
          FROM match_results r JOIN matches m ON m.match_id = r.match_id
          JOIN venues v ON v.venue_id = m.venue_id
          WHERE r.match_result = 'completed' AND v.home_team IN (r.home_team, r.away_team)"""),

 dict(id=99, diff="brutal", cat=["role-join", "group", "order", "domain"],
   q="Which batter scored the most runs off the bat against a single bowler this season? Give the batter's name, the bowler's name and the runs.",
   sql="""SELECT s.player_name, b.player_name, SUM(d.runs_of_bat) AS r FROM deliveries d
          JOIN players s ON s.player_id = d.striker_id
          JOIN players b ON b.player_id = d.bowler_id
          GROUP BY d.striker_id, d.bowler_id ORDER BY r DESC LIMIT 1"""),

 dict(id=100, diff="brutal", cat=["role-join", "cte", "ratio", "order", "domain"],
   q="For which bowling team (full name) did overseas bowlers take the highest share of its bowler-credited wickets? Give the team and the percentage.",
   sql=f"""WITH w AS (SELECT d.bowling_team, b.nationality FROM deliveries d
                      JOIN players b ON b.player_id = d.bowler_id WHERE {BOWLER_WKT})
           SELECT t.team_name,
                  100.0 * SUM(CASE WHEN w.nationality = 'Overseas' THEN 1 ELSE 0 END) / COUNT(*) AS pct
           FROM w JOIN teams t ON t.team_code = w.bowling_team
           GROUP BY t.team_code ORDER BY pct DESC LIMIT 1"""),
]

if __name__ == "__main__":
    import sqlite3
    from collections import Counter
    from config import DB_PATH as DB
    conn = sqlite3.connect(DB); cur = conn.cursor()
    print(f"Validating {len(GOLDEN)} golden queries against {DB}\n")
    ok = 0
    for g in GOLDEN:
        try:
            rows = cur.execute(g["sql"]).fetchall()
            preview = rows[0] if rows else "(empty)"
            print(f"[{g['diff']:6}] #{g['id']:3}  OK  rows={len(rows):<3} sample={str(preview)[:55]}")
            ok += 1
        except Exception as e:
            print(f"[{g['diff']:6}] #{g['id']:3}  FAIL  {e}")
    print(f"\n{ok}/{len(GOLDEN)} passed")
    print("spread:", dict(Counter(g["diff"] for g in GOLDEN)))
    print("skills:", dict(Counter(c for g in GOLDEN for c in g["cat"]).most_common()))
    conn.close()
