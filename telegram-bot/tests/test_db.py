from pathlib import Path

from bot.db import Database


def test_user_subscribe_flow(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    db.upsert_user(10, "ali", "Ali")
    assert db.get_user(10) is not None
    assert db.list_subscribers() == [10]

    db.set_subscribed(10, False)
    assert db.list_subscribers() == []

    db.set_subscribed(10, True)
    db.mark_blocked(10)
    assert db.list_subscribers() == []
    stats = db.stats()
    assert stats["total_users"] == 1
    assert stats["blocked"] == 1


def test_save_signal(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    sid = db.save_signal(symbol="EURUSD", side="BUY", entry="1.1", source="manual")
    assert sid >= 1
    assert db.stats()["signals"] == 1
