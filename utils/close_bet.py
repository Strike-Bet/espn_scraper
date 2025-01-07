import requests
import json
import os 

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.getenv("TOKEN")}'
}


GO_BACKEND_URL = os.getenv('GO_BACKEND_URL')


def close_bet(parsed_players):
    for player in parsed_players:
        betting_events = requests.post(url=f"{GO_BACKEND_URL}/betting-events/{player.get('player_name')}", headers=headers, json={'player_name': player.get('player_name')})
        print(f'betting_events: {betting_events}')
       
        if betting_events:
            for betting_event in betting_events:
                response = requests.post(f"{GO_BACKEND_URL}/betting-events/{betting_event.get('id')}/complete")
                if response.status_code == 200:
                    print(f"Bet for {player.get('player_name')} closed successfully")
                else:
                    print(f"Failed to close bet for {player.get('player_name')}: {response.status_code}")
        else:
            print(f"Failed to get betting event id for {player.get('player_name')}")

    return True

