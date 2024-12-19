from flask import Flask, jsonify, request
from flask_cors import CORS

from utils import scrape_current_nba_player_stats

app = Flask(__name__)

# Enable CORS for the entire app
CORS(app)

# Define a basic route
@app.route('/getCurNbaPlayerStats', methods=['GET'])
def getCurNBAPlayerStats():
    try: 
        # run scraper on today's date and return json of player data
        player_data = scrape_current_nba_player_stats()

        return jsonify(player_data)
     
        # get cur bet players in the supabase

        # update the bet players in supabase (take in list of bet players, and scrape output)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    # Run the app on port 5000
    app.run(port=5000, debug=True)