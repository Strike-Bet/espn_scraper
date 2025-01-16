from datetime import datetime, timedelta
from ..nba.processor import process_boxscores as nba_process
from ..nfl.processor import process_boxscores as nfl_process
from ..nba.scraper import scrape_games as nba_scrape
from ..nfl.scraper import scrape_games as nfl_scrape
import requests
import os
from ..common.helpers import get_headers
import logging

logger = logging.getLogger(__name__)

def test_nba_processing():
    """Test NBA betting event creation and processing"""
    print("\n=== Starting NBA Processing Test ===")
    current_date = datetime(2025, 1, 1)
    
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
    
    print("Creating NBA betting events...")
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/api/betting-events/bulk", 
        headers=get_headers(), 
        json=sample_betting_events_nba
    )
    assert response.status_code == 201, f"Failed to create NBA betting events: {response.status_code} {response.text}"
    
    created_events = response.json()
    print(f"Successfully created {len(created_events)} NBA betting events")
    assert len(created_events) == 2, "Expected 2 NBA betting events to be created"
    
    print("Scraping NBA games...")
    nba_game_ids = nba_scrape(current_date)
    assert nba_game_ids == ['401705021', '401705022', '401705023', '401705024', '401705025', '401705026', '401705027', '401705028'], "NBA game ids should match"
    print(f"Found {len(nba_game_ids)} NBA games")
    
    print("Processing NBA games (in_progress)...")
    nba_process(nba_game_ids, current_date, testing="in_progress")
    
    print("Verifying NBA event updates (in_progress)...")
    for event in created_events:
        response = requests.get(
            f"{os.getenv('BACKEND_URL')}/api/betting-events/{event['event_id']}", 
            headers=get_headers()
        )
        assert response.status_code == 200, f"Failed to fetch NBA event {event['event_id']}"
        updated_event = response.json()
        assert updated_event["in_progress"] == True, "Event should be in progress"
        assert updated_event["is_closed"] == False, "Event should be open"
        assert float(updated_event["result"]) > 0, "Event result should be greater than 0"
        print(f"NBA event {event['event_id']} verified - Result: {updated_event.get('result')}")

    print("\nProcessing NBA games (complete)...")
    nba_process(nba_game_ids, current_date, testing="complete")

    print("Verifying NBA event updates (complete)...")
    for event in created_events:
        response = requests.get(
            f"{os.getenv('BACKEND_URL')}/api/betting-events/{event['event_id']}", 
            headers=get_headers()
        )
        assert response.status_code == 200, f"Failed to fetch NBA event {event['event_id']}"
        updated_event = response.json()
        assert updated_event["is_complete"] == True, "Event should be complete"
        print(f"NBA event {event['event_id']} completed successfully")
    
    print("=== NBA Processing Test Completed Successfully ===\n")

def test_nfl_processing():
    """Test NFL betting event creation and processing"""
    print("\n=== Starting NFL Processing Test ===")
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
            }
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
            }
        }
    ]
    
    print("Creating NFL betting events...")
    response = requests.post(
        f"{os.getenv('BACKEND_URL')}/api/betting-events/bulk", 
        headers=get_headers(), 
        json=sample_betting_events_nfl
    )
    assert response.status_code == 201, f"Failed to create NFL betting events: {response.status_code} {response.text}"
    
    created_events = response.json()
    print(f"Successfully created {len(created_events)} NFL betting events")
    assert len(created_events) == 2, "Expected 2 NFL betting events to be created"
    
    print("Scraping NFL games...")
    nfl_game_ids = nfl_scrape(current_date)
    assert nfl_game_ids == ["401671834", "401671836"], "NFL game ids should match"
    print(f"Found {len(nfl_game_ids)} NFL games")
    
    print("Processing NFL games (in_progress)...")
    nfl_process(nfl_game_ids, current_date, testing="in_progress")
    
    print("Verifying NFL event updates (in_progress)...")
    for event in created_events:
        response = requests.get(
            f"{os.getenv('BACKEND_URL')}/api/betting-events/{event['event_id']}", 
            headers=get_headers()
        )
        assert response.status_code == 200, f"Failed to fetch NFL event {event['event_id']}"
        updated_event = response.json()
        assert updated_event["in_progress"] == True, "Event should be in progress"
        assert updated_event["is_closed"] == False, "Event should be open"

        assert float(updated_event["result"]) > 0, "Event result should be greater than 0"
        print(f"NFL event {event['event_id']} verified - Result: {updated_event.get('result')}")

    print("\nProcessing NFL games (complete)...")
    nfl_process(nfl_game_ids, current_date, testing="complete")

    
    print("Verifying NFL event updates (complete)...", created_events)
    for event in created_events:
        response = requests.get(
            f"{os.getenv('BACKEND_URL')}/api/betting-events/{event['event_id']}", 
            headers=get_headers()
        )
        assert response.status_code == 200, f"Failed to fetch NFL event {event['event_id']}"
        updated_event = response.json()
        assert updated_event["is_complete"] == True, "Event should be complete"
        print(f"NFL event {event['event_id']} completed successfully")
    
    print("=== NFL Processing Test Completed Successfully ===\n")

def run_test():
    """Run all processor tests"""
    try:
        print("\n=== Starting Processor Tests ===")
        test_nba_processing()
        test_nfl_processing()
        print("=== All Tests Completed Successfully ===\n")
        return {"message": "All tests completed successfully"}
    except AssertionError as e:
        logger.error(f"Test failed: {str(e)}")
        print(f"\n!!! Test Failed: {str(e)} !!!\n")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error during testing: {str(e)}")
        print(f"\n!!! Unexpected Error: {str(e)} !!!\n")
        return {"error": str(e)}

if __name__ == "__main__":
    run_test() 