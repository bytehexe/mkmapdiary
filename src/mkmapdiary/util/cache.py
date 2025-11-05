from collections.abc import Callable
from typing import Any


def with_cache(
    cache: Any,
    key: str,
    compute_func: Callable[..., Any],
    *args: Any,
    cache_args: tuple[Any, ...] | None = None,
) -> Any:
    """Get the value from cache or compute it if not present."""

    assert type(key) is str, "Key must be a string"
    assert callable(compute_func), "compute_func must be callable"

    if cache_args is None:
        full_key = (key, args)
    else:
        full_key = (key, cache_args)

    try:
        return cache[full_key]
    except KeyError:
        value = compute_func(*args)
        cache[full_key] = value
        return value
