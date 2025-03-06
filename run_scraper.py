#!/usr/bin/env python
from datetime import datetime
import pytz
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('espn_scraper_runner')

# Import the scraping function directl
from tasks import scrape_all_games

if __name__ == "__main__":
    logger.info("Starting ESPN scraper job")
    try:
        result = scrape_all_games()
        logger.info(f"Scraper job completed with result: {result}")
    except Exception as e:
        logger.error(f"Scraper job failed with error: {str(e)}")