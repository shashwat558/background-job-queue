def exponential_backoff(attempt_count:int):
    return 2 ** attempt_count