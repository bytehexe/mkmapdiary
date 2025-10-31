import pytest

from mkmapdiary.util.algo import deep_update


def test_deep_update_simple():
    """Test deep_update with simple dictionaries."""
    d = {"a": 1, "b": 2}
    u = {"b": 3, "c": 4}
    result = deep_update(d, u)

    expected = {"a": 1, "b": 3, "c": 4}
    assert result == expected
    assert d == expected  # Original dict should be modified


def test_deep_update_nested():
    """Test deep_update with nested dictionaries."""
    d = {
        "level1": {
            "level2a": {"key1": "value1", "key2": "value2"},
            "level2b": "simple_value",
        },
        "other": "data",
    }
    u = {
        "level1": {
            "level2a": {"key2": "updated_value2", "key3": "new_value3"},
            "level2c": "new_simple_value",
        },
        "new_top": "new_data",
    }

    result = deep_update(d, u)

    expected = {
        "level1": {
            "level2a": {
                "key1": "value1",
                "key2": "updated_value2",
                "key3": "new_value3",
            },
            "level2b": "simple_value",
            "level2c": "new_simple_value",
        },
        "other": "data",
        "new_top": "new_data",
    }
    assert result == expected


def test_deep_update_empty_dicts():
    """Test deep_update with empty dictionaries."""
    # Empty update dict
    d = {"a": 1, "b": 2}
    u = {}
    result = deep_update(d, u)
    assert result == {"a": 1, "b": 2}

    # Empty original dict
    d = {}
    u = {"a": 1, "b": 2}
    result = deep_update(d, u)
    assert result == {"a": 1, "b": 2}

    # Both empty
    d = {}
    u = {}
    result = deep_update(d, u)
    assert result == {}


def test_deep_update_overwrites_non_dict():
    """Test that deep_update overwrites non-dict values with dict values."""
    d = {"key": "string_value"}
    u = {"key": {"nested": "dict_value"}}
    with pytest.raises(TypeError):
        deep_update(d, u)


def test_deep_update_preserves_references():
    """Test that deep_update modifies the original dictionary in place."""
    original = {"a": 1}
    update = {"b": 2}

    result = deep_update(original, update)

    assert result is original  # Should return the same object
    assert original == {"a": 1, "b": 2}
