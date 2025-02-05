from rq_scheduler import Scheduler
from redis import Redis
from tasks import scrape_all_games
import os

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(redis_url)
scheduler = Scheduler(connection=redis_conn)

# Schedule jobs
scheduler.schedule(
    scheduled_time=datetime.utcnow(),
    func=scrape_all_games,
    interval=180  # 3 minutes in seconds
)

# Start the scheduler
scheduler.run() 