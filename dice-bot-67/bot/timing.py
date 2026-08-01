"""منطق زمان‌بندی رندوم و تعویض هر N چرخه."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class DelayScheduler:
    """
    هر چرخه کامل = یک 🎲 + یک 🎰.
    بعد از `change_every` چرخه، delay جدید بین min/max انتخاب می‌شود.
    """

    min_delay: int = 61
    max_delay: int = 100
    change_every: int = 10
    current_delay: int = field(init=False)
    cycles_done: int = 0
    actions_done: int = 0
    _rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        if self.min_delay > self.max_delay:
            raise ValueError("min_delay نباید از max_delay بزرگ‌تر باشد.")
        if self.change_every < 1:
            raise ValueError("change_every باید >= 1 باشد.")
        self.current_delay = self._roll_delay()

    def _roll_delay(self) -> int:
        return self._rng.randint(self.min_delay, self.max_delay)

    @property
    def next_action(self) -> str:
        """dice روی اکشن‌های زوج، slot روی فرد."""
        return "dice" if self.actions_done % 2 == 0 else "slot"

    def mark_action_done(self) -> dict[str, int | str | bool]:
        """بعد از هر کلیک کامل (تاس/اسلات + SEND) صدا زده شود."""
        self.actions_done += 1
        changed = False
        old_delay = self.current_delay

        # هر دو اکشن = یک چرخه
        if self.actions_done % 2 == 0:
            self.cycles_done += 1
            if self.cycles_done % self.change_every == 0:
                self.current_delay = self._roll_delay()
                changed = True

        return {
            "actions_done": self.actions_done,
            "cycles_done": self.cycles_done,
            "current_delay": self.current_delay,
            "previous_delay": old_delay,
            "delay_changed": changed,
            "next_action": self.next_action,
        }

    def wait_seconds(self) -> int:
        return int(self.current_delay)
