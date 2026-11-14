import shutil, re, ipaddress
from PyQt6.QtWidgets import QLabel, QLineEdit, QGridLayout, QPushButton, QVBoxLayout, QGroupBox, \
                            QMessageBox, QTableWidget, QHeaderView, QTableWidgetItem, QPlainTextEdit
from PyQt6.QtCore import QProcess

from ToolBar import ToolBar


class Arp(ToolBar):
    command = "arp"

    _iface_re = re.compile(r"^\s*(?:Интерфейс|Interface):\s*(\S+)")
    _entry_re = re.compile(r"^\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})\s+(\S+)")
    _mac_re = re.compile(r"^[0-9a-fA-F]{2}([-:][0-9a-fA-F]{2}){5}$")

    def _build_ui(self):
        self._queue = []
        self._last_show_args = ["-a"]
        self._selected = None 

        v = QVBoxLayout()

        show_box = QGroupBox("Просмотр: arp -a [IP-адрес] [-N интерфейс]")
        g1 = QGridLayout(show_box)
        self.le_filter_ip = QLineEdit()
        self.le_filter_ip.setPlaceholderText("IP-адрес узла (необязательно)")
        self.le_filter_if = QLineEdit()
        self.le_filter_if.setPlaceholderText("IP-адрес интерфейса (необязательно)")
        btn_show = QPushButton("Показать")
        g1.addWidget(QLabel("IP-адрес:"), 0, 0)
        g1.addWidget(self.le_filter_ip, 0, 1)
        g1.addWidget(QLabel("-N интерфейс:"), 0, 2)
        g1.addWidget(self.le_filter_if, 0, 3)
        g1.addWidget(btn_show, 0, 4)
        v.addWidget(show_box)

        edit_box = QGroupBox("Изменение ARP-таблицы (требуются права администратора)")
        g2 = QGridLayout(edit_box)
        self.le_ip = QLineEdit()
        self.le_ip.setPlaceholderText("inet_addr, напр. 192.168.1.50")
        self.le_mac = QLineEdit()
        self.le_mac.setPlaceholderText("eth_addr, напр. aa-bb-cc-dd-ee-ff")
        self.le_if = QLineEdit()
        self.le_if.setPlaceholderText("if_addr (необязательно)")

        g2.addWidget(QLabel("IP-адрес:"), 0, 0)
        g2.addWidget(self.le_ip, 0, 1)
        g2.addWidget(QLabel("MAC-адрес:"), 0, 2)
        g2.addWidget(self.le_mac, 0, 3)
        g2.addWidget(QLabel("Интерфейс:"), 0, 4)
        g2.addWidget(self.le_if, 0, 5)

        btn_add = QPushButton("Добавить (-s)")
        btn_change = QPushButton("Изменить выбранную")
        btn_del = QPushButton("Удалить (-d)")
        btn_clear = QPushButton("Очистить таблицу (-d *)")
        g2.addWidget(btn_add, 1, 0, 1, 2)
        g2.addWidget(btn_change, 1, 2, 1, 2)
        g2.addWidget(btn_del, 1, 4, 1, 1)
        g2.addWidget(btn_clear, 1, 5, 1, 1)
        v.addWidget(edit_box)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Интерфейс", "IP-адрес", "Физический адрес", "Тип"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        v.addWidget(self.table, 3)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(110)
        v.addWidget(self.log, 1)

        self.setLayout(v)

        btn_show.clicked.connect(self._on_show)
        btn_add.clicked.connect(self._on_add)
        btn_change.clicked.connect(self._on_change)
        btn_del.clicked.connect(self._on_delete)
        btn_clear.clicked.connect(self._on_clear)
        self.table.itemSelectionChanged.connect(self._on_select)

        self._show(["-a"])

    def _check_ip(self, text, what):
        try:
            ipaddress.IPv4Address(text)
            return True
        except ValueError:
            QMessageBox.warning(self, "Ошибка", f"Неверный {what}")
            return False

    def _read_edit_fields(self, need_mac):
        ip = self.le_ip.text().strip()
        mac = self.le_mac.text().strip()
        ifa = self.le_if.text().strip()

        if not ip:
            QMessageBox.warning(self, "Ошибка", "Введите IP-адрес")
            return None
        if not self._check_ip(ip, "IP-адрес"):
            return None
        if need_mac:
            if not mac:
                QMessageBox.warning(self, "Ошибка", "Введите MAC-адрес")
                return None
            if not self._mac_re.match(mac):
                QMessageBox.warning(self, "Ошибка", "Неверный MAC-адрес (формат aa-bb-cc-dd-ee-ff)")
                return None
            mac = mac.replace(":", "-")
        if ifa and not self._check_ip(ifa, "адрес интерфейса"):
            return None
        return ip, mac, ifa

    def _on_show(self):
        args = ["-a"]
        ip = self.le_filter_ip.text().strip()
        ifa = self.le_filter_if.text().strip()
        if ip:
            if not self._check_ip(ip, "IP-адрес"):
                return
            args.append(ip)
        if ifa:
            if not self._check_ip(ifa, "адрес интерфейса"):
                return
            args += ["-N", ifa]
        self._show(args)

    def _on_add(self):
        f = self._read_edit_fields(need_mac=True)
        if f is None:
            return
        ip, mac, ifa = f
        cmd = ["-s", ip, mac] + ([ifa] if ifa else [])
        self._modify([cmd])

    def _on_change(self):
        if self._selected is None:
            QMessageBox.warning(self, "Ошибка", "Выберите запись в таблице")
            return
        f = self._read_edit_fields(need_mac=True)
        if f is None:
            return
        ip, mac, ifa = f
        old_ip, old_if = self._selected

        cmds = []
        if ip != old_ip or (ifa and ifa != old_if):
            cmds.append(["-d", old_ip, old_if])
        cmds.append(["-s", ip, mac] + ([ifa] if ifa else []))
        self._modify(cmds)

    def _on_delete(self):
        f = self._read_edit_fields(need_mac=False)
        if f is None:
            return
        ip, _, ifa = f
        self._modify([["-d", ip] + ([ifa] if ifa else [])])

    def _on_clear(self):
        ans = QMessageBox.question(self, "Подтверждение",
                                   "Очистить всю ARP-таблицу (arp -d *)?")
        if ans == QMessageBox.StandardButton.Yes:
            self._modify([["-d", "*"]])

    def _on_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self._selected = None
            return
        r = rows[0].row()
        iface = self.table.item(r, 0).text()
        ip = self.table.item(r, 1).text()
        mac = self.table.item(r, 2).text()
        self.le_ip.setText(ip)
        self.le_mac.setText(mac)
        self.le_if.setText(iface)
        self._selected = (ip, iface)

    def _start(self, args):
        if self._proc and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()
            self._proc.waitForFinished(1000)

        proc = QProcess(self)
        self._proc = proc
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.errorOccurred.connect(
            lambda err: QMessageBox.warning(self, "Ошибка QProcess", str(err)))
        exe = shutil.which(self.command) or self.command
        proc.start(exe, args)
        return proc

    @staticmethod
    def _decode(proc):
        return proc.readAllStandardOutput().data().decode("cp866", errors="replace").strip()

    def _show(self, args):
        self._last_show_args = args
        proc = self._start(args)

        def on_finished(code, status):
            if proc is not self._proc:
                return
            text = self._decode(proc)
            rows = self._parse(text)
            self._fill_table(rows)
            if not rows and text:
                self.log.appendPlainText(text)

        proc.finished.connect(on_finished)

    def _modify(self, commands):
        self.log.clear()
        self._queue = list(commands)
        self._next()

    def _next(self):
        if not self._queue:
            self._show(self._last_show_args)
            return

        args = self._queue.pop(0)
        self.log.appendPlainText("> arp " + " ".join(args))
        proc = self._start(args)

        def on_finished(code, status):
            if proc is not self._proc:
                return
            text = self._decode(proc)
            if text:
                self.log.appendPlainText(text)
            if code != 0:
                self._queue.clear() 
            self._next()

        proc.finished.connect(on_finished)

    def _parse(self, text):
        rows, iface = [], ""
        for line in text.splitlines():
            m = self._iface_re.match(line)
            if m:
                iface = m.group(1)
                continue
            m = self._entry_re.match(line)
            if m:
                rows.append((iface, m.group(1), m.group(2), m.group(3)))
        return rows

    def _fill_table(self, rows):
        self._selected = None
        self.table.setRowCount(0)
        for r, values in enumerate(rows):
            self.table.insertRow(r)
            for c, val in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(val))
