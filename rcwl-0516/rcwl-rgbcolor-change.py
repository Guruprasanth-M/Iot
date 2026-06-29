import RPi.GPIO as GPIO
import time

SENSOR = 27

RED = 19
GREEN = 13
BLUE = 18

GPIO.setmode(GPIO.BCM)

GPIO.setup(SENSOR, GPIO.IN)

GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)

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
last_state = GPIO.LOW

try:
    while True:
        state = GPIO.input(SENSOR)

        # Motion just detected
        if state == GPIO.HIGH and last_state == GPIO.LOW:

            print("Motion Detected!")

            r, g, b = colors[color_index]

            GPIO.output(RED, r)
            GPIO.output(GREEN, g)
            GPIO.output(BLUE, b)

            color_index = (color_index + 1) % len(colors)

        last_state = state
        time.sleep(0.05)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
