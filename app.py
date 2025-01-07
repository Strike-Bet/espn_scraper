from flask import Flask
from flask_cors import CORS
from utils import scrape_games
from utils import fetch_and_process_boxscores
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route("/espn-scraper", methods=['GET'])
def extract_boxscore_espn():
    try:
        game_ids = scrape_games()
        fetch_and_process_boxscores(game_ids=game_ids)
        return {"message": "Boxscores extracted and processed successfully!"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    app.run(port=5000, debug=True)
