import RPi.GPIO as GPIO
import time

BUTTON = 27

RED = 19
GREEN = 13
BLUE = 18

GPIO.setmode(GPIO.BCM)

GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)

# (Red, Green, Blue)
colors = [
    (1, 0, 0),  # Red
    (0, 1, 0),  # Green
    (0, 0, 1),  # Blue
    (1, 1, 0),  # Yellow
    (0, 1, 1),  # Cyan
    (1, 0, 1),  # Magenta
    (1, 1, 1),  # White
]

color_index = 0

try:
    while True:
        if GPIO.input(BUTTON) == GPIO.HIGH:

            r, g, b = colors[color_index]

            GPIO.output(RED, r)
            GPIO.output(GREEN, g)
            GPIO.output(BLUE, b)

            color_index = (color_index + 1) % len(colors)

            # Wait until button is released
            while GPIO.input(BUTTON) == GPIO.HIGH:
                time.sleep(0.01)

            # Debounce
            time.sleep(0.2)

        time.sleep(0.01)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
