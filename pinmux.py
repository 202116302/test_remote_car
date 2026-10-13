import Jetson.GPIO as GPIO, timeㅅㄷ
GPIO.setmode(GPIO.BOARD)
pins = [11, 13, 15, 16, 29, 31, 33, 35]
GPIO.setup(pins, GPIO.OUT, initial=GPIO.LOW)
for p in pins:
    print(p, "HIGH"); GPIO.output(p, GPIO.HIGH); time.sleep(3)
    GPIO.output(p, GPIO.LOW)
GPIO.cleanup()
