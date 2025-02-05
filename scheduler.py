from rq_scheduler import Scheduler
from redis import Redis
from tasks import scrape_all_games
import os
import ssl

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

redis_conn = Redis.from_url(
    redis_url,
    ssl_cert_reqs=None,  # Disables certificate verification
    ssl=True
)

scheduler = Scheduler(connection=redis_conn)

# Schedule jobs
scheduler.schedule(
    scheduled_time=datetime.utcnow(),
    func=scrape_all_games,
    interval=180  # 3 minutes in seconds
)

# Start the scheduler
scheduler.run() 