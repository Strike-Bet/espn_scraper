import requests
import json
import os 


TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMmIxYjdmYmQtM2FkZi00MmUxLWFiNjEtM2NhODBmYzA1ZTc5IiwiaXNzIjoic3BvcnRzLXByb3BzLWFwcCIsImV4cCI6MTczNjU4MDMxOH0.ZZvVScsVzfFJwf4J_TLGbvMnIQm-Va3FZ2j4GYt_6eA"

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {TOKEN}'
}


GO_BACKEND_URL = os.getenv('GO_BACKEND_URL')


def close_bet(parsed_players):

    for player in parsed_players:

        player_name = player.get('player_name')

        try:    
            response = requests.post(url=f"{GO_BACKEND_URL}/betting-events/by-player", headers=headers, json={'player_name': player_name})
        except Exception as e:
            print("Error getting betting events")
            continue
    
        if response.status_code == 200:
            betting_events = response.json()
            

            event_ids = betting_events["event_ids"]
            if len(event_ids) == 0:
                continue
            
            print(f"Betting events found for {player.get('player_name')}")
            for event_id in event_ids:
                response = requests.post(f"{GO_BACKEND_URL}/betting-events/{event_id}/complete", headers=headers, json={"result": 25.5})
                if response.status_code == 200:
                    print(f"Bet for {player.get('player_name')} closed successfully")
                else:
                    print(f"Failed to close bet for {player.get('player_name')}: {response.status_code}")
        else:
            print(f"Failed to get betting events for {player.get('player_name')}, response: {response.status_code}")
