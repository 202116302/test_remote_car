#!/usr/bin/env python3
"""
Jetson Orin Nano + L298N x2 4륜 모터 제어

배선 (BOARD 물리핀 번호)
  앞 드라이버: IN1=11, IN2=13 (OUT1/2, 왼쪽 앞)  IN3=15, IN4=16 (OUT3/4, 오른쪽 앞)
  뒤 드라이버: IN1=29, IN2=31 (OUT1/2, 왼쪽 뒤)  IN3=33, IN4=35 (OUT3/4, 오른쪽 뒤)
  ENA/ENB 점퍼 장착 상태 -> 속도 고정, on/off/방향만 제어
  Jetson GND <-> 브레드보드 GND <-> 배터리(-) 공통 연결 필수

실행
  sudo python3 motor_control.py test    # 모터 하나씩 + 전후좌우 자동 테스트
  sudo python3 motor_control.py drive   # 키보드 조작 (기본값)
"""
import os
import sys
import time
import select
import termios
import tty

import Jetson.GPIO as GPIO

# 이름: (IN_a 핀, IN_b 핀, 방향 반전)
# 테스트에서 바퀴가 반대로 돌면 해당 모터만 True로 바꾸면 됨 (전선 다시 안 끼워도 됨)
MOTORS = {
    "FL": (11, 13, False),  # 앞-왼쪽  (앞 드라이버 OUT1/OUT2)
    "FR": (15, 16, False),  # 앞-오른쪽 (앞 드라이버 OUT3/OUT4)
    "RL": (29, 31, False),  # 뒤-왼쪽  (뒤 드라이버 OUT1/OUT2)
    "RR": (33, 35, False),  # 뒤-오른쪽 (뒤 드라이버 OUT3/OUT4)
}


class Motor:
    def __init__(self, name, in_a, in_b, invert=False):
        self.name = name
        self.in_a = in_a
        self.in_b = in_b
        self.invert = invert
        GPIO.setup([in_a, in_b], GPIO.OUT, initial=GPIO.LOW)

    def run(self, direction):
        """direction: 1=정회전, -1=역회전, 0=정지"""
        if self.invert:
            direction = -direction
        GPIO.output(self.in_a, GPIO.HIGH if direction > 0 else GPIO.LOW)
        GPIO.output(self.in_b, GPIO.HIGH if direction < 0 else GPIO.LOW)


class Car:
    def __init__(self):
        self.motors = {name: Motor(name, *cfg) for name, cfg in MOTORS.items()}

    def _set(self, left, right):
        self.motors["FL"].run(left)
        self.motors["RL"].run(left)
        self.motors["FR"].run(right)
        self.motors["RR"].run(right)

    def forward(self):
        self._set(1, 1)

    def backward(self):
        self._set(-1, -1)

    def turn_left(self):   # 제자리 좌회전 (왼쪽 뒤로, 오른쪽 앞으로)
        self._set(-1, 1)

    def turn_right(self):  # 제자리 우회전
        self._set(1, -1)

    def stop(self):
        self._set(0, 0)


def test(car):
    print("[1] 모터 개별 테스트 - 각 바퀴가 '앞으로' 도는지 확인")
    for name, motor in car.motors.items():
        print(f"  {name} 정회전 1초")
        motor.run(1)
        time.sleep(1)
        motor.run(0)
        time.sleep(0.5)

    print("[2] 주행 테스트")
    for label, action in [("전진", car.forward), ("후진", car.backward),
                          ("좌회전", car.turn_left), ("우회전", car.turn_right)]:
        print(f"  {label} 1초")
        action()
        time.sleep(1)
        car.stop()
        time.sleep(0.5)
    print("테스트 완료")


def get_key(fd, timeout=0.1):
    r, _, _ = select.select([fd], [], [], timeout)
    if not r:
        return None
    data = os.read(fd, 3).decode(errors="ignore")
    if data.startswith("\x1b["):
        return data[:3]          # 방향키
    return data[-1].lower() if data else None


def drive(car):
    keymap = {
        "w": car.forward,    "\x1b[A": car.forward,
        "s": car.backward,   "\x1b[B": car.backward,
        "a": car.turn_left,  "\x1b[D": car.turn_left,
        "d": car.turn_right, "\x1b[C": car.turn_right,
        " ": car.stop,
    }
    print("방향키 또는 W/A/S/D: 이동 | 스페이스: 정지 | Q: 종료")

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            key = get_key(fd)
            if key is None:
                continue
            if key == "q":
                break
            if key in keymap:
                keymap[key]()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "drive"
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    car = Car()
    try:
        if mode == "test":
            test(car)
        else:
            drive(car)
    except KeyboardInterrupt:
        pass
    finally:
        car.stop()
        GPIO.cleanup()
        print("\nGPIO 정리 완료")


if __name__ == "__main__":
    main()
