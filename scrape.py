import requests
import datetime
import json

# Get the current date in the required format: YYYYMMDD
current_date = datetime.datetime.now().strftime("%Y%m%d")

# URL with the current date
url = f"https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?region=us&lang=en&contentorigin=espn&calendartype=offdays&includeModules=videos&dates={current_date}&tz=America%2FNew_York"

# Make a GET request to fetch the JSON data
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON data
    data = response.json()
    
    # Save the JSON data to a file
    with open("all_current_games.json", "w") as json_file:
        json.dump(data, json_file, indent=4)
    
    print(f"JSON data for date {current_date} has been saved to 'all_current_games.json'.")
else:
    print(f"Failed to fetch data. HTTP Status Code: {response.status_code}")

# Extract "id" values from "competitions"
game_ids = set()
try:
    with open("all_current_games.json", "r") as json_file:
        data = json.load(json_file)
        
        # Navigate through the JSON structure
        events = data.get("events", [])
        for event in events:
            competitions = event.get("competitions", [])
            for competition in competitions:
                competition_id = competition.get("id")
                if competition_id:
                    game_ids.add(competition_id)
        
        print(f"Extracted unique game IDs from 'competitions': {game_ids}")
except Exception as e:
    print(f"An error occurred while processing the file: {e}")

# Save the game IDs to a file
if game_ids:
    with open("game_ids.txt", "w") as game_ids_file:
        for game_id in game_ids:
            game_ids_file.write(game_id + "\n")
    print("All extracted game IDs have been saved to 'game_ids.txt'.")
else:
    print("No game IDs were found.")