import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def with_cache(
    cache: Any,
    key: str,
    compute_func: Callable[..., Any],
    *args: Any,
    cache_args: tuple[Any, ...] | None = None,
    bypass_cache: bool = False,
) -> Any:
    """Get the value from cache or compute it if not present."""

    assert type(key) is str, "Key must be a string"
    assert callable(compute_func), "compute_func must be callable"

    if bypass_cache:
        return compute_func(*args)

    if cache_args is None:
        full_key = (key, args)
    else:
        full_key = (key, cache_args)

    try:
        value = cache[full_key]
        logger.info(f"Cache hit for key: {full_key}")
        return value
    except KeyError:
        value = compute_func(*args)
        cache[full_key] = value
        logger.info(f"Cache miss for key: {full_key}. Computed and cached new value.")
        return value
