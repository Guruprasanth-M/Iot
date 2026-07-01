"""Reusable driver for the RCWL-0516 microwave radar motion sensor.

The RCWL-0516 exposes a single digital ``OUT`` pin that goes HIGH while motion
is detected and returns LOW after its on-board hold time expires. This module
wraps that pin behind a small, reusable class with software debounce, an
optional cooldown, and callbacks for motion-start / motion-stop events.

Wiring (Raspberry Pi, BCM numbering) — matches the other scripts in this folder:

    RCWL-0516        Raspberry Pi
    ---------        ------------
    VIN  ----------- 5V   (pin 2 or 4)
    GND  ----------- GND  (pin 6)
    OUT  ----------- GPIO 27 (BCM), physical pin 13

Example:
    from rcwl0516 import RCWL0516

    def on_motion():
        print("Motion started")

    def on_clear():
        print("Area clear")

    sensor = RCWL0516(pin=27, on_motion=on_motion, on_clear=on_clear)
    sensor.run()   # blocks; Ctrl-C to stop and clean up GPIO
"""

from __future__ import annotations

import time
from typing import Callable, Optional

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover - allows import on non-Pi machines
    GPIO = None


# Default OUT pin (BCM). Keep in sync with test.py / motion+color.py in this folder.
DEFAULT_SENSOR_PIN = 27


class RCWL0516:
    """Driver for a single RCWL-0516 sensor on one GPIO pin.

    Args:
        pin: BCM GPIO number wired to the sensor's OUT pin.
        on_motion: called once each time motion transitions LOW -> HIGH.
        on_clear: called once each time motion transitions HIGH -> LOW.
        cooldown: minimum seconds between successive ``on_motion`` callbacks.
        debounce: seconds a reading must be stable before it is accepted.
        poll_interval: seconds to sleep between polls of the pin.
    """

    def __init__(
        self,
        pin: int = DEFAULT_SENSOR_PIN,
        on_motion: Optional[Callable[[], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        cooldown: float = 0.0,
        debounce: float = 0.05,
        poll_interval: float = 0.05,
    ) -> None:
        if GPIO is None:
            raise RuntimeError(
                "RPi.GPIO is not available. Run this on a Raspberry Pi with "
                "the RPi.GPIO package installed."
            )

        self.pin = pin
        self.on_motion = on_motion
        self.on_clear = on_clear
        self.cooldown = cooldown
        self.debounce = debounce
        self.poll_interval = poll_interval

        self._state = GPIO.LOW            # last accepted (debounced) state
        self._last_motion_time = 0.0      # for cooldown gating
        self._setup_done = False

    # -- GPIO lifecycle ---------------------------------------------------

    def setup(self) -> None:
        """Configure GPIO. Safe to call more than once."""
        if self._setup_done:
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        self._setup_done = True

    def cleanup(self) -> None:
        """Release the GPIO pins."""
        if self._setup_done:
            GPIO.cleanup()
            self._setup_done = False

    # -- reading ----------------------------------------------------------

    def _read_debounced(self) -> int:
        """Read the pin, requiring the level to be stable for ``debounce`` seconds."""
        first = GPIO.input(self.pin)
        if self.debounce > 0:
            time.sleep(self.debounce)
            if GPIO.input(self.pin) != first:
                return self._state  # unstable -> keep previous accepted state
        return first

    def poll(self) -> bool:
        """Poll once, firing callbacks on edges. Returns True if motion is present."""
        self.setup()
        reading = self._read_debounced()

        # Rising edge: motion just started.
        if reading == GPIO.HIGH and self._state == GPIO.LOW:
            now = time.time()
            if now - self._last_motion_time >= self.cooldown:
                self._last_motion_time = now
                if self.on_motion:
                    self.on_motion()
            self._state = GPIO.HIGH

        # Falling edge: area cleared.
        elif reading == GPIO.LOW and self._state == GPIO.HIGH:
            self._state = GPIO.LOW
            if self.on_clear:
                self.on_clear()

        return self._state == GPIO.HIGH

    def run(self) -> None:
        """Continuously poll until interrupted, then clean up."""
        self.setup()
        try:
            while True:
                self.poll()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            pass
        finally:
            self.cleanup()


if __name__ == "__main__":
    def _motion() -> None:
        print(f"[{time.strftime('%H:%M:%S')}] Motion detected!")

    def _clear() -> None:
        print(f"[{time.strftime('%H:%M:%S')}] Area clear.")

    RCWL0516(pin=DEFAULT_SENSOR_PIN, on_motion=_motion, on_clear=_clear, cooldown=1.0).run()
