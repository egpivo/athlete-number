import os

def parse_gpu_ids(env_name: str, default_gpus=[0]) -> list[int]:
    """
    Parse comma-separated GPU IDs from an environment variable, e.g. "0,1,2".
    Returns a list of integers. If not found, uses the provided default.
    """
    raw = os.getenv(env_name, None)
    if raw:
        return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
    return default_gpus

