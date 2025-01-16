from typing import Set, Dict, Optional, Union
from datetime import datetime
import os
import json
import requests
import logging
from .extractor import extract_game_data, extract_players, parse_players, extract_game_status
from ..common.constants import STATUS_FINAL, STATUS_IN_PROGRESS, STATUS_SCHEDULED
from utils.s3_service import upload_to_s3
from ..common.helpers import get_headers, NFL_STAT_MAP

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

def update_betting_event(event: Dict, player_stats: Dict, updated_stat: float, testing: str) -> Optional[Dict]:
    """Update or complete a betting event based on game status."""
    try:
        if (player_stats["game_status"] == STATUS_FINAL and event["in_progress"]) or testing == "complete":
            response = requests.post(
                f"{os.getenv('BACKEND_URL')}/api/betting-events/{event['event_id']}/complete",
                headers=get_headers(),
                json={"result": updated_stat}
            )
            response.raise_for_status()
            return None
        elif (player_stats["game_status"] == STATUS_IN_PROGRESS) or (testing == "in_progress"):
            return {**event, "result": str(updated_stat), "in_progress": True}
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

def process_boxscores(game_ids: Set[str], current_date: datetime, testing: str) -> Dict:
    """Process all game boxscores and update betting events."""
    players = {}
    for game_id in game_ids:
        game_data = process_game_data(game_id, current_date)
        if game_data:
            players.update(game_data)

    try:
        response = requests.get(
            f"{os.getenv('BACKEND_URL')}/api/betting-events/active",
            headers=get_headers()
        )
        response.raise_for_status()
        betting_events = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch active betting events: {str(e)}")
        return players


    new_betting_events = []
    for event in betting_events:

        if event["is_complete"] or event["player_name"] not in players:
            continue
        
        stat_type = NFL_STAT_MAP.get(event["stat_type"])
        if not stat_type:
            logger.warning(f"Stat type {event['stat_type']} not found in NFL_STAT_MAP")
            continue

        updated_stat = calculate_stat_value(stat_type, players[event["player_name"]])
        updated_event = update_betting_event(event, players[event["player_name"]], updated_stat, testing)

        if updated_event:
            new_betting_events.append(updated_event)


    if new_betting_events:
        try:
            response = requests.post(
                f"{os.getenv('BACKEND_URL')}/api/betting-events/bulk",
                headers=get_headers(),
                json=new_betting_events
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to bulk update betting events: {str(e)}")

    return players
    