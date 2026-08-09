from bot.timing import DelayScheduler


def test_strict_alternate():
    s = DelayScheduler(min_delay=61, max_delay=80, change_every=10)
    seq = []
    for _ in range(20):
        seq.append(s.next_action)
        s.mark_action_done()
    assert seq == (["dice", "slot"] * 10)
    assert s.cycles_done == 10


def test_never_two_same_in_a_row():
    s = DelayScheduler()
    prev = None
    for _ in range(50):
        cur = s.next_action
        if prev is not None:
            assert cur != prev
        s.mark_action_done()
        prev = cur


def test_delay_range_default_61_80():
    s = DelayScheduler()
    assert s.min_delay == 61
    assert s.max_delay == 80
    assert 61 <= s.current_delay <= 80


def test_delay_changes_every_n_pairs():
    s = DelayScheduler(min_delay=61, max_delay=80, change_every=2)
    s._rng.seed(1)
    s.current_delay = 70
    s.mark_action_done()  # dice
    info = s.mark_action_done()  # slot -> cycle 1
    assert info["cycles_done"] == 1
    assert info["delay_changed"] is False
    s.mark_action_done()
    info = s.mark_action_done()  # cycle 2 -> change
    assert info["cycles_done"] == 2
    assert info["delay_changed"] is True
    assert 61 <= info["current_delay"] <= 80
