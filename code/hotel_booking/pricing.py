"""Price calculation: single > range > weekend > base."""

from __future__ import annotations

from datetime import date

from .domain import PriceRuleType
from .repository import Repository
from .utils import parse_date


class PricingService:
    """Resolve the effective price of a room type for a given night."""

    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    @staticmethod
    def is_weekend(day: date) -> bool:
        """Friday and Saturday are weekend nights (Python Monday is 0)."""
        return day.weekday() in (4, 5)

    def effective_price(self, room_type: dict, day: date) -> float:
        """Return the highest-priority price that matches the date."""
        rules = self.repo.price_rules(room_type["id"])
        day_text = day.isoformat()
        candidates: dict[str, list[float]] = {}
        for rule in rules:
            if not rule["start_date"] <= day_text <= rule["end_date"]:
                continue
            rule_type = rule["rule_type"]
            if rule_type == PriceRuleType.WEEKEND and not self.is_weekend(day):
                continue
            candidates.setdefault(rule_type, []).append(float(rule["price"]))

        for rule_type in (
            PriceRuleType.SINGLE.value,
            PriceRuleType.RANGE.value,
            PriceRuleType.WEEKEND.value,
        ):
            if candidates.get(rule_type):
                return min(candidates[rule_type])
        return float(room_type["base_price"])

    def quote(self, room_type: dict, check_in: str, check_out: str) -> list[tuple[date, float]]:
        """Return (night, price) pairs for a stay."""
        start = parse_date(check_in)
        end = parse_date(check_out)
        nights: list[tuple[date, float]] = []
        cursor = start
        while cursor < end:
            nights.append((cursor, self.effective_price(room_type, cursor)))
            cursor = cursor.fromordinal(cursor.toordinal() + 1)
        return nights
