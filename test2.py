import Jetson.GPIO as GPIO
import time

# -----------------------------
# GPIO 설정
# -----------------------------

GPIO.setmode(GPIO.BOARD)

# 앞쪽 L298N
FRONT_IN1 = 11
FRONT_IN2 = 13
FRONT_IN3 = 15
FRONT_IN4 = 16

# 뒤쪽 L298N
REAR_IN1 = 29
REAR_IN2 = 31
REAR_IN3 = 33
REAR_IN4 = 35

motor_pins = [
    FRONT_IN1,
    FRONT_IN2,
    FRONT_IN3,
    FRONT_IN4,
    REAR_IN1,
    REAR_IN2,
    REAR_IN3,
    REAR_IN4
]

# 모든 핀을 출력으로 설정
for pin in motor_pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


# -----------------------------
# 전진 함수
# -----------------------------

def forward():

    # 앞바퀴
    GPIO.output(FRONT_IN1, GPIO.HIGH)
    GPIO.output(FRONT_IN2, GPIO.LOW)

    GPIO.output(FRONT_IN3, GPIO.HIGH)
    GPIO.output(FRONT_IN4, GPIO.LOW)

    # 뒷바퀴
    GPIO.output(REAR_IN1, GPIO.HIGH)
    GPIO.output(REAR_IN2, GPIO.LOW)

    GPIO.output(REAR_IN3, GPIO.HIGH)
    GPIO.output(REAR_IN4, GPIO.LOW)


# -----------------------------
# 정지 함수
# -----------------------------

def stop():

    for pin in motor_pins:
        GPIO.output(pin, GPIO.LOW)


# -----------------------------
# 자동차 실행
# -----------------------------

try:

    print("자동차 출발")

    forward()

    # 전진 시간
    # 이 값을 실험하면서 조정
    MOVE_TIME = 2.0

    time.sleep(MOVE_TIME)

    stop()

    print("자동차 정지")

finally:

    stop()
    GPIO.cleanup()