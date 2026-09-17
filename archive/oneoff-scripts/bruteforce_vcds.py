#!/usr/bin/env python3
"""
Terminal Brute-force & Probe Engine for Ross-Tech HEX-USB+CAN on VW Golf 5 EDC16U34
Sweeps:
- Baud rates: 10400, 500000, 115200, 38400, 57600, 250000
- Probes: KWP2000 Fast Init, MPPS ECU ID, Ross-Tech Smart Handshake, CAN TP2.0 Broadcast
- Real-time HEX dump of all responses
"""

import sys
import time
import struct
import serial
import serial.tools.list_ports

BAUD_RATES = [10400, 500000, 115200, 38400, 57600, 250000]

PROBES = [
    # 1. KWP2000 StartCommunication (EDC16 Physical Address 0x01)
    ("KWP StartCommunication (Addr 01)", bytes([0x81, 0x01, 0xF1, 0x81, 0xF4])),
    # 2. Direct Read ECU ID (EDC16 MPPS/KWP2000 Service 0x1A 0x9B)
    ("KWP Read ECU ID (1A 9B)", bytes([0x82, 0x01, 0xF1, 0x1A, 0x9B, 0x69])),
    # 3. KWP2000 ReadDataByLocalIdentifier Group 0x80
    ("KWP ReadData ID 80", bytes([0x82, 0x01, 0xF1, 0x21, 0x80, 0x15])),
    # 4. Functional OBD2 Broadcast (Addr 0x33)
    ("OBD2 Broadcast (Addr 33)", bytes([0xC1, 0x33, 0xF1, 0x81, 0x66])),
    # 5. Ross-Tech Intelligent Mode Pings / Handshakes
    ("Ross-Tech Ping 0x55", bytes([0x55])),
    ("Ross-Tech Ping 0xAA", bytes([0xAA])),
    ("Ross-Tech Connect 0x21 0x55", bytes([0x21, 0x55])),
    ("Ross-Tech Query Version 0x22", bytes([0x22])),
    # 6. CAN TP 2.0 Setup Channel (Gateway to Engine 0x01)
    ("CAN TP2.0 Open Engine (0x200)", bytes([0x01, 0xC0, 0x00, 0x10, 0x00, 0x03, 0x01])),
    # 7. ELM327 / ASCII Reset
    ("ASCII ATZ / ATI", b"ATZ\rATI\r0100\r"),
]

def find_vcds_port():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = (p.description or "").lower()
        hw = (p.hwid or "").lower()
        if "com9" in p.device.lower() or "ross" in desc or "0403" in hw or "fa24" in hw:
            return p.device
    if ports:
        return ports[0].device
    return "COM9"

def test_baud(port_name, baud):
    print(f"\n" + "="*70)
    print(f"[*] ТЕСТУВАННЯ ШВИДКОСТІ: {baud} бод на порті {port_name}")
    print("="*70)
    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.6,
            write_timeout=1.0
        )
    except Exception as e:
        print(f"[-] Не вдалося відкрити {port_name} на {baud} бод: {e}")
        return False

    ser.dtr = True
    ser.rts = False
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # If 10400, send 25ms Fast Init Break Pulse
    if baud == 10400:
        print("[*] Надсилання Fast Init 25ms Break / Mark імпульсу...")
        ser.break_condition = True
        time.sleep(0.025)
        ser.break_condition = False
        time.sleep(0.025)

    found_response = False

    for name, packet in PROBES:
        ser.reset_input_buffer()
        print(f"  -> [TX] {name} ({len(packet)} байт): {packet.hex(' ').upper()}")
        ser.write(packet)
        time.sleep(0.08)

        # Read response
        rx = ser.read(128)
        if rx:
            # Filter out direct local echo if identical
            if rx == packet:
                print(f"     [RX-ECHO] Локальне відлуння K-Line: {rx.hex(' ').upper()}")
                # Wait a bit more for ECU reply
                rx_more = ser.read(64)
                if rx_more:
                    print(f"     [+] [RX-ВІДПОВІДЬ ЕБУ!] {rx_more.hex(' ').upper()}")
                    found_response = True
            else:
                print(f"     [+] [RX-ВІДПОВІДЬ!] {len(rx)} байт: {rx.hex(' ').upper()}")
                ascii_repr = "".join(chr(b) if 32 <= b <= 126 else "." for b in rx)
                print(f"         ASCII: {ascii_repr}")
                found_response = True
        else:
            print("     [RX] Немає відповіді (тиша)")

    ser.close()
    return found_response

def main():
    target_port = sys.argv[1] if len(sys.argv) > 1 else find_vcds_port()
    print(f"[*] VCDS/EDC16 Brute-force Probe Engine запущено.")
    print(f"[*] Цільовий порт: {target_port}")

    for baud in BAUD_RATES:
        success = test_baud(target_port, baud)
        if success:
            print(f"\n[✓✓✓] ЗНАЙДЕНО ВІДПОВІДЬ НА ШВИДКОСТІ {baud} БОД! [✓✓✓]\n")
            break
        time.sleep(0.3)

if __name__ == "__main__":
    main()
