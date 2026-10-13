#!/usr/bin/env python3
"""
초음파 센서(HC-SR04) 자동 정지 버전
motor_control.py와 같은 폴더에 두고 실행 (모터 핀/방향 반전 설정을 그대로 사용)

센서 배선 (BOARD 물리핀)
  VCC  -> 2번 (5V)
  GND  -> 6번 (GND)
  TRIG -> 7번
  ECHO -> 분압 저항(1kΩ/2kΩ) 거쳐서 18번   ※ 5V 직결 금지

실행
  sudo ./setup_pinmux.sh                    # 부팅할 때마다
  sudo python3 motor_auto_stop.py sensor    # 거리만 출력 (센서 확인용)
  sudo python3 motor_auto_stop.py           # 키보드 주행 + 자동 정지
"""
import sys
import time
import termios
import tty

import Jetson.GPIO as GPIO

from motor_control import Car, get_key

TRIG = 7
ECHO = 18
STOP_CM = 20      # 이 거리(cm) 안에 물체가 있으면 전진 정지
TIMEOUT = 0.03    # 에코 대기 최대 시간(초)


def setup_sensor():
    GPIO.setup(TRIG, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(ECHO, GPIO.IN)
    time.sleep(0.1)


def measure_once():
    GPIO.output(TRIG, GPIO.HIGH)
    time.sleep(0.00001)               # 10us 트리거 펄스
    GPIO.output(TRIG, GPIO.LOW)

    t0 = time.perf_counter()
    while GPIO.input(ECHO) == GPIO.LOW:
        if time.perf_counter() - t0 > TIMEOUT:
            return None
    start = time.perf_counter()
    while GPIO.input(ECHO) == GPIO.HIGH:
        if time.perf_counter() - start > TIMEOUT:
            return None
    return (time.perf_counter() - start) * 34300 / 2   # 음속 343m/s, 왕복이라 /2


def measure_cm(n=3):
    """3번 재서 중앙값 사용 (튀는 값 제거)"""
    vals = []
    for _ in range(n):
        d = measure_once()
        if d is not None and 2 <= d <= 400:
            vals.append(d)
        time.sleep(0.01)
    if not vals:
        return None
    vals.sort()
    return vals[len(vals) // 2]


def fmt(d):
    return f"{d:6.1f} cm" if d is not None else "  ---- cm"


def sensor_test():
    print("거리 측정 중 (Ctrl+C 종료)")
    while True:
        print(f"\r거리: {fmt(measure_cm())}   ", end="", flush=True)
        time.sleep(0.2)


def drive(car):
    actions = {
        "forward": car.forward, "backward": car.backward,
        "left": car.turn_left, "right": car.turn_right, "stop": car.stop,
    }
    keymap = {
        "w": "forward", "\x1b[A": "forward",
        "s": "backward", "\x1b[B": "backward",
        "a": "left", "\x1b[D": "left",
        "d": "right", "\x1b[C": "right",
        " ": "stop",
    }
    print(f"방향키/WASD: 이동 | 스페이스: 정지 | Q: 종료 | {STOP_CM}cm 이내 물체 감지 시 전진 정지")

    state = "stop"
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            key = get_key(fd, timeout=0.02)
            if key == "q":
                break
            if key in keymap:
                state = keymap[key]

            d = measure_cm()
            blocked = d is not None and d < STOP_CM
            if state == "forward" and blocked:
                state = "stop"            # 전진만 막고 후진/회전은 허용
            actions[state]()

            warn = "  [장애물! 전진 차단]" if blocked else "                    "
            print(f"\r상태: {state:8s} 거리: {fmt(d)}{warn}", end="", flush=True)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "drive"
    GPIO.setmode(GPIO.BOARD)
    setup_sensor()
    car = Car()
    try:
        if mode == "sensor":
            sensor_test()
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
