from flask import Flask, jsonify
from flask_cors import CORS
from utils.leagues.nba import scraper as nba_scraper
from utils.leagues.nfl import scraper as nfl_scraper
from utils.leagues.nba import processor as nba_processor
from utils.leagues.nfl import processor as nfl_processor
from utils.leagues.cbb import scraper as cbb_scraper
from utils.leagues.cbb import processor as cbb_processor
from datetime import datetime
from dotenv import load_dotenv
import pytz
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('espn_scraper')

load_dotenv()
app = Flask(__name__)
CORS(app)

def scrape_all_games():
    """Function to scrape both NBA, NFL, and CBB games"""
    job_start_time = datetime.now(pytz.timezone('US/Pacific'))
    logger.info(f"Starting scraper job at {job_start_time}")
    
    try:
        current_date = datetime.now()
        results = {
            'nba': {'status': 'pending'},
            'nfl': {'status': 'pending'}, 
            'cbb': {'status': 'pending'}
        }

        # Process NBA games
        try:
            logger.info("Starting NBA games scraping...")
            nba_game_ids = nba_scraper.scrape_games(current_date)
            logger.info(f"Found {len(nba_game_ids)} NBA games: {nba_game_ids}")
            
            logger.info("Processing NBA boxscores...")
            completed = nba_processor.process_boxscores(nba_game_ids, current_date, testing_mode=False, testing="")
            if completed:
                results['nba'] = {
                    'status': 'success',
                    'game_count': len(nba_game_ids),
                    'game_ids': nba_game_ids
                }
            else:
                logger.info("NBA processing failed")
                results['nba'] = {
                    'status': 'error',
                    'error': 'NBA processing failed'
                }
        except Exception as e:
            logger.error(f"Error processing NBA games: {str(e)}", exc_info=True)
            results['nba'] = {
                'status': 'error',
                'error': str(e)
            }

        # Process NFL games
        try:
            logger.info("Starting NFL games scraping...")
            nfl_game_ids = nfl_scraper.scrape_games(current_date)
            logger.info(f"Found {len(nfl_game_ids)} NFL games: {nfl_game_ids}")
            
            logger.info("Processing NFL boxscores...")
            nfl_processor.process_boxscores(nfl_game_ids, current_date, testing_mode=False, testing="")
            results['nfl'] = {
                'status': 'success',
                'game_count': len(nfl_game_ids),
                'game_ids': nfl_game_ids
            }
            logger.info("NFL processing completed successfully")
        except Exception as e:
            logger.error(f"Error processing NFL games: {str(e)}", exc_info=True)
            results['nfl'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Process CBB games
        try:
            logger.info("Starting CBB games scraping...")
            cbb_game_ids = cbb_scraper.scrape_games(current_date)
            logger.info(f"Found {len(cbb_game_ids)} CBB games: {cbb_game_ids}")
            completed = cbb_processor.process_boxscores(cbb_game_ids, current_date, testing_mode=False, testing="")
            if completed:
                results['cbb'] = {
                    'status': 'success',
                    'game_count': len(cbb_game_ids),
                    'game_ids': cbb_game_ids
                }
        except Exception as e:
            logger.error(f"Error processing CBB games: {str(e)}", exc_info=True)
            results['cbb'] = {
                'status': 'error',
                'error': str(e)
            }

        job_end_time = datetime.now(pytz.timezone('US/Pacific'))
        duration = (job_end_time - job_start_time).total_seconds()
        logger.info(f"Scraper job completed in {duration:.2f} seconds")
        logger.info(f"Final results: {results}")
        return results
    except Exception as e:
        logger.error(f"Fatal error in scraper job: {str(e)}", exc_info=True)
        return {'error': str(e)}


def scrape_cbb_games():
    job_start_time = datetime.now(pytz.timezone('US/Pacific'))
    logger.info(f"Starting scraper job at {job_start_time}")
    
    try:
        current_date = datetime.now()
        results = {
            'cbb': {'status': 'pending'}
        }

        logger.info("Starting CBB games scraping...")
        cbb_game_ids = cbb_scraper.scrape_games(current_date)
        logger.info(f"Found {len(cbb_game_ids)} CBB games: {cbb_game_ids}")
        completed = cbb_processor.process_boxscores(cbb_game_ids, current_date, testing_mode=False, testing="")
        if completed:
            results['cbb'] = {
                'status': 'success',
                'game_count': len(cbb_game_ids),
                'game_ids': cbb_game_ids
            }
    except Exception as e:
            logger.error(f"Error processing CBB games: {str(e)}", exc_info=True)
            results['cbb'] = {
                'status': 'error',
                'error': str(e)
            }
            
            


@app.route('/health', methods=['GET'])
def health_check():
    current_time = datetime.utcnow().isoformat() + 'Z'
    return jsonify({
        "message": "Endpoint hit",
        "timestamp": current_time
    }), 200


@app.route('/run-scraper', methods=['GET'])
def run_scraper():
    """Endpoint to manually trigger the scraper"""
    try:
        results = scrape_all_games()
        return jsonify({
            "status": "success",
            "results": results
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    # Run the initial scrape
    logger.info("Running initial scraper job")
    scrape_all_games()
    
    # Start the Flask app
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
