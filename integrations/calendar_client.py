import contextlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("dex.integrations.calendar")


class CalendarClient:
    def __init__(self, ical_path: str | Path | None = None) -> None:
        self._ical_path = Path(ical_path) if ical_path else None
        self._events: list[dict[str, Any]] = []

    def load_ical(self, path: str | Path | None = None) -> list[dict[str, Any]]:
        p = Path(path) if path else self._ical_path
        if not p or not p.exists():
            logger.warning("No iCal file found")
            return
        try:
            import icalendar
            with open(p, "rb") as f:
                cal = icalendar.Calendar.from_ical(f.read())
            for component in cal.walk():
                if component.name == "VEVENT":
                    self._events.append({
                        "summary": str(component.get("summary", "")),
                        "start": component.get("dtstart").dt.isoformat() if component.get("dtstart") else "",
                        "end": component.get("dtend").dt.isoformat() if component.get("dtend") else "",
                        "location": str(component.get("location", "")),
                        "description": str(component.get("description", ""))[:200]
                    })
            logger.info(f"Loaded {len(self._events)} events from iCal")
        except ImportError:
            logger.warning("icalendar not installed, loading raw")
            self._load_raw_ical(p)
        except Exception as e:
            logger.error(f"Failed to load iCal: {e}")

    def _load_raw_ical(self, path: Path) -> list[dict[str, Any]]:
        try:
            text = path.read_text(encoding="utf-8")
            for block in text.split("BEGIN:VEVENT"):
                if "END:VEVENT" not in block:
                    continue
                event = block[:block.index("END:VEVENT")]
                summary = ""
                for line in event.split("\n"):
                    if line.startswith("SUMMARY"):
                        summary = line.split(":", 1)[-1].strip()
                    elif line.startswith("DTSTART"):
                        dt = line.split(":", 1)[-1].strip()
                        if dt:
                            with contextlib.suppress(Exception):
                                dt = f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}T{dt[9:11]}:{dt[11:13]}:{dt[13:15]}"
                if summary:
                    self._events.append({"summary": summary, "start": dt if 'dt' in dir() else ""})
        except Exception as e:
            logger.error(f"Raw iCal parse error: {e}")

    def get_today_events(self) -> list[dict[str, Any]]:
        today = datetime.now().date().isoformat()
        return [e for e in self._events if today in str(e.get("start", ""))]

    def get_upcoming(self, days: int = 7) -> list[dict[str, Any]]:
        result = []
        for e in self._events:
            start = e.get("start", "")
            if start:
                try:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    if 0 <= (dt - datetime.now()).days <= days:
                        result.append(e)
                except (ValueError, TypeError):
                    pass
        return sorted(result, key=lambda x: x.get("start", ""))

    def create_event(self, summary: str, start: str, end: str,
                     location: str = "", description: str = "") -> bool:
        try:
            import icalendar
            cal = icalendar.Calendar()
            event = icalendar.Event()
            event.add("summary", summary)
            event.add("dtstart", datetime.fromisoformat(start))
            event.add("dtend", datetime.fromisoformat(end))
            if location:
                event.add("location", location)
            if description:
                event.add("description", description)
            cal.add_component(event)

            out_path = self._ical_path or Path("data/calendar/new_event.ics")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(cal.to_ical())
            logger.info(f"Event created: {summary}")
            return True
        except ImportError:
            logger.error("icalendar not installed")
            return False
