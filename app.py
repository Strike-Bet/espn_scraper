from flask import Flask, jsonify
from flask_cors import CORS
from rq_scheduler import Scheduler
from utils.leagues.nba import scraper as nba_scraper
from utils.leagues.nfl import scraper as nfl_scraper
from utils.leagues.nba import processor as nba_processor
from utils.leagues.nfl import processor as nfl_processor
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pytz
import os
from worker import default_queue, get_job_status, redis_conn
from tasks import scrape_all_games
from rq.job import Job
from rq.worker import Worker
from redis import Redis
import ssl


load_dotenv()
app = Flask(__name__)
CORS(app)

# Initialize scheduler
scheduler = Scheduler(queue=default_queue, connection=redis_conn)

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

redis_conn = Redis.from_url(
    redis_url)

@app.route("/espn-scraper/start", methods=['POST'])
def start_scraper_job():
    """Start a new scraper job and schedule recurring execution"""
    try:
        # Schedule immediate job
        job = default_queue.enqueue(scrape_all_games)

        
        
        # Schedule recurring job (every 3 minutes)
        scheduler.schedule(
            scheduled_time=datetime.now(pytz.timezone('US/Pacific')) + timedelta(minutes=3),
            func=scrape_all_games,
            interval=180  # 3 minutes in seconds
        )

        print("Job scheduled")
        
        return jsonify({
            'message': 'Scraper job started and scheduled',
            'job_id': job.id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/espn-scraper/job/<job_id>", methods=['GET'])
def check_job_status(job_id):
    """Check status of a specific job"""
    try:
        status = get_job_status(job_id)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    current_time = datetime.utcnow().isoformat() + 'Z'
    return jsonify({
        "message": "Endpoint hit",
        "timestamp": current_time
    }), 200

@app.route('/redis-health', methods=['GET'])
def redis_health():
    try:
        redis_conn.ping()
        return jsonify({
            "status": "healthy",
            "message": "Redis connection successful"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/workers-health', methods=['GET'])
def workers_health():
    try:
        # Convert generator to list before getting length
        workers = list(Worker.all(connection=redis_conn))
        scheduler_jobs = list(scheduler.get_jobs())


        
        return jsonify({
            "status": "healthy",
            "active_workers": len(workers),
            "queued_jobs": len(default_queue.jobs),
            "scheduled_jobs": len(scheduler_jobs),
            "failed_jobs": len(default_queue.failed_job_registry)
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
