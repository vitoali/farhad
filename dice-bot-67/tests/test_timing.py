from bot.timing import DelayScheduler


def test_alternates_dice_and_slot():
    s = DelayScheduler(min_delay=61, max_delay=61, change_every=10)
    assert s.next_action == "dice"
    s.mark_action_done()
    assert s.next_action == "slot"
    s.mark_action_done()
    assert s.next_action == "dice"
    assert s.cycles_done == 1


def test_delay_changes_every_n_cycles():
    s = DelayScheduler(min_delay=61, max_delay=100, change_every=10)
    s._rng.seed(1)
    s.current_delay = 70

    # 9 cycles: no change yet (18 actions)
    for _ in range(18):
        info = s.mark_action_done()
    assert info["cycles_done"] == 9
    assert info["delay_changed"] is False
    assert s.current_delay == 70

    # 10th cycle completes on 20th action
    s.mark_action_done()  # dice of cycle 10
    info = s.mark_action_done()  # slot completes cycle 10
    assert info["cycles_done"] == 10
    assert info["delay_changed"] is True
    assert 61 <= info["current_delay"] <= 100


def test_wait_seconds_returns_current():
    s = DelayScheduler(min_delay=80, max_delay=80, change_every=3)
    assert s.wait_seconds() == 80
