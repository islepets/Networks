import sys, shutil
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QHBoxLayout, QLabel, QCheckBox, QLineEdit, QGridLayout, \
                            QPushButton, QVBoxLayout, QTextEdit, QMessageBox
from PyQt6.QtCore import QSize, QProcess

class ToolBar(QWidget):
    command = ""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc = None
        self._buffer = b""
        self._build_ui()    

    def _build_ui(self):
        raise NotImplementedError

    def _read_output(self, proc, output):
        data = proc.readAllStandardOutput().data()
        self._buffer += data

        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            line = line.rstrip(b"\r")
            output.insertPlainText(line.decode("cp866", errors="replace") + "\n")

    def _flush_buffer(self, output):
        if self._buffer:
            text = self._buffer.decode("cp866", errors="replace")
            output.insertPlainText(text.rstrip("\r") + "\n")
            self._buffer = b""

    def _run(self, command, fields, output):
        raise NotImplementedError