#!/usr/bin/env python
from app import scrape_cbb_games
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('espn_scraper_cron')

if __name__ == "__main__":
    logger.info("Starting scheduled ESPN scraper job")
    try:
        results = scrape_cbb_games()
        logger.info(f"Scheduled scraper job completed with results: {results}")
    except Exception as e:
        logger.error(f"Scheduled scraper job failed with error: {str(e)}") 