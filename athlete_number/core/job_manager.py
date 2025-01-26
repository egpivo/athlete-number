import threading
import time

# In-memory storage for job results
job_results = {}
job_results_lock = threading.Lock()

# Job result expiration time in seconds
JOB_RESULT_EXPIRATION = 3600  # 1 hour


class JobResultsManager:
    @staticmethod
    def update(job_id: str, status: str, extracted_text: str = None, error: str = None):
        with job_results_lock:
            timestamp = time.time()
            job_results[job_id] = {
                "status": status,
                "extracted_text": extracted_text,
                "error": error,
                "timestamp": timestamp,
            }

    @staticmethod
    def get(job_id: str):
        with job_results_lock:
            result = job_results.get(job_id, {})
            return result if not JobResultsManager.is_expired(result) else {}

    @staticmethod
    def is_expired(result):
        return result and (
            time.time() - result.get("timestamp", 0) > JOB_RESULT_EXPIRATION
        )
