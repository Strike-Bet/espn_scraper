import uuid
from datetime import datetime, timezone
import requests
import os
from typing import Optional, Dict, Any

class JobService:
    def __init__(self):
        self.hasura_url = "https://lasting-scorpion-21.hasura.app/v1/graphql"
        self.headers = {
            "X-Hasura-Admin-Secret": "DHieJhzOpml0wBIbEZC5mvsDdSKMnyMC4b8Kx04p0adKUO0zd2e2LSganKK6CRAb",
            "Content-Type": "application/json"
        }

    def create_job(self, task_name: str) -> str:
        job_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc).isoformat()
        mutation = """
       Assuming that your new table jobs_espn has the same fields as jobs, you can update the mutation by replacing the insert_jobs_one field with insert_jobs_espn_one. Here’s the updated mutation:

mutation CreateJob($job_id: uuid!, $task_name: String!, $status: String!, $start_time: timestamptz!) {
  insert_jobs_espn_one(object: {
    job_id: $job_id,
    task_name: $task_name,
    status: $status,
    start_time: $start_time
  }) {
    job_id
  }
}

        """
        variables = {
            "job_id": job_id,
            "task_name": task_name,
            "status": "pending",
            "start_time": start_time
        }
        response = requests.post(
            self.hasura_url,
            json={"query": mutation, "variables": variables},
            headers=self.headers
        )
        response.raise_for_status()
        return job_id

    def update_job_status(self, job_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        end_time = datetime.now(timezone.utc).isoformat() if status in ["completed", "failed"] else None
        mutation = """
        mutation UpdateJob($job_id: uuid!, $status: String!, $end_time: timestamptz, $result: jsonb) {
          update_jobs_by_pk(
            pk_columns: {job_id: $job_id}, 
            _set: {
              status: $status, 
              end_time: $end_time,
              result: $result
            }
          ) {
            job_id
          }
        }
        """
        variables = {
            "job_id": job_id,
            "status": status,
            "end_time": end_time,
            "result": result
        }
        response = requests.post(
            self.hasura_url,
            json={"query": mutation, "variables": variables},
            headers=self.headers
        )
        response.raise_for_status()

    def get_job_details(self, job_id: str) -> Dict[str, Any]:
        query = """
        query GetJob($job_id: uuid!) {
          jobs_by_pk(job_id: $job_id) {
            job_id
            task_name
            status
            start_time
            end_time
            result
          }
        }
        """
        response = requests.post(
            self.hasura_url,
            json={"query": query, "variables": {"job_id": job_id}},
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["data"]["jobs_by_pk"] 