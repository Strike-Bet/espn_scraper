import requests 
import os


GO_BACKEND_URL = os.getenv('GO_BACKEND_URL')




headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {os.getenv("TOKEN")}'
}



def update_results(parsed_players, closed):

    STAT_MAP = {
        "Minutes": "minutes",
        "FG Attempted": "fieldGoalsMade-fieldGoalsAttempted",
        "3-PT Made": "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
        "3-PT Attempted": "threePointFieldGoalsMade-threePointFieldGoalsAttempted",
        "FT Attempted": "freeThrowsMade-freeThrowsAttempted",
        "Free Throws Made": "freeThrowsMade-freeThrowsAttempted",
        "Offensive Rebounds": "offensiveRebounds",
        "Defensive Rebounds": "defensiveRebounds",
        "Rebounds": "rebounds",
        "Assists": "assists",
        "Steals": "steals",
        "Blocks": "blocks",
        "Turnovers": "turnovers",
        "Fouls": "fouls",
        "+/-": "plusMinus",
        "Points": "points",
        "Pts": "points", 
        "Rebs": "rebounds",
        "Asts": "assists",
        "Stls": "steals",
        "Blks": "blocks",
        "TOs": "turnovers",
        "Fls": "fouls",
        "+/-": "plusMinus",
    }

    
    for player in parsed_players:
        print(f"Processing player: {player.get('player_name')}")
        player_name = player.get('player_name')

        try:    
            response = requests.post(url=f"{GO_BACKEND_URL}/api/betting-events/by-player", headers=headers, json={'player_name': player_name})
        except Exception as e:
            print("Error getting betting events")
            continue
    
        if response.status_code == 200:
            
            event_ids = response.json()["event_ids"]
            
            if len(event_ids) == 0:
                continue
            

            for event_id in event_ids:
                response = requests.get(f"{GO_BACKEND_URL}/api/betting-events/{event_id}", headers=headers)
                
                # gets the stat type of the betting line e.g. "Points+Rebounds"
                desired_stat_type = response.json()["stat_type"]

                # splits the stat types up in case of multiple stats 
                stat_list = desired_stat_type.split("+")

                #end result of a potential combination of stats 
                result = 0 
                for stat_type in stat_list: 
                    print(f"Processing stat: {stat_type}")
                    
                    # Skip if stat type is Dunks since it's not in player_statistics
                    if stat_type == "Dunks":
                        print(f"Skipping unsupported stat type: {stat_type}")
                        continue
                        
                    stat = STAT_MAP.get(stat_type)
                    if not stat:
                        print(f"Unknown stat type: {stat_type}")
                        continue

                    #finds the stat in the player's boxscore 
                    for statistic in player.get("player_statistics"): 
                        if statistic[0] == stat: 
                            try:
                                # Handle cases where the stat might be in format "4-9" (like FG attempts)
                                if '-' in str(statistic[2]):
                                    made, attempted = statistic[2].split('-')
                                    # If we want attempts, use the second number
                                    if stat_type.endswith('Attempted'):
                                        result += float(attempted)
                                    # If we want made shots, use the first number
                                    elif stat_type.endswith('Made'):
                                        result += float(made)
                                    else:
                                        result += float(made)  # Default to made shots
                                else:
                                    result += float(statistic[2])
                            except (ValueError, TypeError) as e:
                                print(f"Error processing stat {stat}: {e}")
                                continue

                # updates the betting line with the result 
                if closed: 
                    response = requests.post(f"{GO_BACKEND_URL}/api/betting-events/{event_id}/complete", headers=headers, json={"result": str(result)})
                    if response.status_code == 200:
                        print(f"Betting line {event_id} closed successfully")
                    else:
                        print(f"Failed to close betting line {event_id}: {response.status_code}")

                else: 
                    response = requests.put(f"{GO_BACKEND_URL}/api/betting-events/{event_id}", headers=headers, json={"result": str(result)})

                    if response.status_code == 200:
                        print(f"Betting line {event_id} updated successfully")
                    else:
                        print(f"Failed to update betting line {event_id}: {response.status_code}")

    return 