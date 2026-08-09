"""زمان‌بندی و الگوی یکی‌درمیان تاس/گردونه."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class DelayScheduler:
    """
    الگوی قطعی یکی‌درمیان:
      ارسال ۰: 🎲
      ارسال ۱: 🎰
      ارسال ۲: 🎲
      ...

    فاصله بین ارسال‌ها: min_delay..max_delay (پیش‌فرض ۶۱–۸۰)
    هر change_every جفت کامل (تاس+گردونه)، delay عوض می‌شود.
    """

    min_delay: int = 61
    max_delay: int = 80
    change_every: int = 10
    # فیلدهای قدیمی فقط برای سازگاری امضا؛ دیگر الگو را عوض نمی‌کنند
    dice_min: int = 1
    dice_max: int = 1
    slot_per_cycle: int = 1
    dice_per_cycle: int | None = None

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
        # زوج = تاس، فرد = گردونه — قطعی و ساده
        return "dice" if self.actions_done % 2 == 0 else "slot"

    @property
    def progress_in_cycle(self) -> str:
        if self.next_action == "dice":
            return "نوبت تاس 🎲"
        return "نوبت گردونه 🎰"

    def mark_action_done(self) -> dict[str, int | str | bool]:
        just_did = self.next_action
        self.actions_done += 1
        changed = False
        old_delay = self.current_delay
        finished_cycle = False

        # هر ۲ ارسال = یک جفت کامل
        if self.actions_done % 2 == 0:
            finished_cycle = True
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
            "progress": self.progress_in_cycle,
            "just_did": just_did,
            "finished_cycle": finished_cycle,
            "cycle_dice": 1,
        }

    def wait_seconds(self) -> int:
        return int(self.current_delay)
