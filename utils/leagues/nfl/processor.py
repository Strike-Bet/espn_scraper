from typing import Set, Dict, Optional, Union
from datetime import datetime
import os
import json
import requests
import logging
from .extractor import extract_game_data, extract_players, parse_players, extract_game_status
from ..common.constants import STATUS_FINAL, STATUS_IN_PROGRESS, STATUS_SCHEDULED, NFL_LEAGUE_ID
from utils.s3_service import upload_to_s3
from ..common.helpers import get_hasura_headers, NFL_STAT_MAP
import pytz
from datetime import timedelta

logger = logging.getLogger(__name__)

def process_player_stats(player_statistics: dict) -> dict:
    """Process raw player statistics into a formatted dictionary."""
    stats_dict = {}
    for stat_item in player_statistics:
        try:
            stats_dict[stat_item[0]] = float(stat_item[2]) if stat_item[1] else 0.0
        except (ValueError, TypeError):
            stats_dict[stat_item[0]] = 0.0
    return stats_dict

def process_game_data(game_id: str, current_date: datetime) -> Optional[Dict]:
    """Process individual game data and return player statistics."""
    try:
        data = extract_game_data(game_id)
        event = data.get("gamepackageJSON", {}).get("header", [{}]).get("competitions", [])[0]
        game_status = extract_game_status(event, current_date)

        if game_status is None:
            logger.warning(f"Did not find game status for game {game_id}")
            return None

        players_data = extract_players(data)
       
        upload_to_s3(players_data, f"NFL/NFL_PLAYERDATA/players_{game_id}.json")
        parsed_players = parse_players(players_data)

        return {
            player["player_name"]: {
                **process_player_stats(player["player_statistics"]),
                "game_status": game_status
            }
            for player in parsed_players
            if player.get("player_statistics")
        }

    except Exception as e:
        logger.error(f"Error processing game {game_id}: {str(e)}")
        return None

def update_betting_event(event: Dict, player_stats: Dict, updated_stat: float, testing: str, testing_mode: bool) -> Optional[Dict]:
    """Update or complete a betting event based on game status."""
    try:
        print("player_stats", player_stats)
        if (player_stats["game_status"] == STATUS_FINAL and event["in_progress"]) or (player_stats["game_status"] == STATUS_SCHEDULED) or testing == "complete":
            print("completed betting event")
            response = requests.post(
                f"{os.getenv('BACKEND_URL')}/actions/complete-betting-event",
                headers=get_hasura_headers(),
                json={"actual_result": updated_stat, "betting_event_id": event["event_id"]}
            )
            response.raise_for_status()
            return None
        elif (player_stats["game_status"] == STATUS_IN_PROGRESS) or (testing_mode and testing == "in_progress"):
            return {**event, "result_numeric": str(updated_stat), "status": "IN_PROGRESS"}
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update betting event {event['event_id']}: {str(e)}")
        return None

def calculate_stat_value(stat_type: str, player_stats: Dict) -> float:
    """Calculate the stat value based on the stat type."""
    if "+" in stat_type:
        # Handle combined stats (e.g., "passingYards+rushingYards")
        return sum(float(player_stats.get(key, 0)) for key in stat_type.split("+"))
    elif "/" in stat_type:
        # Handle ratio stats (e.g., "completions/passingAttempts")
        numerator, denominator = stat_type.split("/")
        if float(player_stats.get(denominator, 0)) != 0:
            return float(player_stats.get(numerator, 0))
        return 0
    return float(player_stats.get(stat_type, 0))

def process_boxscores(game_ids: Set[str], current_date: datetime, testing: str, testing_mode: bool) -> Dict:
    """Process all game boxscores and update betting events."""
    players = {}
    for game_id in game_ids:
        game_data = process_game_data(game_id, current_date)
        if game_data:
            players.update(game_data)

    try:
        response = requests.get(
            f"{os.getenv('BACKEND_URL')}/api/rest/getactivebettingevents",
            headers=get_hasura_headers()
        )
        response.raise_for_status()

        betting_events = response.json()["betting_events"]
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch active betting events: {str(e)}")
        return players
    



    new_betting_events = []

    for event in betting_events:
        with open("events.json", "w") as f:
            json.dump(event, f)
        if int(event["league"]) != NFL_LEAGUE_ID:
            continue

        utc = pytz.UTC
        utc_time = current_date.astimezone(utc)

        if event["player_name"] not in players:
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
        
        
        stat_type = NFL_STAT_MAP.get(event["stat_type"])
        if not stat_type:
            logger.warning(f"Stat type {event['stat_type']} not found in NFL_STAT_MAP")
            continue

        updated_stat = calculate_stat_value(stat_type, players[event["player_name"]])
        updated_event = update_betting_event(event, players[event["player_name"]], updated_stat, testing, testing_mode)
        print("updated_event", updated_event)

        if updated_event:
            new_betting_events.append(updated_event)

        print("new_betting_events", new_betting_events)
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
                print("response", response.json())
                if response.status_code != [200, 201]:
                    logger.error(f"Failed to bulk update betting events: {response.json()}")
                    print(f"Bulk update failed: {response.json()}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to bulk update betting events: {str(e)}")
                print(f"Bulk update failed: {str(e)}")

    return players
    