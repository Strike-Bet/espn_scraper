from datetime import datetime, timedelta
from ..nba.processor import process_boxscores as nba_process
from ..nfl.processor import process_boxscores as nfl_process
from ..nba.scraper import scrape_games as nba_scrape
from ..nfl.scraper import scrape_games as nfl_scrape
import requests
import os
headers = { 
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('TOKEN')}"
}

def run_test():
    """Run test processing for both NBA and NFL games from yesterday."""
    current_date = datetime(2025, 1, 1)
#     {
#     "player_id": "12345",
#     "player_name": "LeBron James",
#     "stat_type": "points",
#     "league": 68,
#     "premium": 8.5,
#     "result": "",
#     "is_closed": false,
#     "event_date": "2024-01-15T00:00:00Z",
#     "start_time": "2024-01-15T00:30:00Z",
#     "end_time": "2024-01-15T03:00:00Z",
#     "in_progress": false,
#     "is_complete": false,
#     "metadata": {
#         "projected_assists": 9,
#         "team": "Lakers",
#         "opponent": "Clippers",
#         "home_game": true,
#         "season_average": 8.2
#     }
# }
    sample_betting_events_nba = [

        {
            "player_id": "2322",
            "player_name": "Kyrie Irving",
            "stat_type": "Points",
            "league": 7,
            "event_date": "2025-01-01T00:00:00Z",
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-01T03:00:00Z",
            "is_closed": False,
            "in_progress": False,
            "is_complete": False,
            "metadata": {
                "team": "DAL",
                "opponent": "HOU",
                "game_id": "401705026"
            }
        },
        {
            "player_id": "2322",
            "player_name": "Kyrie Irving",
            "stat_type": "Assists",
            "league": 7,
            "event_date": "2025-01-01T00:00:00Z",
            "start_time": "2025-01-01T00:00:00Z",
            "end_time": "2025-01-01T03:00:00Z",
            "is_closed": False,
            "in_progress": False,
            "is_complete": False,
            "metadata": {
                "team": "DAL",
                "opponent": "HOU",
                "game_id": "401705026"
            }
        }
    ]
    
    response = requests.post(f"{os.getenv('GO_BACKEND_URL')}/betting-events/bulk", headers=headers, json=sample_betting_events_nba)
    print(response.text)

    if response.status_code != 201:  
        print(f"Failed to create betting events: {response.status_code} {response.text}")
        return
    
    print("NBA betting events created successfully")

    
    # Test NBA Processing
   
    print("Testing NBA Processing...")
    nba_game_ids = nba_scrape(current_date)
    if nba_game_ids:
        nba_process(nba_game_ids, current_date, testing=True)
    else:
        print("No NBA games found for testing")

    
    # Test NFL Processing
    current_date = datetime(2025, 1, 4)

    sample_betting_events_nfl = [
            {
                "player_id": "2322",
                "player_name": "Lamar Jackson",
                "stat_type": "Pass Yards",
                "league": 9,
                "event_date": "2025-01-04T00:00:00Z",
                "start_time": "2025-01-04T00:00:00Z",
                "end_time": "2025-01-04T03:00:00Z",
                "is_closed": False,
                "in_progress": False,
                "is_complete": False,
                "metadata": {
                    "team": "BAL",
                    "opponent": "CIN",
                    "game_id": "401705026"
                }, 
                "created_at": "2025-01-04T00:00:00Z",
                "updated_at": "2025-01-04T00:00:00Z"
            }, 
            {
                "player_id": "2322",
                "player_name": "Lamar Jackson",
                "stat_type": "Rush Yards",
                "league": 9,
                "event_date": "2025-01-04T00:00:00Z",
                "start_time": "2025-01-04T00:00:00Z",
                "end_time": "2025-01-04T03:00:00Z",
                "is_closed": False,
                "in_progress": False,
                "is_complete": False,
                "metadata": {
                    "team": "BAL",
                    "opponent": "CIN",
                    "game_id": "401705026"
                }, 
            }
    ]

    response = requests.post(f"{os.getenv('GO_BACKEND_URL')}/betting-events/bulk", headers=headers, json=sample_betting_events_nfl)

    if response.status_code != 201:  
        print(f"Failed to create betting events: {response.status_code} {response.text}")
        return
    
    print("NFL betting events created successfully")

    print("\nTesting NFL Processing...")
    nfl_game_ids = nfl_scrape(current_date)
 
    if nfl_game_ids:
        nfl_process(nfl_game_ids, current_date, testing=True)
    else:
        print("No NFL games found for testing")

if __name__ == "__main__":
    run_test() 