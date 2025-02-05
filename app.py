from flask import Flask, jsonify
from flask_cors import CORS
from rq_scheduler import Scheduler
from utils.leagues.nba import scraper as nba_scraper
from utils.leagues.nfl import scraper as nfl_scraper
from utils.leagues.nba import processor as nba_processor
from utils.leagues.nfl import processor as nfl_processor
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import pytz
import os
from worker import default_queue, get_job_status, redis_conn
from tasks import scrape_all_games
from rq.job import Job
from rq.worker import Worker
from redis import Redis
import ssl
from utils.job_service import JobService
import psutil
import platform
import requests


load_dotenv()
app = Flask(__name__)
CORS(app)

# Initialize scheduler
scheduler = Scheduler(queue=default_queue, connection=redis_conn)

# Initialize job service
job_service = JobService()

redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

redis_conn = Redis.from_url(
    redis_url,
    ssl_cert_reqs=None,  # Disables certificate verification
)

@app.route("/espn-scraper/start", methods=['POST'])
def start_scraper_job():
    """Start a new scraper job and schedule recurring execution"""
    try:
        # Check for existing scheduled jobs
        existing_jobs = scheduler.get_jobs()
        job_exists = any(job.func_name == 'scrape_all_games' for job in existing_jobs)
        
        if not job_exists:
            # Schedule immediate job
            job = default_queue.enqueue(scrape_all_games)
            
            # Schedule recurring job (every 3 minutes)
            scheduler.schedule(
                scheduled_time=datetime.now(pytz.timezone('US/Pacific')) + timedelta(minutes=3),
                func=scrape_all_games,
                interval=180  # 3 minutes in seconds
            )
            
            return jsonify({
                'message': 'Scraper job started and scheduled',
                'job_id': job.id
            })
        else:
            return jsonify({
                'message': 'Scraper job already scheduled',
                'status': 'existing'
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

@app.route('/health/detailed', methods=['GET'])
def detailed_health():
    try:
        # System info
        system_info = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "platform": platform.platform(),
            "python_version": platform.python_version()
        }

        # Redis health
        redis_healthy = False
        redis_error = None
        try:
            redis_conn.ping()
            redis_healthy = True
        except Exception as e:
            redis_error = str(e)

        # Worker status
        workers = list(Worker.all(connection=redis_conn))
        scheduler_jobs = list(scheduler.get_jobs())

        # Recent jobs status
        query = """
        query GetRecentJobsEspn {
          jobs_espn(order_by: {start_time: desc}, limit: 10) {
            job_id
            task_name
            status
            start_time
            end_time
          }
        }
        """
        recent_jobs = requests.post(
            f"https://lasting-scorpion-21.hasura.app/v1/graphql",
            json={"query": query},
            headers=job_service.headers
        ).json()["data"]["jobs_espn"]

        #if recent_jobs is empty, set it to an empty list
        if not recent_jobs:
            recent_jobs = []
            return jsonify({
                "status": "healthy" if redis_healthy else "degraded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "redis": {
                        "status": "healthy" if redis_healthy else "unhealthy",
                        "error": redis_error
                    },
                    "recent_jobs": recent_jobs
                }
            }), 200

        




        return jsonify({
            "status": "healthy" if redis_healthy else "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {
                "redis": {
                    "status": "healthy" if redis_healthy else "unhealthy",
                    "error": redis_error
                },
                "workers": {
                    "active_count": len(workers),
                    "worker_ids": [str(w.key) for w in workers]
                },
                "scheduler": {
                    "job_count": len(scheduler_jobs),
                    "next_jobs": [
                        {"func": job.func_name, "scheduled_for": job.enqueued_at.isoformat() if job is not None else None}
                        for job in scheduler_jobs[:5] if job is not None

                    ]
                },
                "queue": {
                    "queued_jobs": len(default_queue.jobs),
                    "failed_jobs": len(default_queue.failed_job_registry)
                }
            },
            "system": system_info,
            "recent_jobs": recent_jobs
        }), 200
    except Exception as e:
        print(e)
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
