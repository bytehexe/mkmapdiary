"""Persistent record of which AI prompts actually produced content.

The Art. 50 disclosure on the credits page must name what a build really
generated, not what its feature flags permit. Feature flags alone over-claim:
`features.llms` on with a photos-only trip still advertises titles and tags.

The records live in the build directory because that is exactly the lifetime of
doit's up-to-date database (`dirs.doit_db_path`). `-a` wipes both together, so a
skipped task's record and the artifact it describes can never disagree; an
incremental `-B` run keeps both. The user cache would be wrong on all three
counts: it survives `-a`, it is shared between projects, and `--no-cache`
discards it.

One file per scope rather than one shared file: doit runs threaded and
`text2markdown` fans out per source, so a shared file would need a lock and a
read-modify-write cycle.
"""

import hashlib
import json
import logging
import pathlib
from collections.abc import Collection, Iterable

logger = logging.getLogger(__name__)

#: Keys recorded by the tasks. The first two are `llm_prompts` keys; whisper is
#: not driven through `BaseTask.ai`, so its transcripts get a key of their own.
TITLE = "generate_title"
TAGS = "generate_tags"
TRANSCRIPT = "transcribe"


def usage_path(usage_dir: pathlib.Path, scope: str) -> pathlib.Path:
    """Marker file for `scope`.

    Tasks declare this as a target at creation time, long before the action
    knows what the model returned, so it must depend on the scope alone. Scopes
    are dates and destination paths; hashing keeps them filesystem-safe, and the
    scope itself is stored inside the file so records can be pruned later.
    """
    digest = hashlib.sha256(scope.encode("utf-8")).hexdigest()[:16]
    return usage_dir / f"{digest}.json"


def record_usage(
    usage_dir: pathlib.Path,
    scope: str,
    used: Iterable[str],
) -> None:
    """Record which prompts produced content for `scope`.

    Always writes, even when nothing was generated: the file is a doit target,
    and a missing target would make doit re-run the task — and re-invoke the
    model — on every build of an unchanged source.
    """
    usage_dir.mkdir(parents=True, exist_ok=True)
    path = usage_path(usage_dir, scope)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"scope": scope, "used": sorted(set(used))}, f)


def used_keys(usage_dir: pathlib.Path, live_scopes: Collection[str]) -> set[str]:
    """Every prompt key recorded for a scope that still exists.

    Deleting a source from a persistent build directory leaves its marker
    behind — doit neither re-runs the vanished task nor removes its targets — so
    records are pruned against the scopes the current build still knows about.
    """
    if not usage_dir.is_dir():
        return set()

    keys: set[str] = set()
    for path in sorted(usage_dir.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as f:
                record = json.load(f)
            scope = record["scope"]
            used = record["used"]
        except (OSError, ValueError, KeyError, TypeError):
            logger.warning(f"Ignoring unreadable AI usage record: {path}")
            continue

        if scope in live_scopes:
            keys.update(used)

    return keys
