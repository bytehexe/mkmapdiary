def test_calculate_rank():
    from mkmapdiary.util import calculate_rank

    assert calculate_rank(radius=1000) == 20
    assert calculate_rank(radius=2000) == 19
    assert calculate_rank(radius=4000) == 18
    assert calculate_rank(radius=8000) == 17
    assert calculate_rank(radius=8002) == 17

    assert calculate_rank(place="city") == 13
    assert calculate_rank(place="town") == 17
    assert calculate_rank(place="village") == 19
    assert calculate_rank(place="hamlet") == 20
    assert calculate_rank(place="isolated_dwelling") == 21

    assert calculate_rank() == 23
    assert calculate_rank(place="unknown_place") is None
    assert calculate_rank(radius=60000) in (13, 14, 15, 16)
