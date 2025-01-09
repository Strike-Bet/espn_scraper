from flask import Flask
from flask_cors import CORS
from utils import scrape_games
from utils import fetch_and_process_boxscores
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route("/espn-scraper", methods=['GET'])
def extract_boxscore_espn():
    try:
        # initial parameters
        current_date = datetime.now()
        
        game_ids = scrape_games(current_date)
        fetch_and_process_boxscores(game_ids=game_ids, current_date=current_date, testing=False)
        return {"message": "Boxscores extracted and processed successfully!"}
    except Exception as e:
        return {"error": str(e)}
    

@app.route("/espn-scraper-testing", methods=['GET'])
def extract_boxscore_espn_testing():
    try:
        # initial parameters
        current_date = datetime.now() - timedelta(days=1)

        game_ids = scrape_games(current_date)
        fetch_and_process_boxscores(game_ids=game_ids, current_date=current_date, testing=True)
        return {"message": "Boxscores extracted and processed successfully!"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    app.run(port=5000, debug=True)
