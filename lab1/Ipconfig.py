import shutil, ctypes, sys
from PyQt6.QtWidgets import QWidget, QLabel, QCheckBox, QLineEdit, QGridLayout, QPushButton, QVBoxLayout, QTableWidget, QHeaderView, QTableWidgetItem, \
                            QPlainTextEdit, QTabWidget, QMessageBox, QApplication
from PyQt6.QtCore import QProcess

from ToolBar import ToolBar


class Ipconfig(ToolBar):
    command = "ipconfig"

    def _build_ui(self):
        v = QVBoxLayout()
        grid = QGridLayout()

        self.cb_all         = QCheckBox("/all")
        self.cb_flushdns    = QCheckBox("/flushdns")
        self.cb_displaydns  = QCheckBox("/displaydns")
        self.cb_register    = QCheckBox("/registerdns")
        self.cb_release     = QCheckBox("/release")
        self.cb_renew       = QCheckBox("/renew")
        self.cb_showclassid = QCheckBox("/showclassid")
        self.cb_setclassid  = QCheckBox("/setclassid")

        flags = [self.cb_all, self.cb_flushdns, self.cb_displaydns,
                 self.cb_register, self.cb_release, self.cb_renew,
                 self.cb_showclassid, self.cb_setclassid]
        for i, cb in enumerate(flags):
            grid.addWidget(cb, 0, i)

        self.le_adapter = QLineEdit()
        self.le_adapter.setPlaceholderText("имя адаптера (для /release /renew /showclassid /setclassid)")
        self.le_classid = QLineEdit()
        self.le_classid.setPlaceholderText("ClassID, напр. 0001")

        grid.addWidget(QLabel("Адаптер:"), 1, 0)
        grid.addWidget(self.le_adapter, 1, 1, 1, 7)
        grid.addWidget(QLabel("ClassID:"), 2, 0)
        grid.addWidget(self.le_classid, 2, 1, 1, 7)

        v.addLayout(grid)

        btn = QPushButton("Запустить")
        v.addWidget(btn)
        btn.clicked.connect(self._run_all)

        self.tabs = QTabWidget()
        v.addWidget(self.tabs, 1)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(110)
        v.addWidget(self.log)

        self.setLayout(v)
        btn.clicked.connect(self._run_all)

    def _build_args(self):
        actions = []
        if self.cb_flushdns.isChecked():    actions.append("/flushdns")
        if self.cb_displaydns.isChecked():  actions.append("/displaydns")
        if self.cb_register.isChecked():    actions.append("/registerdns")
        if self.cb_release.isChecked():     actions.append("/release")
        if self.cb_renew.isChecked():       actions.append("/renew")
        if self.cb_showclassid.isChecked(): actions.append("/showclassid")
        if self.cb_setclassid.isChecked():  actions.append("/setclassid")

        if len(actions) > 1:
            QMessageBox.warning(self, "Ошибка", "Выберите только одну операцию")
            return None
        if self.cb_all.isChecked() and actions:
            QMessageBox.warning(self, "Ошибка", "/all нельзя совмещать с операциями")
            return None

        if not actions:
            return ["/all"] if self.cb_all.isChecked() else []

        flag = actions[0]
        args = [flag]
        adapter = self.le_adapter.text().strip()

        if flag in ("/showclassid", "/setclassid"):
            if not adapter:
                QMessageBox.warning(self, "Ошибка", f"Для {flag} нужен адаптер")
                return None
            args.append(adapter)
        elif flag in ("/release", "/renew"):
            if adapter:
                args.append(adapter)

        if flag == "/setclassid":
            code = self.le_classid.text().strip()
            if not code:
                QMessageBox.warning(self, "Ошибка", "Введите ClassID")
                return None
            args.append(code)

        return args

    def _run_all(self):
        args = self._build_args()
        if args is None:
            return

        self.tabs.clear()
        self.log.clear()

        old_proc = self._proc
        self._proc = None 
        
        if old_proc and old_proc.state() != QProcess.ProcessState.NotRunning:
            old_proc.kill()
            old_proc.waitForFinished(1000)

        proc = QProcess(self)
        self._proc = proc
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def on_finished(code, status):

            if proc is not self._proc:
                return

            text = proc.readAllStandardOutput().data().decode("cp866", errors="replace")
            if not args or args == ["/all"]:
                self._fill_tabs_from_blocks(self._parse_blocks(text))
            else:
                self._fill_single_tab("Вывод", text)

        proc.finished.connect(on_finished)
        exe = shutil.which(self.command) or self.command
        proc.start(exe, args)

    @staticmethod
    def _parse_blocks(text):
        blocks, name, items = [], None, []
        for line in text.splitlines():
            if not line.strip():
                continue
            if not line[0].isspace() and line.rstrip().endswith(":"):
                if name is not None:
                    blocks.append((name, items))
                name = line.rstrip()[:-1].strip()
                items = []
                continue
            if name is None:
                continue
            idx = line.find(":")
            if idx < 0:
                continue
            key = line[:idx].rstrip(". ").strip()
            val = line[idx + 1:].strip()
            if key:
                items.append((key, val))
        if name is not None:
            blocks.append((name, items))
        return blocks

    def _fill_tabs_from_blocks(self, blocks):
        if not blocks:
            self._fill_single_tab("Вывод", "")
            return
        for name, items in blocks:
            page = QWidget()
            v = QVBoxLayout(page)
            t = QTableWidget(len(items), 2)
            t.setHorizontalHeaderLabels(["Параметр", "Значение"])
            t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            t.setAlternatingRowColors(True)
            t.verticalHeader().setVisible(False)
            t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            t.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for i, (k, val) in enumerate(items):
                t.setItem(i, 0, QTableWidgetItem(k))
                t.setItem(i, 1, QTableWidgetItem(val))
            v.addWidget(t)
            self.tabs.addTab(page, name)

    def _fill_single_tab(self, title, text):
        page = QWidget()
        v = QVBoxLayout(page)
        te = QPlainTextEdit()
        te.setReadOnly(True)
        te.setPlainText(text)
        v.addWidget(te)
        self.tabs.addTab(page, title)