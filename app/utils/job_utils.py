def exponential_backoff(retry_count:int):
    return 2 ** retry_count