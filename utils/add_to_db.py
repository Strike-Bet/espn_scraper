import os
import json
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection details
DB_HOST = os.getenv("POSTGRES_HOST")
DB_PORT = os.getenv("POSTGRES_PORT")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")

# Connect to the PostgreSQL database
conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    dbname=DB_NAME
)

cursor = conn.cursor()

def insert_boxscore_data(file_path):
    """
    Inserts data from the final JSON file into the PostgreSQL database.
    """
    with open(file_path, "r") as f:
        data = json.load(f)

    for game_id, players in data.items():
        for player in players:
            team = player["team"]
            opposing_team = player["opposing_team"]
            player_name = player["player_name"]
            starter = player["player_metadata"].get("starter")
            did_not_play = player["player_metadata"].get("didNotPlay")
            ejected = player["player_metadata"].get("ejected")
            active = player["player_metadata"].get("active")
            reason = player["player_metadata"].get("reason")
            jersey = player["player_metadata"].get("jersey")
            
            stat_full_name = [stat[0] for stat in player["player_statistics"]]
            stat_abbreviation = [stat[1] for stat in player["player_statistics"]]
            stat_value = [stat[2] for stat in player["player_statistics"]]

            # Insert the data into the database
            cursor.execute(
                """
                INSERT INTO boxscore_data (
                    game_id, team, opposing_team, player_name, starter, did_not_play, ejected,
                    active, reason, jersey, stat_full_name, stat_abbreviation, stat_value
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    game_id, team, opposing_team, player_name, starter, did_not_play, ejected,
                    active, reason, jersey, stat_full_name, stat_abbreviation, stat_value
                )
            )
    conn.commit()

if __name__ == "__main__":
    # Path to the final JSON file
    final_json_file = "boxscores_final.json"

    insert_boxscore_data(final_json_file)
    print("Data inserted successfully.")

    # Close the database connection
    cursor.close()
    conn.close()