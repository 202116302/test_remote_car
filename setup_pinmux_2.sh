#!/bin/bash
# Jetson Orin Nano (JetPack 6) 모터용 핀 8개를 GPIO 출력으로 설정
# 레지스터 주소 출처: NVIDIA Jetson.GPIO gpio_pin_data.py (JETSON_ORIN_NX_PIN_DEFS)
# 재부팅하면 초기화되므로, 부팅 후 모터 코드 실행 전에 한 번씩 실행
#   chmod +x setup_pinmux.sh
#   sudo ./setup_pinmux.sh

if [ "$EUID" -ne 0 ]; then
  echo "sudo로 실행하세요: sudo ./setup_pinmux.sh"; exit 1
fi
if ! command -v busybox >/dev/null; then
  echo "busybox가 없습니다: sudo apt install busybox"; exit 1
fi

declare -A REG=(
  [11]=0x02430098 [13]=0x0243D030 [15]=0x02440020 [16]=0x0243D020
  [29]=0x02430068 [31]=0x02430070 [33]=0x02434040 [35]=0x024340A0
  [7]=0x02448030  [18]=0x0243D010
)
OUT_PINS="11 13 15 16 29 31 33 35 7"   # 모터 8개 + 초음파 TRIG
IN_PINS="18"                           # 초음파 ECHO

# bit10: 1=SFIO(UART/SPI 등), 0=GPIO
# bit6 : 1=입력, 0=출력
# bit4 : 1=tristate(출력 끊김), 0=연결
SFIO=$(( 1<<10 )); INOUT=$(( (1<<6) | (1<<4) ))

set_pin() {  # $1=핀, $2=out|in
  addr=${REG[$1]}
  old=$(busybox devmem "$addr")
  if [ "$2" = out ]; then v=$(( old & ~(SFIO | INOUT) ))
  else                    v=$(( (old & ~SFIO) | INOUT )); fi
  busybox devmem "$addr" w "$(printf "0x%08X" $v)"
  printf "pin %2s (%-3s) %s : %s -> %s\n" "$1" "$2" "$addr" "$old" "$(busybox devmem "$addr")"
}

for pin in $OUT_PINS; do set_pin "$pin" out; done
for pin in $IN_PINS;  do set_pin "$pin" in;  done

echo "완료. 이제 실행: sudo python3 motor_control.py test"
