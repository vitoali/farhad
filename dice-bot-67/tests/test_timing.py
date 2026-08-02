from bot.timing import DelayScheduler


def test_random_dice_then_five_slots():
    s = DelayScheduler(
        min_delay=61,
        max_delay=80,
        change_every=10,
        dice_min=10,
        dice_max=15,
        slot_per_cycle=5,
    )
    s._cycle_dice = 12

    for i in range(12):
        assert s.next_action == "dice", i
        s.mark_action_done()
    for i in range(5):
        assert s.next_action == "slot", i
        s.mark_action_done()
    assert s.cycles_done == 1
    assert 10 <= s._cycle_dice <= 15


def test_delay_range_default_61_80():
    s = DelayScheduler()
    assert s.min_delay == 61
    assert s.max_delay == 80
    assert 61 <= s.current_delay <= 80


def test_delay_changes_every_n_full_patterns():
    s = DelayScheduler(
        min_delay=61,
        max_delay=80,
        change_every=1,  # هر چرخه delay عوض شود
        dice_min=10,
        dice_max=10,
        slot_per_cycle=5,
    )
    s._rng.seed(7)
    s.current_delay = 70
    s._cycle_dice = 10

    for _ in range(14):
        info = s.mark_action_done()
        assert info["delay_changed"] is False
    info = s.mark_action_done()  # تکمیل چرخه ۱
    assert info["cycles_done"] == 1
    assert info["delay_changed"] is True
    assert 61 <= info["current_delay"] <= 80


def test_wait_seconds_returns_current():
    s = DelayScheduler(min_delay=70, max_delay=70, change_every=3)
    assert s.wait_seconds() == 70
