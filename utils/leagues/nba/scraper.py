from ..common.constants import LEAGUE_ENDPOINTS
from ..common.helpers import format_date
import requests
import json
from datetime import datetime
import pytz
def scrape_games(current_date: datetime) -> set:
    """Scrape NBA games for the given date."""

    pst_date = current_date.astimezone(pytz.timezone('US/Pacific'))
    formatted_date = format_date(pst_date)
    url = f"{LEAGUE_ENDPOINTS['nba']}?dates={formatted_date}"
    
    response = requests.get(url)
    game_ids = set()

    if response.status_code == 200:
        data = response.json()
        
        events = data.get("events", [])
        for event in events:
            for competition in event.get("competitions", []):
                if game_id := competition.get("id"):
                    game_ids.add(game_id)
                    
    game_ids = sorted(list(game_ids))
    return game_ids
