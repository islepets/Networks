import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import base64
import os
import struct
import math

MASK32 = 0xFFFFFFFF
MASK64 = 0xFFFFFFFFFFFFFFFF

sTable = bytes([
    0xa3,0xd7,0x09,0x83,0xf8,0x48,0xf6,0xf4,0xb3,0x21,0x15,0x78,0x99,0xb1,0xaf,0xf9,
    0xe7,0x2d,0x4d,0x8a,0xce,0x4c,0xca,0x2e,0x52,0x95,0xd9,0x1e,0x4e,0x38,0x44,0x28,
    0x0a,0xdf,0x02,0xa0,0x17,0xf1,0x60,0x68,0x12,0xb7,0x7a,0xc3,0xe9,0xfa,0x3d,0x53,
    0x96,0x84,0x6b,0xba,0xf2,0x63,0x9a,0x19,0x7c,0xae,0xe5,0xf5,0xf7,0x16,0x6a,0xa2,
    0x39,0xb6,0x7b,0x0f,0xc1,0x93,0x81,0x1b,0xee,0xb4,0x1a,0xea,0xd0,0x91,0x2f,0xb8,
    0x55,0xb9,0xda,0x85,0x3f,0x41,0xbf,0xe0,0x5a,0x58,0x80,0x5f,0x66,0x0b,0xd8,0x90,
    0x35,0xd5,0xc0,0xa7,0x33,0x06,0x65,0x69,0x45,0x00,0x94,0x56,0x6d,0x98,0x9b,0x76,
    0x97,0xfc,0xb2,0xc2,0xb0,0xfe,0xdb,0x20,0xe1,0xeb,0xd6,0xe4,0xdd,0x47,0x4a,0x1d,
    0x42,0xed,0x9e,0x6e,0x49,0x3c,0xcd,0x43,0x27,0xd2,0x07,0xd4,0xde,0xc7,0x67,0x18,
    0x89,0xcb,0x30,0x1f,0x8d,0xc6,0x8f,0xaa,0xc8,0x74,0xdc,0xc9,0x5d,0x5c,0x31,0xa4,
    0x70,0x88,0x61,0x2c,0x9f,0x0d,0x2b,0x87,0x50,0x82,0x54,0x64,0x26,0x7d,0x03,0x40,
    0x34,0x4b,0x1c,0x73,0xd1,0xc4,0xfd,0x3b,0xcc,0xfb,0x7f,0xab,0xe6,0x3e,0x5b,0xa5,
    0xad,0x04,0x23,0x9c,0x14,0x51,0x22,0xf0,0x29,0x79,0x71,0x7e,0xff,0x8c,0x0e,0xe2,
    0x0c,0xef,0xbc,0x72,0x75,0x6f,0x37,0xa1,0xec,0xd3,0x8e,0x62,0x8b,0x86,0x10,0xe8,
    0x08,0x77,0x11,0xbe,0x92,0x4f,0x24,0xc5,0x32,0x36,0x9d,0xcf,0xf3,0xa6,0xbb,0xac,
    0x5e,0x6c,0xa9,0x13,0x57,0x25,0xb5,0xe3,0xbd,0xa8,0x3a,0x01,0x05,0x59,0x2a,0x46
])

def _lrot14(x):
    return ((x << 14) | (x >> 18)) & MASK32

def _rrot14(x):
    return ((x << 18) | (x >> 14)) & MASK32

def _lfsr(x0, x1, x2, x3, x4, sr):
    b = ((sr >> x0) ^ (sr >> x1) ^ (sr >> x2) ^ (sr >> x3) ^ (sr >> x4) ^ sr) & 1
    sr = ((b << 31) | (sr >> 1)) & MASK64
    return sr & 1, sr

def stop_and_go(n, seed):
    s1 = (seed + 0x1111111) & MASK64
    s2 = (seed + 0x2222222) & MASK64
    s3 = (seed + 0x3333333) & MASK64
    s1 = ((((s1 << 13) & MASK64) ^ (s1 >> 19)) ^ seed) & MASK64
    s2 = ((((s2 << 17) & MASK64) ^ (s2 >> 15)) ^ seed) & MASK64
    s3 = ((((s3 << 19) & MASK64) ^ (s3 >> 13)) ^ seed) & MASK64

    b1, s1 = _lfsr(31, 7, 9, 1, 0, s1)
    b2, s2 = _lfsr(31, 27, 9, 21, 0, s2)
    b3, s3 = _lfsr(31, 8, 19, 10, 3, s3)
    prev = b1

    out = []
    for _ in range(n):
        b1, s1 = _lfsr(31, 7, 9, 1, 0, s1)
        if prev == 1:
            b2, s2 = _lfsr(31, 27, 9, 21, 0, s2)
        b3, s3 = _lfsr(31, 8, 19, 10, 3, s3)
        out.append('1' if (b2 ^ b3) else '0')
        prev = b1
    return ''.join(out)

def mahash8v64(data: bytes) -> int:
    n = len(data)
    h1 = n & MASK32
    h2 = n & MASK32
    for i, byte in enumerate(data):
        t = sTable[(byte + i) & 255]
        h1 = (h1 + t) & MASK32
        h1 = (h1 + (((h1 << 6) & MASK32) ^ (h1 >> 11))) & MASK32
        h1 = _lrot14(h1)
        h2 = (h2 + t) & MASK32
        h2 = (h2 + (((h2 << 6) & MASK32) ^ (h2 >> 11))) & MASK32
        h2 = _rrot14(h2)
        sh1, sh2 = h1, h2
        h1 = ((sh1 >> 16) & 0xFFFF) | ((sh2 & 0xFFFF) << 16)
        h2 = ((sh2 >> 16) & 0xFFFF) | ((sh1 & 0xFFFF) << 16)
    return ((h2 & MASK32) << 32) | (h1 & MASK32)

def roud(x):
    return int(x + 0.5) if x >= 0 else int(x - 0.5)


class MatrixShifr:
    def __init__(self):
        self.input_string = b''
        self.input_blocks = []
        self.enc = [[0.0] * 7 for _ in range(7)]
        self.dec = [[0.0] * 7 for _ in range(7)]
        self.shifr = 0
        self.posl = ''
        self.blocks_int = []
        self.iv = [0] * 7
        self.result = []

    def _det(self, m, n):
        if n == 1:
            return m[0][0]
        if n == 2:
            return m[0][0] * m[1][1] - m[0][1] * m[1][0]
        d = 0.0
        for k in range(n):
            sub = [[m[i][j] for j in range(n) if j != k] for i in range(1, n)]
            sign = 1.0 if k % 2 == 0 else -1.0
            d += sign * m[0][k] * self._det(sub, n - 1)
        return d

    def _inverse(self):
        det = self._det(self.enc, 7)
        cof = [[0.0] * 7 for _ in range(7)]
        for i in range(7):
            for j in range(7):
                minor = [[self.enc[r][c] for c in range(7) if c != j]
                         for r in range(7) if r != i]
                md = self._det(minor, 6)
                sign = 1.0 if (i + j) % 2 == 0 else -1.0
                cof[i][j] = sign * md
        for i in range(7):
            for j in range(7):
                self.dec[i][j] = cof[j][i] / det

    def set_shifr(self, h):
        self.shifr = h

    def gen_posl(self):
        self.posl = stop_and_go(392, self.shifr)

    def gen_matrix(self):
        bitpos = 0
        for i in range(7):
            for j in range(7):
                v = 0
                for _ in range(8):
                    if bitpos < len(self.posl):
                        v = (v << 1) | int(self.posl[bitpos])
                        bitpos += 1
                self.enc[i][j] = float(v % 256)
        self._inverse()

    def set_raw_data(self, data: bytes):
        self.input_string = data
        self.input_blocks = []
        for i in range(0, len(data), 7):
            chunk = data[i:i + 7]
            if len(chunk) < 7:
                chunk = chunk + b'\x00' * (7 - len(chunk))
            self.input_blocks.append(chunk)
        self.blocks_int = [list(b) for b in self.input_blocks]

    def _gen_iv(self):
        rnd = stop_and_go(56, self.shifr)
        for i in range(7):
            v = 0
            for j in range(8):
                bp = i * 8 + j
                if bp < len(rnd):
                    v = (v << 1) | int(rnd[bp])
            self.iv[i] = v

    def _enc_gamma(self, gamma):
        res = [0] * 7
        for i in range(7):
            s = 0.0
            for j in range(7):
                s += self.enc[i][j] * gamma[j]
            v = roud(s) % 256
            if v < 0:
                v += 256
            res[i] = v
        return res

    def ofb(self):
        self.result = [[0] * 7 for _ in range(len(self.blocks_int))]
        self._gen_iv()
        gamma = list(self.iv)
        for idx in range(len(self.blocks_int)):
            gb = self._enc_gamma(gamma)
            for j in range(7):
                self.result[idx][j] = self.blocks_int[idx][j] ^ gb[j]
            gamma = gb

    def raw_bytes(self) -> bytes:
        out = bytearray()
        for block in self.result:
            for v in block:
                out.append(v & 0xFF)
        return bytes(out)


def crypt_data(data: bytes, password: bytes, encrypt: bool) -> bytes:
    if encrypt:
        payload = struct.pack('<I', len(data)) + data
        while len(payload) % 7 != 0:
            payload += b'\x00'
        nonce = os.urandom(8)
        h = mahash8v64(nonce + password)
        ms = MatrixShifr()
        ms.set_shifr(h)
        ms.gen_posl()
        ms.gen_matrix()
        ms.set_raw_data(payload)
        ms.ofb()
        return nonce + ms.raw_bytes()

    if len(data) < 8:
        return b''
    nonce = data[:8]
    cipher = data[8:]
    while len(cipher) % 7 != 0:
        cipher += b'\x00'
    h = mahash8v64(nonce + password)
    ms = MatrixShifr()
    ms.set_shifr(h)
    ms.gen_posl()
    ms.gen_matrix()
    ms.set_raw_data(cipher)
    ms.ofb()
    plain = ms.raw_bytes()
    if len(plain) < 4:
        return b''
    length = struct.unpack('<I', plain[:4])[0]
    if length > len(plain) - 4:
        length = len(plain) - 4
    return plain[4:4 + length]


def process_command(line: str):
    line = line.strip()
    if not line:
        return "", False
    parts = line.split()
    cmd = parts[0].lower()

    if cmd == "hello":
        if len(parts) < 2:
            return "error: usage: hello <variant>", False
        return f"hello variant {parts[1]}", False
    if cmd == "bye":
        if len(parts) < 2:
            return "error: usage: bye <variant>", False
        return f"bye variant {parts[1]}", True
    if cmd == "help":
        return ("commands: hello <n> | bye <n> | "
                "encrypt <password> <base64> | decrypt <password> <base64> | "
                "encryptfile <password> <base64> | decryptfile <password> <base64>"), False
    if cmd in ("encrypt", "decrypt", "encryptfile", "decryptfile"):
        if len(parts) < 3:
            return f"error: usage: {cmd} <password> <base64>", False
        password = parts[1].encode('utf-8')
        try:
            raw = base64.b64decode(parts[2], validate=False)
        except Exception:
            return "error: bad base64", False
        try:
            if cmd in ("encrypt", "encryptfile"):
                out = crypt_data(raw, password, True)
            else:
                out = crypt_data(raw, password, False)
            return "OK " + base64.b64encode(out).decode('ascii'), False
        except Exception as e:
            return f"error: {e}", False
    return f"error: unknown command '{parts[0]}'", False


class ServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Сервер")
        self.server_socket = None
        self.running = False
        self.clients = []
        self.lock = threading.Lock()

        top = tk.Frame(root)
        top.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(top, text="IP:").pack(side=tk.LEFT)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Combobox(top, textvariable=self.ip_var,
                     values=self._local_ips(), width=18).pack(side=tk.LEFT, padx=2)

        tk.Label(top, text="Порт:").pack(side=tk.LEFT, padx=(10, 0))
        self.port_var = tk.StringVar(value="8080")
        tk.Entry(top, textvariable=self.port_var, width=8).pack(side=tk.LEFT, padx=2)

        self.btn_start = tk.Button(top, text="Запуск", command=self.start_server)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        self.btn_stop = tk.Button(top, text="Стоп", command=self.stop_server, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        tk.Button(top, text="Очистить", command=self._clear_log).pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Остановлен")
        self.status_label = tk.Label(root, textvariable=self.status_var,
                                     fg="red", font=("Arial", 10, "bold"))
        self.status_label.pack(anchor=tk.W, padx=5)

        self.log = scrolledtext.ScrolledText(root, height=25, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _local_ips(self):
        ips = ["127.0.0.1"]
        try:
            for info in socket.getaddrinfo(socket.gethostname(), None):
                ip = info[4][0]
                if ':' not in ip and ip not in ips:
                    ips.append(ip)
        except Exception:
            pass
        return ips

    def _log(self, msg):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def _clear_log(self):
        self.log.config(state=tk.NORMAL)
        self.log.delete(1.0, tk.END)
        self.log.config(state=tk.DISABLED)

    def start_server(self):
        try:
            port = int(self.port_var.get())
            if not 1 <= port <= 65535:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Порт должен быть в диапазоне 1..65535")
            return

        ip = self.ip_var.get()
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((ip, port))
            self.server_socket.listen(50)
        except OSError as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить сервер:\n{e}")
            return

        self.running = True
        self.status_var.set("Запущен")
        self.status_label.config(fg="green")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self._log(f"=== Запуск сервера {ip}:{port} ===")
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
            except OSError:
                break
            with self.lock:
                self.clients.append(conn)
            self.root.after(0, self._log, f"[+] подключён {addr[0]}:{addr[1]}")
            threading.Thread(target=self._client_loop,
                             args=(conn, addr), daemon=True).start()

    def _client_loop(self, conn, addr):
        who = f"{addr[0]}:{addr[1]}"
        buf = b''
        try:
            while self.running:
                data = conn.recv(4096)
                if not data:
                    break
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    if line.endswith(b'\r'):
                        line = line[:-1]
                    if not line:
                        continue
                    text = line.decode('utf-8', errors='replace')
                    self.root.after(0, self._log, f"[<<] {who}: {text}")
                    try:
                        resp, close = process_command(text)
                    except Exception as e:
                        resp, close = f"error: {e}", False
                    if resp:
                        self.root.after(0, self._log, f"[>>] {who}: {resp}")
                        try:
                            conn.sendall((resp + "\n").encode('utf-8'))
                        except OSError:
                            pass
                    if close:
                        return
        except OSError:
            pass
        finally:
            with self.lock:
                if conn in self.clients:
                    self.clients.remove(conn)
            try:
                conn.close()
            except OSError:
                pass
            self.root.after(0, self._log, f"[-] отключён {who}")

    def stop_server(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None
        with self.lock:
            for c in self.clients:
                try:
                    c.shutdown(socket.SHUT_RDWR)
                    c.close()
                except OSError:
                    pass
            self.clients.clear()
        self.status_var.set("Остановлен")
        self.status_label.config(fg="red")
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self._log("=== Остановка сервера ===")

    def _on_close(self):
        self.stop_server()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x600")
    ServerApp(root)
    root.mainloop()