import requests
import json
import os
from datetime import datetime, timedelta
from typing import Set, Dict, List
import pytz
BOXSCORE_URL = "https://cdn.espn.com/core/mens-college-basketball/"
print(BOXSCORE_URL)

def extract_players(input_data: Dict) -> List:
    """Extracts the 'players' section from the input JSON."""
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

def extract_game_data(game_id: str) -> Dict:
    """Fetches and extracts game data for a specific game ID."""
    url = f"{BOXSCORE_URL}/boxscore?xhr=1&gameId={game_id}"
    response = requests.get(url)

    # with open(f"boxscore_{game_id}.json", "w") as file:
    #     json.dump(response.json(), file)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data for gameId {game_id}: {response.status_code}")
        
    return response.json()

def extract_game_status(competitions: List, current_date: datetime) -> str:
    pass
