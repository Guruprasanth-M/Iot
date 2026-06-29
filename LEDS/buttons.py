
import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
channel = 27

GPIO.setup(channel, GPIO.IN)

while True:
	if(GPIO.input(channel) == GPIO.LOW):
		print("1")
		time.sleep(0.1)
