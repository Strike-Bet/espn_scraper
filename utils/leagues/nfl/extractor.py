import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from ..common.constants import STATUS_FINAL, STATUS_IN_PROGRESS, STATUS_SCHEDULED

NFL_BOXSCORE_URL = f"https://cdn.espn.com/core/nfl/boxscore?xhr=1"

def extract_players(input_data: Dict) -> List:
    """Extracts the 'players' section from the input JSON."""
    return input_data.get("gamepackageJSON", {}).get("boxscore", {}).get("players", [])

def parse_players(players_data):
    """
    Processes the NFL players data and returns a list of player dictionaries.
    Each team's data contains statistics grouped by category (passing, rushing, receiving, etc.)
    """
    all_players = []

    for team_data in players_data:
        team_abbrev = team_data["team"]["abbreviation"]
        # Get the other team's abbreviation from the next/previous team data
        opp_abbrev = players_data[1 - players_data.index(team_data)]["team"]["abbreviation"]
        
        # Process each statistic category (passing, rushing, receiving)
        for stat_category in team_data.get("statistics", []):

            category_name = stat_category.get("name", "")
            stat_keys = stat_category.get("keys", [])
            
            # Process each athlete in this category
            for athlete in stat_category.get("athletes", []):
                player_name = athlete["athlete"]["displayName"]
                jersey = athlete["athlete"].get("jersey", "")
                
                # Convert stats array to our standard format
                player_stats_list = []
                athlete_stats = athlete.get("stats", [])

                if "adjQBR" in stat_keys and len(athlete_stats) < len(stat_keys):
                    athlete_stats.append(athlete_stats[-1])
                
                if athlete_stats and len(athlete_stats) == len(stat_keys):
                    for key, stat_value in zip(stat_keys, athlete_stats):
                        if player_name == "Patrick Mahomes":
                            print(key, stat_value)
                        player_stats_list.append([key, key, stat_value])
                else: 
                    print(player_name, stat_keys, athlete_stats)
            
                
                player_dict = {
                    "team": team_abbrev,
                    "opposing_team": opp_abbrev,
                    "player_name": player_name,
                    "player_metadata": {
                        "starter": False,  # NFL data doesn't provide this
                        "didNotPlay": False,
                        "ejected": False,
                        "active": True,
                        "reason": "",
                        "jersey": jersey,
                        "category": category_name  # Add category for NFL-specific processing
                    },
                    "player_statistics": player_stats_list
                }
                # Check if player already exists (might have stats in multiple categories)
                existing_player = next(
                    (p for p in all_players if p["player_name"] == player_name), 
                    None
                )
                
                if existing_player:
                    # Append new statistics to existing player
                    existing_player["player_statistics"].extend(player_stats_list)
                else:
                    # Add new player
                    all_players.append(player_dict)
    
    return all_players

def extract_game_data(game_id: str) -> Dict:
    """Fetches and extracts game data for a specific game ID."""
    url = f"{NFL_BOXSCORE_URL}&gameId={game_id}"
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data for gameId {game_id}: {response.status_code}")
        
    return response.json()

def extract_game_status(event: Dict, current_date: datetime) -> str:
    """Extract game status from event data."""
    event_date = event.get("date", "")
    try:
        # NFL uses a shorter date format
        event_datetime = datetime.strptime(event_date, "%Y-%m-%dT%H:%MZ")
    except ValueError:
        # Fallback to full format if needed
        try:
            event_datetime = datetime.strptime(event_date, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            print(f"Could not parse date: {event_date}")
            return STATUS_SCHEDULED

    
    if current_date.date() <= event_datetime.date() <= (current_date + timedelta(days=1)).date():
         return event.get("status", {}).get("type", {}).get("name", "")
    
    return STATUS_SCHEDULED
