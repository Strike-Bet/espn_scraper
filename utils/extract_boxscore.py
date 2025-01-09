import requests
import json
import os
from datetime import datetime, timedelta
from typing import Set
from utils.close_bet import close_bet  
from utils.update_results import update_results
from utils.s3_service import upload_to_s3

S3_URL = os.getenv('S3_URL')
BOXSCORE_URL = os.getenv('BOXSCORE_URL')
GO_BACKEND_URL = os.getenv('GO_BACKEND_URL')


GAMEID_STATUS = {}


def extract_players(input_data):
    """
    Extracts the 'players' section from the input JSON and returns it.
    """
    return input_data.get("gamepackageJSON", {}).get("boxscore", {}).get("players", [])

def parse_players(players_data):
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

def process_game_status(event: dict, game_id: str, current_date: datetime) -> None:
    """Process game status from event data and update GAMEID_STATUS."""
    event_date = event.get("date", "")
    event_datetime = datetime.strptime(event_date, "%Y-%m-%dT%H:%M:%SZ")
    
    # Check if event is within current day or next day (UTC differences)
    if current_date.date() <= event_datetime.date() <= (current_date + timedelta(days=1)).date():
        status_name = event.get("statusType", {}).get("name", "")
        GAMEID_STATUS[game_id] = status_name
        print(f"Game {game_id} status: {status_name}")

def handle_player_data(game_id: str, parsed_players: list) -> None:
    """Handle player data based on game status."""
    status = GAMEID_STATUS.get(game_id)
    
    if status == "STATUS_FINAL":
        print(f"Game {game_id} is final")
        close_bet(parsed_players)
    elif status == "STATUS_IN_PROGRESS":
        print(f"Game {game_id} is in progress")
        update_results(parsed_players)
    else:
        print(f"Game {game_id} is not final")

def fetch_and_process_boxscores(game_ids: Set[str], current_date: datetime, testing: bool = False) -> dict:
    """
    Fetches boxscore data for game IDs, extracts player data, and saves it to a final JSON file.
    """
    all_data = {}

    for game_id in game_ids:
        # Skip if game is already final
        if GAMEID_STATUS.get(game_id) == "STATUS_FINAL":
            print(f"Game {game_id} is final")
            continue

        # Fetch boxscore data
        url = f"{BOXSCORE_URL}/boxscore?xhr=1&gameId={game_id}"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to fetch data for gameId {game_id}: {response.status_code}")
            continue

        print(f"Processing gameId: {game_id}")
        data = response.json()

        # Upload boxscore to S3
        try:
            upload_status = upload_to_s3(data, f"NBA/NBA_BOXSCORES/boxscore_{game_id}.json")
            print(f"Boxscore uploaded to s3: {upload_status}")
        except Exception as e:
            print(f"Error uploading boxscore to s3: {e}")

        # Process game events and status
        events = data.get("gamepackageJSON", {}).get("seasonseries", [{}])[0].get("events", [])

        #for testing 
        if testing: 
            for event in events: 
                event["statusType"]["name"] = "STATUS_IN_PROGRESS"


        for event in events:
            process_game_status(event, game_id, current_date)

        # Process player data
        players_data = extract_players(data)
        if len(players_data) != 2:
            if GAMEID_STATUS.get(game_id) == "STATUS_SCHEDULED":
                print(f"Game {game_id} has not started yet")
            else:
                print(f"Error: Player data not found for game {game_id}")
            continue

        # Upload and process player data
        upload_to_s3(players_data, f"NBA/PLAYERDATA/players_{game_id}.json")
        parsed_players = parse_players(players_data)
        all_data[game_id] = parsed_players
        
        handle_player_data(game_id, parsed_players)

    return all_data
