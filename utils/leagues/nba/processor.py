from typing import Set, Dict, Optional, Union
from datetime import datetime
from collections import defaultdict
import os
import requests
import logging
from .extractor import extract_game_data, extract_players, parse_players, extract_game_status
from ..common.constants import STATUS_FINAL, STATUS_IN_PROGRESS, STATUS_SCHEDULED, NBA_LEAGUE_ID
from utils.s3_service import upload_to_s3
from ..common.helpers import parse_shot_stats, get_headers, NBA_STAT_MAP, get_hasura_headers
import json
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

def update_betting_event(event: Dict, player_stats: Dict, updated_stat: float, testing_mode, testing: str) -> Optional[Dict]:
    """Update or complete a betting event based on game status."""
    try:
        if (player_stats["game_status"] == STATUS_FINAL) or testing_mode and testing == "complete":
            response = requests.post(
                f"{os.getenv('BACKEND_URL')}/actions/complete-betting-event",
                headers=get_hasura_headers(),
                json={"actual_result": updated_stat, "betting_event_id": event["event_id"]}
            )
            response.raise_for_status()
            return None
        elif (player_stats["game_status"] == STATUS_IN_PROGRESS) or (testing_mode and testing == "in_progress"):
            return {**event, "result": str(updated_stat), "status": "IN_PROGRESS"}
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

    players = {}
    for game_id in game_ids:
        print(f"\nProcessing game {game_id}...")
        game_data = process_game_data(game_id, current_date)
        with open(f"players_{game_id}.json", "w") as f:
            json.dump(game_data, f)
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
        
        if event["player_name"] not in players and event["start_time"] < current_date:
            print("Player not found in game data, categorizing them as DNP")
            response = requests.post(
                f"{os.getenv('BACKEND_URL')}/actions/set-dnp",
                headers=get_hasura_headers(),
                json={"betting_event_id": event["event_id"]}
            )
            response.raise_for_status()
            continue
   
        stat_type = NBA_STAT_MAP.get(event["stat_type"])
        if not stat_type:
            print(f"Stat type {event['stat_type']} not found in NBA_STAT_MAP")
            continue

        print("Calculating updated stat value...")
        updated_stat = calculate_stat_value(stat_type, players[event["player_name"]])
        print(f"New stat value: {updated_stat}")
        
        print("Updating betting event...")
        updated_event = update_betting_event(event, players[event["player_name"]], updated_stat, testing_mode, testing)
        
        if updated_event:
            print("Event updated successfully")
            new_betting_events.append(updated_event)
        else:
            print("No update needed or event completed")

    print(f"\nProcessed all events. {len(new_betting_events)} events to update")
    
    if new_betting_events:
        try:
            print("Sending bulk update request...")
            response = requests.post(
                f"{os.getenv('BACKEND_URL')}/api/rest/updatebettingeventsmany",
                headers=get_headers(),
                json=new_betting_events
            )
            response.raise_for_status()
            print("Bulk update successful")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to bulk update betting events: {str(e)}")
            print(f"Bulk update failed: {str(e)}")

    return players



