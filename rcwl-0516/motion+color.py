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
    ("Red",     (1, 0, 0)),
    ("Green",   (0, 1, 0)),
    ("Blue",    (0, 0, 1)),
    ("Yellow",  (1, 1, 0)),
    ("Cyan",    (0, 1, 1)),
    ("Magenta", (1, 0, 1)),
    ("White",   (1, 1, 1)),
]

color_index = 0
last_detection = 0
cooldown = 3  # seconds

try:
    while True:
        if GPIO.input(SENSOR):
            current_time = time.time()

            # Only change color once every 3 seconds
            if current_time - last_detection > cooldown:
                name, (r, g, b) = colors[color_index]

                GPIO.output(RED, r)
                GPIO.output(GREEN, g)
                GPIO.output(BLUE, b)

                print(f"Motion Detected! -> {name}")

                color_index = (color_index + 1) % len(colors)
                last_detection = current_time

        time.sleep(0.05)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
