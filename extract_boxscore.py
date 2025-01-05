import requests
import json
import os
from datetime import datetime, timedelta


current_date = datetime.utcnow()  # Use UTC time to avoid discrepancies
formatted_date = current_date.strftime("%Y-%m-%dT00:00:00Z")


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
           

           # Step 2: Extract events safely
            events = data.get("gamepackageJSON", {}).get("seasonseries", [{}])[0].get("events", [])

            # Step 3: Process each event
            for event in events:
                event_date = event.get("date", "")
                
                # Check if the event date is within the same day or the next day (to account for UTC differences)
                event_datetime = datetime.strptime(event_date, "%Y-%m-%dT%H:%M:%SZ")
                if current_date.date() <= event_datetime.date() <= (current_date + timedelta(days=1)).date():
                    
                    # Extract and handle the `statusType`
                    status_type = event.get("statusType", {})
                    status_name = status_type.get("name", "")

                    if status_name == "STATUS_IN_PROGRESS":
                        print(f"Game {event.get('id')} is in progress")
                    elif status_name == "STATUS_SCHEDULED":
                        print(f"Game {event.get('id')} is scheduled")
                    elif status_name == "STATUS_HALFTIME":
                        print(f"Game {event.get('id')} is at halftime")
                    elif status_name == "STATUS_FINAL":
                        print(f"Game {event.get('id')} is final")
                    else:
                        print(f"Game {event.get('id')} has an unknown status: {status_name}")
                    



            players_data = extract_players(data)

            if len(players_data) == 2:
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
                print(f"Skipping gameId {game_id} due to unexpected number of players: {len(players_data)}")
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