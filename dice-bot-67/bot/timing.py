"""منطق الگو و زمان‌بندی رندوم."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class DelayScheduler:
    """
    الگو پیش‌فرض: ۱۰ تا 🎲 بعد ۵ تا 🎰 و تکرار.
    بین هر ارسال صبر می‌کند (min_delay..max_delay).
    بعد از هر `change_every` چرخهٔ کامل الگو، delay جدید انتخاب می‌شود.
    """

    min_delay: int = 61
    max_delay: int = 100
    change_every: int = 10
    dice_per_cycle: int = 10
    slot_per_cycle: int = 5
    current_delay: int = field(init=False)
    cycles_done: int = 0
    actions_done: int = 0
    _rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        if self.min_delay > self.max_delay:
            raise ValueError("min_delay نباید از max_delay بزرگ‌تر باشد.")
        if self.change_every < 1:
            raise ValueError("change_every باید >= 1 باشد.")
        if self.dice_per_cycle < 0 or self.slot_per_cycle < 0:
            raise ValueError("تعداد تاس/گردونه منفی نباشد.")
        if self.dice_per_cycle + self.slot_per_cycle < 1:
            raise ValueError("حداقل یک ارسال در الگو لازم است.")
        self.current_delay = self._roll_delay()

    @property
    def pattern_len(self) -> int:
        return self.dice_per_cycle + self.slot_per_cycle

    def _roll_delay(self) -> int:
        return self._rng.randint(self.min_delay, self.max_delay)

    @property
    def next_action(self) -> str:
        pos = self.actions_done % self.pattern_len
        if pos < self.dice_per_cycle:
            return "dice"
        return "slot"

    @property
    def progress_in_cycle(self) -> str:
        pos = self.actions_done % self.pattern_len
        if pos < self.dice_per_cycle:
            return f"تاس {pos + 1}/{self.dice_per_cycle}"
        slot_i = pos - self.dice_per_cycle + 1
        return f"گردونه {slot_i}/{self.slot_per_cycle}"

    def mark_action_done(self) -> dict[str, int | str | bool]:
        self.actions_done += 1
        changed = False
        old_delay = self.current_delay

        if self.actions_done % self.pattern_len == 0:
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
        }

    def wait_seconds(self) -> int:
        return int(self.current_delay)
