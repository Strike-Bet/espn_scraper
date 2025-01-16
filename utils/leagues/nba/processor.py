from typing import Set, Dict, Optional, Union
from datetime import datetime
from collections import defaultdict
import os
import requests
import logging
from .extractor import extract_game_data, extract_players, parse_players, extract_game_status
from ..common.constants import STATUS_FINAL, STATUS_IN_PROGRESS, STATUS_SCHEDULED
from utils.s3_service import upload_to_s3
from ..common.helpers import parse_shot_stats, get_headers, NBA_STAT_MAP

logger = logging.getLogger(__name__)

def process_player_stats(player_stats: list) -> dict:
    """Process raw player statistics into a formatted dictionary."""
    return {
        'MIN': int(player_stats[0][2]),
        'FG': player_stats[1][2],
        '3PT': player_stats[2][2],
        'FT': player_stats[3][2],
        'OREB': int(player_stats[4][2]),
        'DREB': int(player_stats[5][2]),
        'REB': int(player_stats[6][2]),
        'AST': int(player_stats[7][2]),
        'STL': int(player_stats[8][2]),
        'BLK': int(player_stats[9][2]),
        'TO': int(player_stats[10][2]),
        'PF': int(player_stats[11][2]),
        '+/-': int(player_stats[12][2]),
        'PTS': int(player_stats[13][2]),
    }

def process_game_data(game_id: str, current_date: datetime) -> Optional[Dict]:
    """Process individual game data and return player statistics."""
    try:
        data = extract_game_data(game_id)
        events = data.get("gamepackageJSON", {}).get("seasonseries", [{}])[0].get("events", [])
        game_status = extract_game_status(events, current_date)

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

def update_betting_event(event: Dict, player_stats: Dict, updated_stat: float) -> Optional[Dict]:
    """Update or complete a betting event based on game status."""
    try:
        if player_stats["game_status"] == STATUS_FINAL and event["in_progress"]:
            response = requests.post(
                f"{os.getenv('BACKEND_URL')}/api/betting-events/{event['event_id']}/complete",
                headers=get_headers(),
                json={"result": updated_stat}
            )
            response.raise_for_status()
            return None
        elif player_stats["game_status"] == STATUS_IN_PROGRESS:
            return {**event, "result": updated_stat, "in_progress": True}
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

def process_boxscores(game_ids: Set[str], current_date: datetime) -> Dict:
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

        stat_type = NBA_STAT_MAP.get(event["stat_type"])
        if not stat_type:
            logger.warning(f"Stat type {event['stat_type']} not found in NBA_STAT_MAP")
            continue

        updated_stat = calculate_stat_value(stat_type, players[event["player_name"]])
        updated_event = update_betting_event(event, players[event["player_name"]], updated_stat)
        
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

