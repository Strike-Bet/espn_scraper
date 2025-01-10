from typing import Set, Dict
from datetime import datetime
from ..common.constants import STATUS_IN_PROGRESS, STATUS_FINAL, STATUS_SCHEDULED
from .extractor import extract_game_data, extract_players, parse_players, extract_game_status
from utils.s3_service import upload_to_s3
from utils.leagues.nfl.update_results import update_results
import json

def process_boxscores(game_ids: Set[str], current_date: datetime, testing: bool = False) -> Dict:
    all_data = {}
    game_statuses = {}

    for game_id in game_ids:
        
        try:
            # Skip if game is already final
            if game_statuses.get(game_id) == STATUS_FINAL and not testing:
                print(f"Game {game_id} is final")
                continue

            # Fetch and process game data
            data = extract_game_data(game_id)

            # Upload raw boxscore to S3 if not testing
            if not testing:
                upload_to_s3(data, f"NFL/NFL_BOXSCORES/boxscore_{game_id}.json")

            # Process game events and status
            event = data.get("gamepackageJSON", {}).get("header", [{}]).get("competitions", [])[0]
            
            # Override status for testing
            if testing:
                event["status"]["type"]["name"] = STATUS_IN_PROGRESS
                print(f"Testing mode: Setting game {game_id} status to {STATUS_IN_PROGRESS}")

            # Update game status
            
            status = extract_game_status(event, current_date)
            game_statuses[game_id] = status if not testing else STATUS_IN_PROGRESS

            

            # # Process player data
            players_data = extract_players(data)


            if len(players_data) != 2:
                if game_statuses.get(game_id) == STATUS_SCHEDULED:
                    print(f"Game {game_id} has not started yet")
                else:
                    print(f"Error: Player data not found for game {game_id}")
                continue

            # # Upload and process player data
            if not testing:
                upload_to_s3(players_data, f"NFL/NFL_PLAYERDATA/players_{game_id}.json")
            parsed_players = parse_players(players_data)
            all_data[game_id] = parsed_players

           

            # # Handle betting updates based on game status
            status = game_statuses.get(game_id)
            
            if status == STATUS_FINAL and not testing:
                update_results(parsed_players, closed=True)
            elif status == STATUS_IN_PROGRESS or testing:
                update_results(parsed_players, closed=False)

        except Exception as e:
            print(f"Error processing game {game_id}: {e}")
            continue

    return all_data
    