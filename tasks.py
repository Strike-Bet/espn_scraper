from utils.leagues.nba import scraper as nba_scraper
from utils.leagues.nfl import scraper as nfl_scraper
from utils.leagues.cbb import scraper as cbb_scraper
from utils.leagues.nba import processor as nba_processor
from utils.leagues.nfl import processor as nfl_processor
from utils.leagues.cbb import processor as cbb_processor
from datetime import datetime, timedelta
import pytz
import logging
from utils.job_service import JobService
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('espn_scraper')

# Initialize job service
job_service = JobService()

def scrape_all_games():
    """Background task to scrape both NBA and NFL games"""
    job_id = job_service.create_job("scrape_all_games")
    job_service.update_job_status(job_id, "running")
    
    try:
        result = _scrape_all_games()
        job_service.update_job_status(job_id, "completed", result)
        return result
    except Exception as e:
        error_result = {'error': str(e)}
        job_service.update_job_status(job_id, "failed", error_result)
        raise

def _scrape_all_games():
    """Internal function that does the actual scraping work"""
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