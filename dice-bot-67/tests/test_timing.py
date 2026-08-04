from bot.timing import DelayScheduler


def test_alternate_dice_and_slot():
    s = DelayScheduler(
        min_delay=61,
        max_delay=80,
        change_every=10,
        dice_min=1,
        dice_max=1,
        slot_per_cycle=1,
    )
    assert s.next_action == "dice"
    s.mark_action_done()
    assert s.next_action == "slot"
    s.mark_action_done()
    assert s.next_action == "dice"
    assert s.cycles_done == 1


def test_delay_range_default_61_80():
    s = DelayScheduler()
    assert s.min_delay == 61
    assert s.max_delay == 80
    assert 61 <= s.current_delay <= 80


def test_delay_changes_every_n_full_patterns():
    s = DelayScheduler(
        min_delay=61,
        max_delay=80,
        change_every=1,
        dice_min=1,
        dice_max=1,
        slot_per_cycle=1,
    )
    s._rng.seed(7)
    s.current_delay = 70
    info = s.mark_action_done()  # dice
    assert info["delay_changed"] is False
    info = s.mark_action_done()  # slot completes cycle
    assert info["cycles_done"] == 1
    assert info["delay_changed"] is True
    assert 61 <= info["current_delay"] <= 80


def test_wait_seconds_returns_current():
    s = DelayScheduler(min_delay=70, max_delay=70, change_every=3)
    assert s.wait_seconds() == 70
