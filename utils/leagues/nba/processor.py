from typing import Set, Dict, Optional, Union
from datetime import datetime
from collections import defaultdict
import os
import requests
import logging
from .extractor import extract_game_data, extract_players, parse_players, extract_game_status
from ..common.constants import STATUS_FINAL, STATUS_IN_PROGRESS, STATUS_SCHEDULED, NBA_LEAGUE_ID
from utils.s3_service import upload_to_s3
from ..common.helpers import parse_shot_stats, BASKETBALL_STAT_MAP, get_hasura_headers
import json
import pytz
from datetime import timedelta
from unidecode import unidecode
from thefuzz import process

# Create timezone objects
utc = pytz.UTC
pacific = pytz.timezone('US/Pacific')

logger = logging.getLogger(__name__)

def process_player_stats(player_stats: list) -> dict:
    """
    Process raw player statistics into a formatted dictionary.
    Each stat in player_stats is a list of [stat_name, abbreviation, value]
    """
    stats_dict = {}
    for stat in player_stats:
        stat_name = stat[1]  # Use abbreviation as key
        stat_value = stat[2]  # Raw value
        
        # Handle special cases
        if stat_name in ['FG', '3PT', 'FT']:
            # These stay as strings (e.g. "1-9")
            stats_dict[stat_name] = stat_value
        elif stat_name == '+/-':
            # Remove '+' sign if present and convert to int
            stats_dict[stat_name] = int(stat_value.replace('+', ''))
        else:
            # Convert all other stats to integers
            try:
                stats_dict[stat_name] = int(stat_value)
            except ValueError:
                stats_dict[stat_name] = 0
    
    return stats_dict


def process_game_data(game_id: str, current_date: datetime) -> Optional[Dict]:
    """Process individual game data and return player statistics."""
    try:
        data = extract_game_data(game_id)
        events = data.get("gamepackageJSON", {}).get("seasonseries", [{}])[0].get("events", [])

        game_status = extract_game_status(events, current_date)
        
        print(f"Game status: {game_status}, {game_id}")

        if game_status is None:
            logger.warning(f"Did not find game status for game {game_id}")
            return None

        players_data = extract_players(data)
        parsed_players = parse_players(players_data)
        upload_to_s3(parsed_players, f"NBA/PLAYERDATA/players_{game_id}.json")


        return {
            player["player_name"]: {**process_player_stats(player["player_statistics"]), 
                                  "game_status": game_status}
            for player in parsed_players
            if player.get("player_statistics")
        }

    except Exception as e:
        logger.error(f"Error processing game {game_id}: {str(e)}")
        return None

def update_betting_event(event: Dict, player_stats: Dict, updated_stat: float, testing_mode: bool, testing: str) -> Optional[Dict]:
    """Update or complete a betting event based on game status."""
    try:
        if (player_stats["game_status"] == STATUS_FINAL) or testing_mode and testing == "complete":
            response = requests.post(
                f"{os.getenv('BACKEND_URL')}/actions/complete-betting-event",
                headers=get_hasura_headers(),
                json={"actual_result": updated_stat, "betting_event_id": event["event_id"]}
            )
            response.raise_for_status()
            print("Event completed successfully")
            return None
        elif (player_stats["game_status"] == STATUS_IN_PROGRESS) or (testing_mode and testing == "in_progress"):
            return {**event, "result_numeric": str(updated_stat), "status": "IN_PROGRESS"}
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update betting event {event['event_id']}: {str(e)}")
        return None

def calculate_stat_value(stat_type: Union[str, dict, list], player_stats: Dict) -> float:
    """Calculate the stat value based on the stat type."""

    if isinstance(stat_type, list):
        return sum(player_stats[stat] for stat in stat_type)
    elif isinstance(stat_type, dict):
        if stat_type.get("calculator"):
            return stat_type["calculator"](player_stats)
        raw_stat = player_stats[stat_type["key"]]
        
        return parse_shot_stats(raw_stat, stat_type["made"])
        
    return player_stats[stat_type]

def process_boxscores(game_ids: Set[str], current_date: datetime, testing_mode: bool, testing: str) -> Dict:
    """Process all game boxscores and update betting events."""
    print(f"\nProcessing NBA boxscores for {len(game_ids)} games...")
    print(f"Testing mode: {testing}")

    scraper_complete = False

    players = {}
    for game_id in game_ids:
        print(f"\nProcessing game {game_id}...")
        game_data = process_game_data(game_id, current_date)

        # with open(f"players_nba_{game_id}.json", "w") as f:
        #     json.dump(game_data, f)
       
        if game_data:
            print(f"Found {len(game_data)} players with stats")
            players.update(game_data)
        else:
            print(f"No game data found for game {game_id}")

    try:
        print("\nFetching active betting events...")
        response = requests.get(
            f"{os.getenv('BACKEND_URL')}/api/rest/getactivebettingevents",
            headers=get_hasura_headers()
        )
        response.raise_for_status()
        betting_events = response.json()["betting_events"]
        print(f"Found {len(betting_events)} active betting events")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch active betting events: {str(e)}")
        return players

    new_betting_events = []
    print("\nProcessing betting events...")
    for event in betting_events:
        if int(event["league"]) != NBA_LEAGUE_ID:
            continue

        print(f"\nChecking event for {event['player_name']} - {event['stat_type']}")
        
        if event["status"] != "IN_PROGRESS" and event["status"] != "NOT_STARTED":
            print("Event is already complete, skipping")
            continue

        utc_time = current_date.astimezone(utc)
        normalized_name = unidecode(event["player_name"])
        print(f"Normalized name: {normalized_name}")
        
        # Fuzzy matching for player name
        player_match = None
        if normalized_name not in players:
            print("Exact match not found, trying fuzzy matching...")
            player_names = list(players.keys())
            if player_names:
                # Find the best match with a score
                best_match, score = process.extractOne(normalized_name, player_names)
                print(f"Best match: {best_match} with score {score}")
                
                # Use the match if the score is high enough (adjust threshold as needed)
                if score >= 85:  # 85% similarity threshold
                    player_match = best_match
                    print(f"Using fuzzy match: {player_match}")
        else:
            player_match = normalized_name
            
        if not player_match:
            try:
                event_time = datetime.fromisoformat(event["start_time"].replace('Z', '+00:00'))
                print(f"Event time: {event_time}, utc time: {utc_time}")
                if event_time + timedelta(hours=3) < utc_time:
                    print("Player not found in game data, categorizing them as DNP")
                    print("Event", event)
                    try:
                        response = requests.post(
                            f"{os.getenv('BACKEND_URL')}/actions/set-dnp",
                            headers=get_hasura_headers(),
                            json={"betting_event_id": event["event_id"]}
                        )
                        response.raise_for_status()
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Failed to set DNP for event {event['event_id']}: {str(e)}")
                else:
                    print("Player not found in game data but game hasn't started, skipping")
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing event time for event {event['event_id']}: {str(e)}")
                print(f"Error parsing event time: {str(e)}")
            continue
        
        stat_type = BASKETBALL_STAT_MAP.get(event["stat_type"])
        if not stat_type:
            print(f"Stat type {event['stat_type']} not found in BASKETBALL_STAT_MAP")
            continue

        print("Calculating updated stat value...")
        updated_stat = calculate_stat_value(stat_type, players[player_match])
        print(f"New stat value: {updated_stat}")
        
        print("Updating betting event...")
        updated_event = update_betting_event(event, players[event["player_name"]], updated_stat, testing_mode, testing)
        
        if updated_event:
            new_betting_events.append(updated_event)
        else:
            scraper_complete = True
            print("No update needed")

    print(f"\nProcessed all events. {len(new_betting_events)} events to update")
    
    if new_betting_events:
        try:
            updates = []
            for event in new_betting_events:
                update_obj = {
                    "where": { "event_id": { "_eq": event["event_id"] } },
                    "_set": {
                        "result_numeric": event["result_numeric"],
                        "status": event["status"]
                    }
                }
                updates.append(update_obj)

            # Prepare the GraphQL payload
            payload = {
                "query": """
                    mutation updateBettingEventsMany($updates: [betting_events_updates!]!) {
                    update_betting_events_many(updates: $updates) {
                        affected_rows
                        returning {
                        event_id
                        result_numeric
                        status
                        }
                    }
                    }
                """,
                "variables": {
                    "updates": updates
                }
            }

            # Define headers and URL (make sure environment variables are set accordingly)
            url = f"https://lasting-scorpion-21.hasura.app/v1/graphql"
            headers = {
                "Content-Type": "application/json",
                "x-hasura-admin-secret": "DHieJhzOpml0wBIbEZC5mvsDdSKMnyMC4b8Kx04p0adKUO0zd2e2LSganKK6CRAb"
            }

            # Send the POST request
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != [200, 201]:
                logger.error(f"Failed to bulk update betting events: {response.json()}")
                print(f"Bulk update failed: {response.json()}")
            else: 
                scraper_complete = True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to bulk update betting events: {str(e)}")
            print(f"Bulk update failed: {str(e)}")
            scraper_complete = False
    return scraper_complete 


