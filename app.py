from flask import Flask
from flask_cors import CORS
from utils.leagues.nba import scraper as nba_scraper
from utils.leagues.nfl import scraper as nfl_scraper
from utils.leagues.nba import processor as nba_processor
from utils.leagues.nfl import processor as nfl_processor
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

@app.route("/espn-scraper-nfl", methods=['GET'])
def extract_boxscore_espn_nfl():
    try:
        current_date = datetime(2025, 1, 25)
        game_ids = nfl_scraper.scrape_games(current_date)
        nfl_processor.process_boxscores(game_ids, current_date, testing_mode = False,testing="")
        return {"message": "NFL boxscores processed successfully!"}
    except Exception as e:
        return {"error": str(e)}

@app.route("/espn-scraper-nba", methods=['GET'])
def extract_boxscore_espn_nba():
    try:
        current_date = datetime.now() - timedelta(days=1)
        game_ids = nba_scraper.scrape_games(current_date)
        nba_processor.process_boxscores(game_ids, current_date, testing_mode = False, testing="")
        return {"message": "NBA boxscores processed successfully!"}
    except Exception as e:
        return {"error": str(e)}

@app.route("/test-processors", methods=['GET'])
def test_processors():
    try:
        from utils.leagues.testing.test_processor import run_test
        try: 
            run_test()
        except Exception as e:
            return {"error": str(e)}
        
        return {"message": "Test processing completed successfully!"}
    except Exception as e:
        return {"error": str(e)}

@app.route('/health', methods=['GET'])
def health_check():
    current_time = datetime.utcnow().isoformat() + 'Z'  # Get current UTC time in ISO format
    return {
        "message": "Endpoint hit",
        "timestamp": current_time
    }, 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8000)
