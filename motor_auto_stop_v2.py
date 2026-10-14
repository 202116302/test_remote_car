#!/usr/bin/env python3
"""
초음파 센서(HC-SR04P) 자동 정지 v2 - 좌우 회전 개선
motor_control.py와 같은 폴더에 두고 실행 (모터 핀/방향 반전 설정을 그대로 사용)

v2 변경점
  - 회전 방식 선택 (TURN_MODE: spin / pivot)
  - 회전키: 누르고 있는 동안만 회전, 떼면 자동 정지 (TURN_TIME)
  - 방향 전환 시 잠깐 정지 후 전환 (모터 전류 급증 방지)
  - 회전 중에는 거리 측정을 건너뛰어 회전 반응 속도 개선

센서 배선 (BOARD 물리핀)
  VCC  -> 1번 (3.3V)
  GND  -> 6번 (GND)
  TRIG -> 7번
  ECHO -> 18번

실행
  sudo ./setup_pinmux.sh                       # 부팅할 때마다
  sudo python3 motor_auto_stop_v2.py sensor    # 거리만 출력 (센서 확인용)
  sudo python3 motor_auto_stop_v2.py           # 키보드 주행 + 자동 정지
"""
import sys
import time
import termios
import tty

import Jetson.GPIO as GPIO

from motor_control import Car, get_key

TRIG = 7
ECHO = 18
STOP_CM = 16      # 이 거리(cm) 안에 물체가 있으면 전진 정지
TIMEOUT = 0.03    # 에코 대기 최대 시간(초)

# ---- 회전 설정 (v2) ----
TURN_MODE = "spin"   # "spin" : 제자리 회전 (왼쪽/오른쪽 바퀴를 반대 방향으로)
                     # "pivot": 한쪽 바퀴만 앞으로 (반대쪽 정지) - 크게 돌며 회전
TURN_TIME = 0.5      # 회전키를 뗀 뒤 이 시간(초)이 지나면 자동 정지 (0이면 스페이스 누를 때까지 계속 회전)
SWITCH_PAUSE = 0.05  # 방향을 바꿀 때 잠깐 멈추는 시간(초)


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
    if TURN_MODE == "pivot":
        turn_left = lambda: car._set(0, 1)    # 오른쪽 바퀴만 전진
        turn_right = lambda: car._set(1, 0)   # 왼쪽 바퀴만 전진
    else:
        turn_left, turn_right = car.turn_left, car.turn_right

    actions = {
        "forward": car.forward, "backward": car.backward,
        "left": turn_left, "right": turn_right, "stop": car.stop,
    }
    keymap = {
        "w": "forward", "\x1b[A": "forward",
        "s": "backward", "\x1b[B": "backward",
        "a": "left", "\x1b[D": "left",
        "d": "right", "\x1b[C": "right",
        " ": "stop",
    }
    print(f"방향키/WASD: 이동 | 스페이스: 정지 | Q: 종료 | {STOP_CM}cm 이내 물체 감지 시 전진 정지")
    print(f"회전 방식: {TURN_MODE} | 회전키는 누르고 있는 동안만 회전")

    state, applied = "stop", None
    turn_until = 0.0
    d = None
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
                if state in ("left", "right"):
                    turn_until = time.time() + TURN_TIME   # 키가 반복 입력되는 동안 계속 연장

            turning = state in ("left", "right")
            if turning and TURN_TIME > 0 and time.time() > turn_until:
                state, turning = "stop", False             # 회전키를 떼면 자동 정지

            if not turning:                                # 회전 중엔 측정 생략 (반응 속도)
                d = measure_cm()
            blocked = d is not None and d < STOP_CM
            if state == "forward" and blocked:
                state = "stop"                             # 전진만 막고 후진/회전은 허용

            if state != applied:                           # 상태가 바뀔 때만 모터 명령
                if applied not in (None, "stop") and state != "stop":
                    car.stop()
                    time.sleep(SWITCH_PAUSE)
                actions[state]()
                applied = state

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
