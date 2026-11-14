import sys, ctypes
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt6.QtCore import QSize

from Ping import Ping
from Ipconfig import Ipconfig
from Tracert import Tracert
from Arp import Arp

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    params = " ".join(f'"{arg}"' for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лабораторная работа №1 - Использование сетевых утилит ОС Windows")
        self.resize(QSize(900, 500))

        tabs = QTabWidget()
        tabs.addTab(Ping(), "ping")
        tabs.addTab(Ipconfig(), "ipconfig")
        tabs.addTab(Tracert(), "tracert")
        tabs.addTab(Arp(), "arp")

        self.setCentralWidget(tabs)

def main():
    if not is_admin():
        run_as_admin()
        sys.exit(0) 


    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()