# import requests
# import datetime
# import json
# import os

# def fetch_scoreboard_and_extract_game_ids():
#     """
#     Fetches the current NBA scoreboard JSON, saves it to 'all_current_games.json',
#     and extracts unique game IDs to 'game_ids.txt'.
#     """
#     # Get the current date in the required format: YYYYMMDD
#     current_date = datetime.datetime.now().strftime("%Y%m%d")

#     # URL with the current date
#     url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?region=us&lang=en&contentorigin=espn&calendartype=offdays&includeModules=videos&dates={current_date}&tz=America%2FNew_York"

#     # Fetch the JSON data
#     response = requests.get(url)
#     if response.status_code == 200:
#         # Save JSON data
#         data = response.json()
#         with open("all_current_games.json", "w") as json_file:
#             json.dump(data, json_file, indent=4)
#         print(f"JSON data for date {current_date} has been saved to 'all_current_games.json'.")

#         # Extract game IDs
#         game_ids = set()
#         events = data.get("events", [])
#         for event in events:
#             competitions = event.get("competitions", [])
#             for competition in competitions:
#                 competition_id = competition.get("id")
#                 if competition_id:
#                     game_ids.add(competition_id)

#         # Save game IDs to a file
#         if game_ids:
#             with open("game_ids.txt", "w") as game_ids_file:
#                 for game_id in game_ids:
#                     game_ids_file.write(game_id + "\n")
#             print(f"Extracted game IDs: {game_ids}")
#             print("All game IDs have been saved to 'game_ids.txt'.")
#         else:
#             print("No game IDs found.")
#     else:
#         print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")

# def extract_players(input_data):
#     """
#     Extracts the 'players' section from the input JSON and returns it.
#     """
#     return input_data.get("gamepackageJSON", {}).get("boxscore", {}).get("players", [])

# def parse_players(players_data, team_0_abbrev, team_1_abbrev):
#     """
#     Processes the 'players' data and returns a list of player dictionaries.
#     """
#     all_players = []
#     if len(players_data) == 2:
#         for i in range(len(players_data)):
#             team_abbrev = players_data[i]["team"]["abbreviation"]
#             opp_abbrev = players_data[1 - i]["team"]["abbreviation"]

#             for stats_obj in players_data[i].get("statistics", []):
#                 keys = stats_obj.get("keys", [])
#                 names = stats_obj.get("names", [])
#                 athletes = stats_obj.get("athletes", [])

#                 for athlete in athletes:
#                     player_name = athlete["athlete"]["displayName"]
#                     starter = athlete.get("starter", False)
#                     did_not_play = athlete.get("didNotPlay", False)
#                     ejected = athlete.get("ejected", False)
#                     active = athlete.get("active", False)
#                     reason = athlete.get("reason", "")
#                     jersey = athlete["athlete"].get("jersey", "")

#                     athlete_stats = athlete.get("stats", [])
#                     player_stats_list = []
#                     if athlete_stats and len(athlete_stats) == len(keys):
#                         for full_name, abbrev, stat_value in zip(keys, names, athlete_stats):
#                             player_stats_list.append([full_name, abbrev, stat_value])

#                     player_dict = {
#                         "team": team_abbrev,
#                         "opposing_team": opp_abbrev,
#                         "player_name": player_name,
#                         "player_metadata": {
#                             "starter": starter,
#                             "didNotPlay": did_not_play,
#                             "ejected": ejected,
#                             "active": active,
#                             "reason": reason,
#                             "jersey": jersey,
#                         },
#                         "player_statistics": player_stats_list,
#                     }
#                     all_players.append(player_dict)

#     return all_players

# def fetch_and_process_boxscores(game_ids_file, output_dir, final_output_file):
#     """
#     Fetches boxscore data for game IDs, extracts player data, and saves it to a final JSON file.
#     """
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)

#     with open(game_ids_file, "r") as f:
#         game_ids = [line.strip() for line in f]

#     all_data = {}

#     for game_id in game_ids:
#         url = f"https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId={game_id}"
#         response = requests.get(url)

#         if response.status_code == 200:
#             print(f"Processing gameId: {game_id}")
#             data = response.json()

#             # Extract 'players' data
#             players_data = extract_players(data)

#             # Save players.json for this game
#             players_file = os.path.join(output_dir, f"players_{game_id}.json")
#             with open(players_file, "w") as f:
#                 json.dump(players_data, f, indent=4)

#             # Parse players and add to the final dataset
#             team_0_abbrev = players_data[0]["team"]["abbreviation"]
#             team_1_abbrev = players_data[1]["team"]["abbreviation"]
#             parsed_players = parse_players(players_data, team_0_abbrev, team_1_abbrev)

#             all_data[game_id] = parsed_players
#         else:
#             print(f"Failed to fetch data for gameId {game_id}: {response.status_code}")

#     # Save the final aggregated data
#     with open(final_output_file, "w") as f:
#         json.dump(all_data, f, indent=4)

# if __name__ == "__main__":
#     GAME_IDS_FILE = "game_ids.txt"
#     OUTPUT_DIR = "players_data"
#     FINAL_OUTPUT_FILE = "boxscores_final.json"

#     # Step 1: Fetch scoreboard and extract game IDs
#     fetch_scoreboard_and_extract_game_ids()

#     # Step 2: Fetch boxscores and process player data
#     fetch_and_process_boxscores(GAME_IDS_FILE, OUTPUT_DIR, FINAL_OUTPUT_FILE)

#     print(f"All data has been aggregated and saved to {FINAL_OUTPUT_FILE}.")


import requests
import json
import os

def extract_players(input_data):
    """
    Extracts the 'players' section from the input JSON and returns it.
    """
    return input_data.get("gamepackageJSON", {}).get("boxscore", {}).get("players", [])

def parse_players(players_data, team_0_abbrev, team_1_abbrev):
    """
    Processes the 'players' data and returns a list of player dictionaries.
    """
    all_players = []
    if len(players_data) == 2:
        for i in range(len(players_data)):
            team_abbrev = players_data[i]["team"]["abbreviation"]
            opp_abbrev = players_data[1 - i]["team"]["abbreviation"]

            for stats_obj in players_data[i].get("statistics", []):
                keys = stats_obj.get("keys", [])
                names = stats_obj.get("names", [])
                athletes = stats_obj.get("athletes", [])

                for athlete in athletes:
                    player_name = athlete["athlete"]["displayName"]
                    starter = athlete.get("starter", False)
                    did_not_play = athlete.get("didNotPlay", False)
                    ejected = athlete.get("ejected", False)
                    active = athlete.get("active", False)
                    reason = athlete.get("reason", "")
                    jersey = athlete["athlete"].get("jersey", "")

                    athlete_stats = athlete.get("stats", [])
                    player_stats_list = []
                    if athlete_stats and len(athlete_stats) == len(keys):
                        for full_name, abbrev, stat_value in zip(keys, names, athlete_stats):
                            player_stats_list.append([full_name, abbrev, stat_value])

                    player_dict = {
                        "team": team_abbrev,
                        "opposing_team": opp_abbrev,
                        "player_name": player_name,
                        "player_metadata": {
                            "starter": starter,
                            "didNotPlay": did_not_play,
                            "ejected": ejected,
                            "active": active,
                            "reason": reason,
                            "jersey": jersey,
                        },
                        "player_statistics": player_stats_list,
                    }
                    all_players.append(player_dict)

    return all_players

def fetch_and_process_boxscores(game_ids_file, output_dir, final_output_file):
    """
    Fetches boxscore data for game IDs, extracts player data, and saves it to a final JSON file.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(game_ids_file, "r") as f:
        game_ids = [line.strip() for line in f]

    all_data = {}

    for game_id in game_ids:
        url = f"https://cdn.espn.com/core/nba/boxscore?xhr=1&gameId={game_id}"
        response = requests.get(url)

        if response.status_code == 200:
            print(f"Processing gameId: {game_id}")
            data = response.json()

            # Extract 'players' data
            players_data = extract_players(data)

            # Save players.json for this game
            players_file = os.path.join(output_dir, f"players_{game_id}.json")
            with open(players_file, "w") as f:
                json.dump(players_data, f, indent=4)

            # Parse players and add to the final dataset
            team_0_abbrev = players_data[0]["team"]["abbreviation"]
            team_1_abbrev = players_data[1]["team"]["abbreviation"]
            parsed_players = parse_players(players_data, team_0_abbrev, team_1_abbrev)

            all_data[game_id] = parsed_players
        else:
            print(f"Failed to fetch data for gameId {game_id}: {response.status_code}")

    # Save the final aggregated data
    with open(final_output_file, "w") as f:
        json.dump(all_data, f, indent=4)

if __name__ == "__main__":
    GAME_IDS_FILE = "game_ids.txt"
    OUTPUT_DIR = "players_data"
    FINAL_OUTPUT_FILE = "boxscores_final.json"

    fetch_and_process_boxscores(GAME_IDS_FILE, OUTPUT_DIR, FINAL_OUTPUT_FILE)
    print(f"All data has been aggregated and saved to {FINAL_OUTPUT_FILE}.")