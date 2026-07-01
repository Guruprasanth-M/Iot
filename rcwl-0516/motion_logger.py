"""Motion logger built on the reusable RCWL0516 driver.

Logs every motion-start and area-clear event to both the console and a CSV
file (``motion_log.csv`` by default), so you get a timestamped history of
detections plus how long each motion episode lasted.

Run on a Raspberry Pi:

    python3 motion_logger.py

Wiring is the same as rcwl0516.py: sensor OUT -> BCM GPIO 27.
"""

from __future__ import annotations

import csv
import os
import time

from rcwl0516 import RCWL0516, DEFAULT_SENSOR_PIN

LOG_FILE = "motion_log.csv"


class MotionLogger:
    """Writes timestamped motion events to a CSV file and the console."""

    def __init__(self, log_file: str = LOG_FILE) -> None:
        self.log_file = log_file
        self._motion_started_at: float | None = None
        self._ensure_header()

    def _ensure_header(self) -> None:
        if not os.path.exists(self.log_file) or os.path.getsize(self.log_file) == 0:
            with open(self.log_file, "w", newline="") as fh:
                csv.writer(fh).writerow(["timestamp", "event", "duration_s"])

    def _write(self, event: str, duration: str = "") -> None:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, "a", newline="") as fh:
            csv.writer(fh).writerow([stamp, event, duration])
        print(f"[{stamp}] {event}" + (f" ({duration}s)" if duration else ""))

    def on_motion(self) -> None:
        self._motion_started_at = time.time()
        self._write("motion_detected")

    def on_clear(self) -> None:
        duration = ""
        if self._motion_started_at is not None:
            duration = f"{time.time() - self._motion_started_at:.1f}"
            self._motion_started_at = None
        self._write("area_clear", duration)


def main() -> None:
    logger = MotionLogger()
    sensor = RCWL0516(
        pin=DEFAULT_SENSOR_PIN,
        on_motion=logger.on_motion,
        on_clear=logger.on_clear,
        cooldown=1.0,
    )
    print(f"Logging RCWL-0516 motion on BCM pin {DEFAULT_SENSOR_PIN} -> {LOG_FILE}")
    print("Press Ctrl-C to stop.")
    sensor.run()


if __name__ == "__main__":
    main()
