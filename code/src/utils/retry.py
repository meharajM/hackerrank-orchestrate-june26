"""
Exponential backoff retry utilities.
"""
from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Any, Callable, Type, Union

logger = logging.getLogger(__name__)


def retry_with_backoff(
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> Callable:
    """Decorator to retry a function call with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise
                    
                    wait_time = delay * (backoff_factor ** attempt)
                    logger.warning(
                        f"Exception caught in {func.__name__}: {e}. "
                        f"Retrying in {wait_time:.2f} seconds (attempt {attempt+1}/{max_retries})..."
                    )
                    time.sleep(wait_time)
            raise RuntimeError(f"Failed to execute {func.__name__} after retrying")
        return wrapper
    return decorator
