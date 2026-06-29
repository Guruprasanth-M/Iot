import RPi.GPIO as GPIO
import time

BUTTON_PIN = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("Waiting for button press...")

try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            print("Button Pressed")
            # Wait until button is released
            while GPIO.input(BUTTON_PIN) == GPIO.HIGH:
                time.sleep(0.01)
            print("Button Released")

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    GPIO.cleanup()
