import collections.abc
from typing import Any, Mapping, MutableMapping


def deep_update(
    d: MutableMapping[str, Any], u: Mapping[str, Any]
) -> MutableMapping[str, Any]:
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d
