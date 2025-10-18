import pytest


def test_env():
    """Make sure the environment is set up correctly."""
    with pytest.raises(ImportError):
        import whisper

    from scipy.spatial import ConvexHull
