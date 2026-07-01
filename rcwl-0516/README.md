# RCWL-0516 — microwave radar motion sensor

Experiments and a small reusable driver for the RCWL-0516 Doppler radar motion
sensor on a Raspberry Pi.

## Pinout / wiring (BCM numbering)

| RCWL-0516 | Raspberry Pi        | Notes                          |
|-----------|---------------------|--------------------------------|
| `VIN`     | 5V (physical 2/4)   | 4–28 V input; 5 V from the Pi  |
| `GND`     | GND (physical 6)    | common ground                  |
| `OUT`     | **GPIO 27** (pin 13)| HIGH on motion, LOW when clear |

Optional RGB LED used by `motion+color.py` / `rcwl-rgbcolor-change.py`:
`RED=19`, `GREEN=13`, `BLUE=18` (BCM).

## Files

| File                       | What it does                                                        |
|----------------------------|--------------------------------------------------------------------|
| `rcwl0516.py`              | **Reusable `RCWL0516` driver class** — debounce, cooldown, motion/clear callbacks. |
| `motion_logger.py`        | Logs timestamped motion events (with episode duration) to `motion_log.csv`. |
| `test.py`                 | Minimal raw read of the OUT pin.                                    |
| `motion+color.py`         | Cycles an RGB LED colour on each detection.                        |
| `rcwl-rgbcolor-change.py` | Edge-triggered RGB colour change.                                  |

## Quick start

```bash
# raw pin read
python3 test.py

# reusable driver, prints motion start/stop
python3 rcwl0516.py

# CSV motion logger built on the driver
python3 motion_logger.py
```

### Using the driver in your own code

```python
from rcwl0516 import RCWL0516

sensor = RCWL0516(
    pin=27,
    on_motion=lambda: print("Motion!"),
    on_clear=lambda: print("Clear"),
    cooldown=1.0,   # ignore repeat triggers within 1s
)
sensor.run()        # blocks; Ctrl-C cleans up GPIO
```

Requires `RPi.GPIO` (`pip install RPi.GPIO`) and must run on the Pi.
