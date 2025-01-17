from typing import Set, Dict
from datetime import datetime
from .extractor import extract_game_data, extract_players, parse_players, extract_game_status
from ..common.constants import STATUS_FINAL, STATUS_IN_PROGRESS, STATUS_SCHEDULED
from utils.s3_service import upload_to_s3
from utils.leagues.nba.update_results import update_results
from collections import defaultdict
import requests
import os
import json

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.getenv("TOKEN")}'
}

def process_boxscores(game_ids: Set[str], current_date: datetime, testing: bool = False) -> Dict:
    players = defaultdict(dict)
    for game_id in game_ids:
        print("Processing game: ", game_id)
        data = extract_game_data(game_id)
        events = data.get("gamepackageJSON", {}).get("seasonseries", [{}])[0].get("events", [])
        status = None
        for event in events:
            status = extract_game_status(event, current_date)
            if status:
                print(status)
                break

        players_data = extract_players(data)
        parsed_players = parse_players(players_data)
       
        # get dict of player name and player stats
        for player in parsed_players:
            player_name = player["player_name"]
            player_stats = player["player_statistics"]
             # update player stats if they played
            if player_stats:
                fg_made, fg_attempted = map(int, player_stats[1][2].split('-'))  # Split FG into made and attempted
                _3pt_made, _3pt_attempted = map(int, player_stats[2][2].split('-'))
                ft_made, ft_attempted = map(int, player_stats[3][2].split('-'))
                stats_dict = {
                    'Minutes': int(player_stats[0][2]),  # minutes
                    'FG Made': fg_made,
                    'FG Attempted': fg_attempted,
                    '3-PT Made': _3pt_made,
                    '3-PT Attempted': _3pt_attempted,
                    'Free Throws Made': ft_made,
                    'Free Throws Attempted': ft_attempted,
                    'Rebounds': int(player_stats[6][2]),  # rebounds
                    'Assists': int(player_stats[7][2]),  # assists
                    'Steals': int(player_stats[8][2]),  # steals
                    'Blocked Shots': int(player_stats[9][2]),  # blocks
                    'Turnovers': int(player_stats[10][2]),  # turnovers
                    'PF': int(player_stats[11][2]),  # fouls
                    '+/-': int(player_stats[12][2]),  # plusMinus
                    'Points': int(player_stats[13][2]),   # points
                    'Status': status
                }

                players[player_name] = stats_dict 
    

    # get all active betting events
    response = requests.get(f"{os.getenv('GO_BACKEND_URL')}/api/betting-events/active", headers=headers)
    active_events = response.json()
    
    # for each active event, if the player name matches, update the player stats
    new_betting_events = []
    for event in active_events:
            if event['player_name'] in players:
                # update the event with the player stats
                stat_type = event['stat_type']
                if stat_type in players[event['player_name']]:
                    event['result'] = players[event['player_name']][stat_type]

                # update the event with the game status
                if players[event['player_name']]['Status'] == STATUS_FINAL and not event['is_complete']:
                    # handle closing event
                    print("Closing event with player: ", event['player_name'])
                else:
                    # handle in progress event
                    # new event with these fields player_id,player_name,stat_type,league,premium,result,is_closed,event_date,start_time,end_time,in_progress,is_complete,metadata.additional_info
                    print("In progress event with player: ", event['player_name'])
                    new_event = {
                        'player_id': event['player_id'],
                        'player_name': event['player_name'],
                        'stat_type': event['stat_type'],
                        'league': event['league'],
                        'premium': event['premium'],
                        'result': str(event['result']),
                        'is_closed': event['is_closed'],
                        'event_date': event['event_date'],
                        'start_time': event['start_time'],
                        'end_time': event['end_time'],
                        'in_progress': event['in_progress'],
                        'is_complete': event['is_complete'],
                        'metadata': event['metadata'],
                    }
                    new_betting_events.append(new_event)
    # bulk insert the new betting events into the database
    response = requests.post(f"{os.getenv('GO_BACKEND_URL')}/api/betting-events/bulk", headers=headers, json=new_betting_events)
    print(response.status_code)
    return players

# def process_boxscores(game_ids: Set[str], current_date: datetime, testing: bool = False) -> Dict:
#     """Process NBA boxscores for given game IDs."""
#     all_data = {}
#     game_statuses = {}

#     for game_id in game_ids:
#         try:
#             # Skip if game is already final
#             if game_statuses.get(game_id) == STATUS_FINAL and not testing:
#                 print(f"Game {game_id} is final")
#                 continue

#             # Fetch and process game data
#             data = extract_game_data(game_id)
            
#             # Upload raw boxscore to S3 if not testing
#             if not testing:
#                 upload_to_s3(data, f"NBA/NBA_BOXSCORES/boxscore_{game_id}.json")

#             # Process game events and status
#             events = data.get("gamepackageJSON", {}).get("seasonseries", [{}])[0].get("events", [])
            
#             # Override status for testing
#             if testing:
#                 for event in events:
#                     event["statusType"] = {"name": STATUS_IN_PROGRESS}
#                     print(f"Testing mode: Setting game {game_id} status to {STATUS_IN_PROGRESS}")

#             # Update game status
#             for event in events:
#                 status = extract_game_status(event, current_date)
#                 game_statuses[game_id] = status if not testing else STATUS_IN_PROGRESS

#             # Process player data
#             players_data = extract_players(data)
#             if len(players_data) != 2:
#                 if game_statuses.get(game_id) == STATUS_SCHEDULED:
#                     print(f"Game {game_id} has not started yet")
#                 else:
#                     print(f"Error: Player data not found for game {game_id}")
#                 continue

#             # Upload and process player data
#             if not testing:
#                 upload_to_s3(players_data, f"NBA/PLAYERDATA/players_{game_id}.json")
#             parsed_players = parse_players(players_data)
#             all_data[game_id] = parsed_players

#             # Handle betting updates based on game status
#             status = game_statuses.get(game_id)
#             if status == STATUS_FINAL and not testing:
#                 update_results(parsed_players, closed=True)
#             elif status == STATUS_IN_PROGRESS or testing:
#                 update_results(parsed_players, closed=False)

#         except Exception as e:
#             print(f"Error processing game {game_id}: {e}")
#             continue

#     return all_data
