from bot.timing import DelayScheduler


def test_ten_dice_then_five_slots():
    s = DelayScheduler(
        min_delay=61,
        max_delay=61,
        change_every=10,
        dice_per_cycle=10,
        slot_per_cycle=5,
    )
    for i in range(10):
        assert s.next_action == "dice", i
        s.mark_action_done()
    for i in range(5):
        assert s.next_action == "slot", i
        s.mark_action_done()
    assert s.next_action == "dice"
    assert s.cycles_done == 1


def test_delay_changes_every_n_full_patterns():
    s = DelayScheduler(
        min_delay=61,
        max_delay=100,
        change_every=2,
        dice_per_cycle=10,
        slot_per_cycle=5,
    )
    s._rng.seed(1)
    s.current_delay = 70

    # یک الگوی کامل = ۱۵ ارسال → هنوز change_every=2 نشده
    for _ in range(15):
        info = s.mark_action_done()
    assert info["cycles_done"] == 1
    assert info["delay_changed"] is False
    assert s.current_delay == 70

    # الگوی دوم کامل → عوض شود
    for _ in range(14):
        s.mark_action_done()
    info = s.mark_action_done()
    assert info["cycles_done"] == 2
    assert info["delay_changed"] is True
    assert 61 <= info["current_delay"] <= 100


def test_wait_seconds_returns_current():
    s = DelayScheduler(min_delay=80, max_delay=80, change_every=3)
    assert s.wait_seconds() == 80


def test_progress_label():
    s = DelayScheduler(dice_per_cycle=10, slot_per_cycle=5, min_delay=61, max_delay=61)
    assert "تاس 1/10" in s.progress_in_cycle
    for _ in range(10):
        s.mark_action_done()
    assert "گردونه 1/5" in s.progress_in_cycle
