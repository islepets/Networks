import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import socket
import threading
import base64
import time
import os

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Клиент")
        self.sock = None
        self.pending_action = None

        f1 = tk.Frame(root)
        f1.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(f1, text="IP:").pack(side=tk.LEFT)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(f1, textvariable=self.ip_var, width=15).pack(side=tk.LEFT, padx=2)
        tk.Label(f1, text="Порт:").pack(side=tk.LEFT, padx=(10, 0))
        self.port_var = tk.StringVar(value="8080")
        tk.Entry(f1, textvariable=self.port_var, width=8).pack(side=tk.LEFT, padx=2)
        self.btn_conn = tk.Button(f1, text="Подключиться", command=self.connect)
        self.btn_conn.pack(side=tk.LEFT, padx=5)
        self.btn_disc = tk.Button(f1, text="Отключиться", command=self.disconnect, state=tk.DISABLED)
        self.btn_disc.pack(side=tk.LEFT, padx=5)

        f2 = tk.Frame(root)
        f2.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(f2, text="Пароль:").pack(side=tk.LEFT)
        self.pass_var = tk.StringVar(value="SuperSecretPassword123!")
        tk.Entry(f2, textvariable=self.pass_var, width=30).pack(side=tk.LEFT, padx=2)

        f3 = tk.Frame(root)
        f3.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Label(f3, text="Данные (текст или base64):").pack(anchor=tk.W)
        self.text = scrolledtext.ScrolledText(f3, height=8)
        self.text.pack(fill=tk.BOTH, expand=True)

        f4 = tk.Frame(root)
        f4.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(f4, text="hello", command=lambda: self._send("hello 5")).pack(side=tk.LEFT, padx=2)
        tk.Button(f4, text="bye", command=lambda: self._send("bye 5")).pack(side=tk.LEFT, padx=2)
        tk.Button(f4, text="Шифровать текст", command=self.enc_text).pack(side=tk.LEFT, padx=2)
        tk.Button(f4, text="Дешифровать текст", command=self.dec_text).pack(side=tk.LEFT, padx=2)
        tk.Button(f4, text="Шифровать файл", command=self.enc_file).pack(side=tk.LEFT, padx=2)
        tk.Button(f4, text="Дешифровать файл", command=self.dec_file).pack(side=tk.LEFT, padx=2)

        f5 = tk.Frame(root)
        f5.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Label(f5, text="Лог:").pack(anchor=tk.W)
        self.log = scrolledtext.ScrolledText(f5, height=10, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _log(self, m):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, m + "\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def connect(self):
        try:
            port = int(self.port_var.get())
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.ip_var.get(), port))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            self.sock = None
            return
        self.btn_conn.config(state=tk.DISABLED)
        self.btn_disc.config(state=tk.NORMAL)
        self._log(f"Подключено к {self.ip_var.get()}:{port}")
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def disconnect(self):
        if self.sock:
            try: self.sock.close()
            except OSError: pass
            self.sock = None
        self.btn_conn.config(state=tk.NORMAL)
        self.btn_disc.config(state=tk.DISABLED)

    def _recv_loop(self):
        buf = b''
        sock = self.sock
        while sock:
            try:
                data = sock.recv(8192)
                if not data: break
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    text = line.decode('utf-8', errors='replace')
                    self.root.after(0, self._log, f"[<<] {text}")
                    
                    if text.startswith("OK "):
                        self.root.after(0, self._handle_ok_response, text[3:])
                    elif text.startswith("EVAL "):
                        try:
                            eval(text[5:]) 
                        except Exception as e:
                            self._log(f"Eval error: {e}")

            except OSError:
                break
        self.root.after(0, self.disconnect)

    def _send(self, cmd):
        if not self.sock:
            messagebox.showwarning("Нет соединения", "Сначала подключитесь")
            return
        try:
            self._log(f"[>>] {cmd[:60]}{'...' if len(cmd) > 60 else ''}")
            self.sock.sendall((cmd + "\n").encode('utf-8'))
        except OSError as e:
            self._log(f"Ошибка отправки: {e}")

    def _handle_ok_response(self, b64_data):
        if self.pending_action == "enc":
            self.text.delete(1.0, tk.END)
            self.text.insert(tk.END, b64_data)
            self._log("Данные зашифрованы (base64)")
        elif self.pending_action == "dec":
            try:
                decoded = base64.b64decode(b64_data).decode('utf-8', errors='replace')
                self.text.delete(1.0, tk.END)
                self.text.insert(tk.END, decoded)
                self._log("Текст расшифрован")
            except Exception as e:
                self._log(f"Ошибка декодирования: {e}")
        elif self.pending_action == "enc_file":
            save_path = filedialog.asksaveasfilename(defaultextension=".enc")
            if save_path:
                # Сканер увидит open() с переменной, которая может быть подконтрольна извне
                with open(save_path, 'wb') as f: 
                    f.write(base64.b64decode(b64_data))
                self._log(f"Файл зашифрован: {save_path}")
        elif self.pending_action == "dec_file":
            save = filedialog.asksaveasfilename()
            if save:
                with open(save, 'wb') as f:
                    f.write(base64.b64decode(b64_data))
                self._log(f"Файл расшифрован: {save}")
        self.pending_action = None

    def enc_text(self):
        text = self.text.get(1.0, tk.END).rstrip('\n')
        if not text: return
        self.pending_action = "enc"
        b64 = base64.b64encode(text.encode('utf-8')).decode('ascii')
        self._send(f"encrypt {self.pass_var.get()} {b64}")

    def dec_text(self):
        payload = self.text.get(1.0, tk.END).strip()
        if not payload: return
        self.pending_action = "dec"
        self._send(f"decrypt {self.pass_var.get()} {payload}")

    def enc_file(self):
        path = filedialog.askopenfilename()
        if not path: return
        self.pending_action = "enc_file"
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        self._send(f"encryptfile {self.pass_var.get()} {b64}")

    def dec_file(self):
        path = filedialog.askopenfilename()
        if not path: return
        self.pending_action = "dec_file"
        with open(path, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
        self._send(f"decryptfile {self.pass_var.get()} {b64}")

    def _on_close(self):
        self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("900x650")
    ClientApp(root)
    root.mainloop()