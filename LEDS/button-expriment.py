import RPi.GPIO as GPIO
import time

BUTTON = 27

RED = 19
GREEN = 13
BLUE = 18

GPIO.setmode(GPIO.BCM)

# Button
#GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
# RGB LED
GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)

# Start with LED off
GPIO.output(RED, GPIO.LOW)
GPIO.output(GREEN, GPIO.LOW)
GPIO.output(BLUE, GPIO.LOW)

try:
    while True:
        if GPIO.input(BUTTON) == GPIO.HIGH:
            # Turn RGB LED ON (White)
            GPIO.output(RED, GPIO.HIGH)
            GPIO.output(GREEN, GPIO.HIGH)
            GPIO.output(BLUE, GPIO.HIGH)
        else:
            # Turn RGB LED OFF
            GPIO.output(RED, GPIO.LOW)
            GPIO.output(GREEN, GPIO.LOW)
            GPIO.output(BLUE, GPIO.LOW)

        time.sleep(0.01)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
