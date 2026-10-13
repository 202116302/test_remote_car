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
)

# bit10: 1=SFIO(UART/SPI 등), 0=GPIO
# bit6 : 1=입력, 0=출력
# bit4 : 1=tristate(끊김), 0=연결
MASK=$(( (1<<10) | (1<<6) | (1<<4) ))

for pin in 11 13 15 16 29 31 33 35; do
  addr=${REG[$pin]}
  old=$(busybox devmem "$addr")
  new=$(printf "0x%08X" $(( old & ~MASK )))
  busybox devmem "$addr" w "$new"
  printf "pin %2s  %s : %s -> %s\n" "$pin" "$addr" "$old" "$(busybox devmem "$addr")"
done

echo "완료. 이제 실행: sudo python3 motor_control.py test"
