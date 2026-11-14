import sys, shutil, re
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QHBoxLayout, QLabel, QCheckBox, QLineEdit, QGridLayout, \
                            QPushButton, QVBoxLayout, QTextEdit, QMessageBox, QTableWidget, QHeaderView, QTableWidgetItem, QPlainTextEdit
from PyQt6.QtCore import QSize, QProcess

from ToolBar import ToolBar


class Ping(ToolBar):
    command = "ping"

    _resp_re = re.compile(
        r"Ответ от (.+?):\s*число байт=(\d+)\s*время[=<](.+?)мс\s*TTL=(\d+)"
    )

    def _build_ui(self):

        options = [("/t", "flag", None),
                       ("/a", "flag", None),
                       ("/n", "value", "4"),
                       ("/l", "value", "64"),
                       ("/f", "flag", None),
                        ("/i", "value", "255"),
                        ("/r", "value", "5"),
                        ("/w", "value", "1000"),
                        ("КонечноеИмя", "host", None)]

        fields = {}

        vertical = QVBoxLayout()
        grid = QGridLayout()
        for col, (label, kind, default) in enumerate(options):
            grid.addWidget(QLabel(label), 0, col)
            if kind == "flag":
                cb = QCheckBox()
                grid.addWidget(cb, 1, col)
                fields[label] = ("flag", cb, None)
            elif kind == "value":
                cell = QWidget()
                h = QHBoxLayout(cell)
                cb = QCheckBox()
                le = QLineEdit()
                if default is not None:
                    le.setText(default)
                le.setEnabled(False)
                cb.toggled.connect(le.setEnabled)
                h.addWidget(cb)
                h.addWidget(le)
                grid.addWidget(cell, 1, col)
                fields[label] = ("value", cb, le)
            elif kind == "host":
                le = QLineEdit()
                grid.addWidget(le, 1, col)
                fields[label] = ("host", None, le)

        grid.setRowStretch(2, 1)
        vertical.addLayout(grid)

        btn = QPushButton("Запуск")
        vertical.addWidget(btn)

        self.output = QTableWidget(0, 7)
        self.output.setHorizontalHeaderLabels(
            ["№", "Тип", "Адрес", "Байты", "Время", "TTL", "Сообщение"])
        self.output.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.output.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.output.setAlternatingRowColors(True)
        self.output.verticalHeader().setVisible(False)

        header = self.output.horizontalHeader()
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        vertical.addWidget(self.output, 3)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(110)
        vertical.addWidget(self.log, 1)

        self.setLayout(vertical)
        btn.clicked.connect(lambda: self._run(self.command, fields, self.output))

    def _parse_line(self, line: str):
        line = line.strip()
        if not line:
            return None

        m = re.search(r"Обмен пакетами с (.+?)\s*\[([\d.]+)\]", line)
        if m:
            self._target = f"{m.group(1)} [{m.group(2)}]"
            return None

        m = self._resp_re.search(line)
        if m:
            return ("Ответ", m.group(1).strip(), m.group(2),
                    m.group(3) + " мс", m.group(4), "")

        if "Превышен интервал" in line:
            return ("Таймаут", self._target or "", "", "", "", line)

        low = line.lower()
        if ("не найден" in low or "не удалось" in low
                or "недоступен" in low or "общий сбой" in low):
            return ("Ошибка", self._target or "", "", "", "", line)

        return None

    def _add_line(self, text: str):
        parsed = self._parse_line(text)
        if not parsed:
            if text.strip():
                self.log.appendPlainText(text)
            return
        row = self.output.rowCount()
        self.output.insertRow(row)
        values = [str(self._counter)] + list(parsed)
        self._counter += 1
        for col, val in enumerate(values):
            self.output.setItem(row, col, QTableWidgetItem(val))

    def _read_output(self, proc, output):
        self._buffer += proc.readAllStandardOutput().data()
        while b"\n" in self._buffer:
            raw, self._buffer = self._buffer.split(b"\n", 1)
            self._add_line(raw.rstrip(b"\r").decode("cp866", errors="replace"))

    def _flush_buffer(self, output):
        if self._buffer:
            self._add_line(self._buffer.decode("cp866", errors="replace").rstrip("\r"))
            self._buffer = b""

    def _run(self, command, fields, output):
        args = [command]
        for label, (kind, w, extra) in fields.items():
            if kind == "flag" and w.isChecked():
                args.append(label)
            elif kind == "value" and w.isChecked():
                args.append(label)
                val = extra.text().strip()
                if val:
                    if label == "/n" and not (1 <= int(val) <= 4294967295):
                        QMessageBox.warning(self, "Ошибка", "Неверный параметр /n"); return
                    if label == "/l" and not (0 <= int(val) <= 65500):
                        QMessageBox.warning(self, "Ошибка", "Неверный параметр /l"); return
                    if label == "/i" and not (1 <= int(val) <= 255):
                        QMessageBox.warning(self, "Ошибка", "Неверный параметр /i"); return
                    if label == "/r" and not (1 <= int(val) <= 9):
                        QMessageBox.warning(self, "Ошибка", "Неверный параметр /r"); return
                    if label == "/w" and not (1 <= int(val) <= 4294967295):
                        QMessageBox.warning(self, "Ошибка", "Неверный параметр /w"); return
                    args.append(val)
            elif kind == "host":
                val = extra.text().strip()
                if val:
                    args.append(val)
                else:
                    QMessageBox.warning(self, "Ошибка", "Неверный параметр хоста")
                    return

        self.output.setRowCount(0)
        self.log.clear()
        self._counter = 1
        self._target = ""
        self._buffer = b""

        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()
            self._proc.waitForFinished(1000)

        proc = QProcess(self)
        self._proc = proc
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        proc.readyReadStandardOutput.connect(lambda: self._read_output(proc, output))

        def on_finished(code, status):
            self._read_output(proc, output)
            self._flush_buffer(output)

        proc.finished.connect(on_finished)
        proc.errorOccurred.connect(
            lambda err: QMessageBox.warning(self, "Ошибка QProcess", str(err)))

        exe = shutil.which(command) or command
        proc.start(exe, args[1:])