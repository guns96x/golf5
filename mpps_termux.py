import socket
import sys
import time

class MppsClient:
    def __init__(self, host='127.0.0.1', port=8888):
        self.host = host
        self.port = port
        self.sock = None
        self.connect()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((self.host, self.port))
        banner = self.sock.recv(1024).decode().strip()
        print(f'[*] Connected to MPPS Bridge: {banner}')

    def cmd(self, command: str) -> str:
        if not self.sock:
            self.connect()
        self.sock.sendall((command.strip() + '\n').encode('utf-8'))
        resp = self.sock.recv(4096).decode('utf-8', errors='ignore').strip()
        return resp

    def ping(self):
        return self.cmd('PING')

    def voltage(self):
        r = self.cmd('VOLTAGE')
        print(f'[+] Voltage: {r}')
        return r

    def read_ee(self, addr, length=2):
        addr_hex = f'{addr:04X}' if isinstance(addr, int) else addr
        r = self.cmd(f'READ_EE {addr_hex} {length}')
        print(f'[+] Read EE 0x{addr_hex} ({length}B): {r}')
        return r

    def write_ee(self, addr, hex_data):
        addr_hex = f'{addr:04X}' if isinstance(addr, int) else addr
        r = self.cmd(f'WRITE_EE {addr_hex} {hex_data}')
        print(f'[+] Write EE 0x{addr_hex}: {r}')
        return r

    def write_raw(self, hex_data):
        return self.cmd(f'WRITE_RAW {hex_data}')

    def write_masked(self, hex_data):
        return self.cmd(f'WRITE_MASKED {hex_data}')

    def read_raw(self, length=64, timeout=1000):
        return self.cmd(f'READ_RAW {length} {timeout}')

    def control(self, req_type, req, val=0, idx=0, length=0, hex_data=''):
        c = f'CONTROL {req_type:02X} {req:02X} {val:04X} {idx:04X} {length}'
        if hex_data:
            c += f' {hex_data}'
        return self.cmd(c)

    def set_baud(self, baud):
        return self.cmd(f'SET_BAUD {baud}')

    def set_dtr(self, state=True):
        return self.cmd(f'SET_DTR {1 if state else 0}')

    def set_rts(self, state=True):
        return self.cmd(f'SET_RTS {1 if state else 0}')

    def diag(self):
        r = self.cmd('DIAG')
        formatted = r.replace('[NL]', '\n')
        print(formatted)
        return formatted

    def fast_init(self, pulse_ms=25, hex_req='8101F181F4'):
        r = self.cmd(f'FAST_INIT {pulse_ms} {hex_req}')
        print(f'[+] Fast Init ({pulse_ms}ms, req={hex_req}): {r}')
        return r

    def can_setup(self, timing=7, tx_id=0x200):
        tx_hex = f'{tx_id:03X}' if isinstance(tx_id, int) else tx_id
        r = self.cmd(f'CAN_SETUP {timing} {tx_hex}')
        print(f'[+] CAN Setup (timing={timing}, tx={tx_hex}): {r}')
        return r

    def can_send(self, hex_data):
        return self.cmd(f'CAN_SEND {hex_data}')

    def can_recv(self, timeout=1000):
        return self.cmd(f'CAN_RECV {timeout}')

    def sweep_baud(self):
        print('[*] Sweeping baud rates with version probe 0x22...')
        for b in [10400, 38400, 57600, 115200, 9600, 500000]:
            self.set_baud(b)
            time.sleep(0.05)
            self.write_raw('22')
            r = self.read_raw(64, 200)
            print(f'  Baud {b:6d} -> raw IN: {r}')

    def bruteforce_kwp_init(self):
        print('[*] Bruteforcing KWP Init...')
        for pulse in [20, 25, 50, 100]:
            for target in ['01', '33']:
                req = f'81{target}F181'
                # compute 8-bit checksum
                b_list = bytes.fromhex(req)
                cs = sum(b_list) & 0xFF
                full_req = f'{req}{cs:02X}'
                print(f'  Trying pulse={pulse}ms req={full_req}...')
                self.fast_init(pulse, full_req)
                time.sleep(0.1)
                r = self.read_raw(64, 500)
                print(f'    Response: {r}')

if __name__ == '__main__':
    try:
        mpps = MppsClient()
        mpps.voltage()
        if len(sys.argv) > 1:
            cmd = sys.argv[1].lower()
            if cmd == 'diag':
                mpps.diag()
            elif cmd == 'sweep':
                mpps.sweep_baud()
            elif cmd == 'kwp':
                mpps.bruteforce_kwp_init()
            elif cmd == 'voltage':
                pass
        else:
            print('[*] MPPS Client ready! Use: mpps.voltage(), mpps.diag(), mpps.read_ee(0x1000), etc.')
    except Exception as e:
        print(f'[-] Error connecting to bridge: {e}')
