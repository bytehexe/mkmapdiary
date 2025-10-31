import pytest


def test_env():
    """Make sure the environment is set up correctly."""
    with pytest.raises(ImportError):
        import whisper  # noqa: F401, I001

    from scipy.spatial import ConvexHull  # noqa: F401, I001
