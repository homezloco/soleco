from prometheus_client import Counter, Histogram
import time

# Trading Metrics
trade_attempts = Counter(
    'pumpfun_trade_attempts_total', 
    'Total number of trade attempts', 
    ['trade_type']
)

trade_successes = Counter(
    'pumpfun_trade_successes_total', 
    'Total number of successful trades', 
    ['trade_type']
)

trade_failures = Counter(
    'pumpfun_trade_failures_total', 
    'Total number of trade failures', 
    ['trade_type', 'reason']
)

trade_duration = Histogram(
    'pumpfun_trade_duration_seconds', 
    'Trade operation duration', 
    ['trade_type']
)

def track_trade_attempt(trade_type):
    """Decorator to track trade attempts and performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            trade_attempts.labels(trade_type=trade_type).inc()
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                trade_successes.labels(trade_type=trade_type).inc()
                return result
            except Exception as e:
                trade_failures.labels(
                    trade_type=trade_type, 
                    reason=type(e).__name__
                ).inc()
                raise
            finally:
                trade_duration.labels(trade_type=trade_type).observe(
                    time.time() - start_time
                )
        return wrapper
    return decorator
