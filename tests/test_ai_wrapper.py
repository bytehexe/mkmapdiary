import json
from typing import Any

from mkmapdiary.lib.asset import AssetMetadata
from mkmapdiary.tasks.base.baseTask import BaseTask


class DummyTask(BaseTask):
    def __init__(self) -> None:
        self._config: dict[str, Any] = {
            "llm_prompts": {
                "summarize_journal_entry": {
                    "translation_key": "journal_prompt",
                    "model": "dummy",
                    "options": {},
                },
                "generate_tags": {
                    "translation_key": "tags_prompt",
                    "model": "dummy",
                    "options": {},
                },
            },
            "strings": {
                "journal_prompt": "Summarize: {text}",
                "tags_prompt": "Tags: {text}",
            },
            "features": {"llms": {"enabled": True}},
        }

    def handle(self, source: Any) -> Any:
        return None

    @property
    def gettext(self) -> Any:
        return lambda text: text

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    @property
    def db(self) -> Any:
        return None

    @property
    def dirs(self) -> Any:
        return None

    @property
    def cache(self) -> dict:
        return {}


def test_ai_returns_dataclass_for_schema() -> None:
    task = DummyTask()
    task._BaseTask__ai = (  # type: ignore[attr-defined]
        lambda prompt, model, message_params=None, **params: json.dumps(
            {
                "@context": "http://purl.org/dc/elements/1.1/",
                "identifier": "id",
                "title": "Title",
                "description": "Description",
                "subject": ["tag1"],
                "coverage": ["place"],
                "created": "2026-04-09",
                "media_type": "text/plain",
            }
        )
    )

    metadata = task.ai(
        "summarize_journal_entry", {"text": "Hello"}, schema=AssetMetadata
    )

    assert isinstance(metadata, AssetMetadata)
    assert metadata.identifier == "id"
    assert metadata.title == "Title"
    assert metadata.subject == ["tag1"]


def test_ai_returns_none_for_schema_when_llms_disabled() -> None:
    """`__ai` yields "" with LLMs off, which json.loads cannot parse.

    Reached by any build with features.llms disabled — example/config.yaml
    does exactly that — via JournalSummarizer.
    """
    task = DummyTask()
    task._config["features"]["llms"]["enabled"] = False

    result = task.ai("summarize_journal_entry", {"text": "Hello"}, schema=AssetMetadata)

    assert result is None


def test_ai_returns_empty_string_without_schema_when_llms_disabled() -> None:
    task = DummyTask()
    task._config["features"]["llms"]["enabled"] = False

    assert task.ai("generate_tags", {"text": "Hello"}) == ""


def test_ai_returns_string_without_schema() -> None:
    task = DummyTask()
    task._BaseTask__ai = (  # type: ignore[attr-defined]
        lambda prompt, model, message_params=None, **params: "just text"
    )

    result = task.ai("generate_tags", {"text": "Hello"})

    assert result == "just text"
