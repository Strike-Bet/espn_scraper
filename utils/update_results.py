import requests 
import os


GO_BACKEND_URL = os.getenv('GO_BACKEND_URL')

TOKEN = os.getenv('TOKEN')

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {TOKEN}'
}



def update_results(game_id, parsed_players):
    for player in parsed_players:
        betting_events = requests.post(url=f"{GO_BACKEND_URL}/betting-events/by-player", headers=headers, json={'player_name': player.get('player_name')})
        
        # Convert betting events response to JSON
        print(f'betting_events_data {betting_events}')
        betting_events_data = betting_events.json()
        
        # Get player statistics from the parsed data
        player_stats = {}
        for stat in player.get("player_statistics", []):
            # Each stat is a list with [stat_key, stat_label, stat_value]
            stat_key = stat[0]
            stat_value = stat[2]
            player_stats[stat_key] = stat_value
        
        # Update each betting event with the corresponding stat
        for betting_event in betting_events_data:
            stat_type = betting_event.get('stat_type')
            
            # Map betting event stat types to player statistics keys
            stat_mapping = {
                'points': 'points',
                'rebounds': 'rebounds',
                'assists': 'assists',
                'steals': 'steals',
                'blocks': 'blocks',
                'three_pointers_made': 'threePointFieldGoalsMade-threePointFieldGoalsAttempted',
                'minutes': 'minutes'
            }
            
            if stat_type in stat_mapping:
                stat_key = stat_mapping[stat_type]
                stat_value = player_stats.get(stat_key)
                
                # For three pointers, we need to extract just the made value
                if stat_type == 'three_pointers_made' and stat_value:
                    stat_value = stat_value.split('-')[0]
                
                # Update the betting event with the actual result
                if stat_value:
                    requests.post(
                        f"{GO_BACKEND_URL}/betting-events/{betting_event.get('event_id')}/complete",
                        json={'actual_result': stat_value}
                    )
    
    return True
