import shutil, re
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QCheckBox, QLineEdit, QGridLayout, \
                            QPushButton, QVBoxLayout, QMessageBox, QTableWidget, QHeaderView, \
                            QTableWidgetItem, QPlainTextEdit
from PyQt6.QtCore import QProcess

from ToolBar import ToolBar


class Tracert(ToolBar):
    command = "tracert"

    _t = r"(<?\d+\s*(?:мс|ms)|\*)"
    _hop_re = re.compile(r"^\s*(\d+)\s+" + _t + r"\s+" + _t + r"\s+" + _t + r"\s+(.*)$")

    def _build_ui(self):
        options = [("-d", "flag", None),
                   ("-h", "value", "30"),
                   ("-w", "value", "1000"),
                   ("имя", "host", None)]

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

        self.output = QTableWidget(0, 5)
        self.output.setHorizontalHeaderLabels(
            ["Хоп", "Время 1", "Время 2", "Время 3", "Узел / сообщение"])
        self.output.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.output.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.output.setAlternatingRowColors(True)
        self.output.verticalHeader().setVisible(False)

        header = self.output.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

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
        m = self._hop_re.match(line)
        if not m:
            return None
        times = [re.sub(r"\s+", " ", m.group(i)) for i in (2, 3, 4)]
        return (m.group(1), *times, m.group(5).strip())

    def _add_line(self, text: str):
        parsed = self._parse_line(text)
        if not parsed:
            if text.strip():
                self.log.appendPlainText(text)
            return
        row = self.output.rowCount()
        self.output.insertRow(row)
        for col, val in enumerate(parsed):
            self.output.setItem(row, col, QTableWidgetItem(val))
        self.output.scrollToBottom()

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
        limits = {"-h": (1, 255), "-w": (1, 4294967295)}

        args = [command]
        for label, (kind, w, extra) in fields.items():
            if kind == "flag" and w.isChecked():
                args.append(label)
            elif kind == "value" and w.isChecked():
                val = extra.text().strip()
                if not val:
                    QMessageBox.warning(self, "Ошибка", f"Не задано значение параметра {label}")
                    return
                try:
                    num = int(val)
                except ValueError:
                    QMessageBox.warning(self, "Ошибка", f"Неверный параметр {label}")
                    return
                lo, hi = limits[label]
                if not (lo <= num <= hi):
                    QMessageBox.warning(self, "Ошибка", f"Неверный параметр {label}")
                    return
                args.append(label)
                args.append(str(num))
            elif kind == "host":
                val = extra.text().strip()
                if val:
                    args.append(val)
                else:
                    QMessageBox.warning(self, "Ошибка", "Неверный параметр хоста")
                    return

        self.output.setRowCount(0)
        self.log.clear()
        self._buffer = b""

        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()
            self._proc.waitForFinished(1000)    

        proc = QProcess(self)
        self._proc = proc
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        proc.readyReadStandardOutput.connect(lambda: self._read_output(proc, output))

        def on_finished(code, status):
            if proc is not self._proc:
                return
            self._read_output(proc, output)
            self._flush_buffer(output)

        proc.finished.connect(on_finished)
        proc.errorOccurred.connect(
            lambda err: QMessageBox.warning(self, "Ошибка QProcess", str(err)))

        exe = shutil.which(command) or command
        proc.start(exe, args[1:])
