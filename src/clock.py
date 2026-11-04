"""The agent's notion of "now", in the store's timezone.

REFERENCE_DATE pins "today" because the data is a snapshot (spec A3).
"""

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

STORE_TZ = ZoneInfo("America/Campo_Grande")


def now() -> datetime:
    current = datetime.now(STORE_TZ)
    pinned = os.getenv("REFERENCE_DATE", "").strip()
    if pinned:
        day = date.fromisoformat(pinned)
        current = current.replace(year=day.year, month=day.month, day=day.day)
    return current


def today() -> date:
    return now().date()
