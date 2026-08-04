"""منطق الگو و زمان‌بندی رندوم."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class DelayScheduler:
    """
    هر چرخه:
      - تعداد رندوم تاس بین dice_min..dice_max (پیش‌فرض ۱)
      - بعد slot_per_cycle گردونه (پیش‌فرض ۱)
      - تکرار

    بین هر ارسال صبر min_delay..max_delay (پیش‌فرض ۶۱–۸۰).
    بعد از هر change_every چرخه کامل، delay جدید انتخاب می‌شود.
    """

    min_delay: int = 61
    max_delay: int = 80
    change_every: int = 10
    dice_min: int = 1
    dice_max: int = 1
    slot_per_cycle: int = 1
    # سازگاری با کانفیگ قدیمی
    dice_per_cycle: int | None = None

    current_delay: int = field(init=False)
    cycles_done: int = 0
    actions_done: int = 0
    _cycle_dice: int = field(init=False)
    _pos_in_cycle: int = 0
    _rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        if self.min_delay > self.max_delay:
            raise ValueError("min_delay نباید از max_delay بزرگ‌تر باشد.")
        if self.change_every < 1:
            raise ValueError("change_every باید >= 1 باشد.")

        # اگر فقط dice_per_cycle آمده باشد، همان را ثابت استفاده کن
        if self.dice_per_cycle is not None:
            self.dice_min = int(self.dice_per_cycle)
            self.dice_max = int(self.dice_per_cycle)

        if self.dice_min < 0 or self.dice_max < 0 or self.slot_per_cycle < 0:
            raise ValueError("تعداد تاس/گردونه منفی نباشد.")
        if self.dice_min > self.dice_max:
            raise ValueError("dice_min نباید از dice_max بزرگ‌تر باشد.")
        if self.dice_max + self.slot_per_cycle < 1:
            raise ValueError("حداقل یک ارسال در الگو لازم است.")

        self.current_delay = self._roll_delay()
        self._cycle_dice = self._roll_dice_count()
        self._pos_in_cycle = 0

    def _roll_delay(self) -> int:
        return self._rng.randint(self.min_delay, self.max_delay)

    def _roll_dice_count(self) -> int:
        return self._rng.randint(self.dice_min, self.dice_max)

    @property
    def pattern_len(self) -> int:
        return self._cycle_dice + self.slot_per_cycle

    @property
    def next_action(self) -> str:
        if self._pos_in_cycle < self._cycle_dice:
            return "dice"
        return "slot"

    @property
    def progress_in_cycle(self) -> str:
        if self._pos_in_cycle < self._cycle_dice:
            return f"تاس {self._pos_in_cycle + 1}/{self._cycle_dice}"
        slot_i = self._pos_in_cycle - self._cycle_dice + 1
        return f"گردونه {slot_i}/{self.slot_per_cycle}"

    def mark_action_done(self) -> dict[str, int | str | bool]:
        self.actions_done += 1
        self._pos_in_cycle += 1
        changed = False
        old_delay = self.current_delay
        finished_cycle = False

        if self._pos_in_cycle >= self.pattern_len:
            finished_cycle = True
            self.cycles_done += 1
            self._pos_in_cycle = 0
            self._cycle_dice = self._roll_dice_count()
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
            "cycle_dice": self._cycle_dice,
            "finished_cycle": finished_cycle,
        }

    def wait_seconds(self) -> int:
        return int(self.current_delay)
