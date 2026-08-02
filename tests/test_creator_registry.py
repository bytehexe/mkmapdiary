from mkmapdiary.tasks.gpxTask import GPXTask


def test_track_creators_is_a_property() -> None:
    """Asserts on the class rather than an instance.

    GPXTask inherits BaseTask's abstract properties (config, db, dirs, cache,
    gettext, handle), so a bare instantiation raises TypeError before
    track_creators is ever reached -- not the AttributeError the brief
    expected. Per the brief's Step 2 fallback, assert on the class instead.
    """
    assert isinstance(GPXTask.track_creators, property)
