from redis import Redis
from rq import Queue, Worker
from rq.job import Job
import os

# Configure Redis connection
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_conn = Redis.from_url(redis_url)

# Create queue
default_queue = Queue('default', connection=redis_conn)

def get_job_status(job_id):
    """Get status of a specific job"""
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            'id': job.id,
            'status': job.get_status(),
            'result': job.result,
            'enqueued_at': job.enqueued_at.isoformat() if job.enqueued_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None
        }
    except Exception as e:
        return {'error': str(e)} 