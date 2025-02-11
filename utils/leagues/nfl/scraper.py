from ..common.constants import LEAGUE_ENDPOINTS
from ..common.helpers import find_next_game_date
import requests
import json
from datetime import datetime

def scrape_games(current_date: datetime) -> set:
    """Scrape NFL games starting from current_date."""

    current_date = datetime(2025, 2, 9)
    game_ids = set()
    
    for check_date in find_next_game_date(current_date):
        url = f"{LEAGUE_ENDPOINTS['nfl']}?dates={check_date.strftime('%Y%m%d')}"
        print(url)
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])
            
            if len(events) > 0:
                for event in events:
                    for competition in event.get("competitions", []):
                        if game_id := competition.get("id"):
                            game_ids.add(game_id)
                break  # Found games, stop searching
            else:
                print(f"No NFL games on {check_date.strftime('%Y%m%d')}")

    game_ids = sorted(list(game_ids))
    return game_ids