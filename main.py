import os
import sys
import time
import random
from pathlib import Path

import psutil
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QVBoxLayout,
    QHBoxLayout, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QPushButton, QSpinBox, QCheckBox,
    QSystemTrayIcon, QStyle, QStackedWidget, QLineEdit
)

BG = "#111114"
SURFACE = "#19191E"
BORDER = "#303036"
PURPLE = "#A987C7"
TEXT = "#E8E5EC"
MUTED = "#85818D"
RED = "#E77A8B"
ORANGE = "#D9A16C"

STYLE = f"""
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-family: 'Segoe UI'; font-size: 13px; }}
QFrame#sidebar {{ background: #16161B; border-right: 1px solid {BORDER}; }}
QFrame#panel {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 5px; }}
QFrame#tuftPanel {{ background: #211C29; border: 1px solid #40344B; border-radius: 5px; }}
QLabel#brand {{ font-size: 24px; font-weight: 700; color: #D9B8F1; }}
QLabel#pageTitle {{ font-size: 23px; font-weight: 650; }}
QLabel#subtitle, QLabel#detail {{ color: {MUTED}; font-size: 11px; }}
QLabel#heading {{ color: {MUTED}; font-size: 11px; font-weight: 650; }}
QLabel#percentage {{ font-size: 31px; font-weight: 700; }}
QLabel#tuftTitle {{ color: #D9B8F1; font-weight: 700; }}
QLabel#tuftText {{ font-size: 14px; color: #F1E8F7; }}
QProgressBar {{ background: #302C36; border: none; border-radius: 2px; }}
QProgressBar::chunk {{ background: {PURPLE}; border-radius: 2px; }}
QPushButton {{ background: #30283A; border: 1px solid #51405C; border-radius: 4px; padding: 9px 13px; }}
QPushButton:hover {{ background: #42324E; }}
QPushButton:pressed {{ background: #5B4269; }}
QPushButton#nav {{ background: transparent; border: none; color: #AAA4B2; text-align: left; padding: 12px 14px; border-radius: 4px; }}
QPushButton#nav:hover {{ background: #25232D; color: {TEXT}; }}
QPushButton#nav[active="true"] {{ background: #352B41; color: #E8CFF8; font-weight: 650; }}
QLineEdit, QSpinBox {{ background: #24232B; border: 1px solid {BORDER}; border-radius: 4px; padding: 8px; }}
QLineEdit:focus, QSpinBox:focus {{ border-color: {PURPLE}; }}
QCheckBox {{ spacing: 8px; }}
QTableWidget {{ background: {SURFACE}; alternate-background-color: #1D1D23; border: none; gridline-color: transparent; selection-background-color: #393043; outline: none; }}
QTableWidget::item {{ padding: 5px; border: none; }}
QHeaderView::section {{ background: #202027; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 8px; font-size: 11px; }}
"""


def format_bytes(value):
    if value >= 1024 ** 3:
        return f"{value / 1024 ** 3:.1f} GB"
    return f"{value / 1024 ** 2:.0f} MB"


def usage_color(percent):
    return RED if percent >= 90 else ORANGE if percent >= 75 else PURPLE


class ResourceCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        name = QLabel(title.upper())
        name.setObjectName("heading")
        self.percentage = QLabel("--%")
        self.percentage.setObjectName("percentage")
        self.detail = QLabel("collecting data...")
        self.detail.setObjectName("detail")
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(5)
        layout.addWidget(name)
        layout.addWidget(self.percentage)
        layout.addWidget(self.detail)
        layout.addStretch()
        layout.addWidget(self.bar)

    def update_usage(self, percent, detail):
        self.percentage.setText(f"{percent:.0f}%")
        self.detail.setText(detail)
        self.bar.setValue(round(percent))
        self.bar.setStyleSheet(f"QProgressBar::chunk {{ background: {usage_color(percent)}; }}")


class ProcessWorker(QThread):
    # dont make the entire window freeze just to read chrome for the 700th time
    updated = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while self.running:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "memory_info"]):
                if not self.running:
                    return
                try:
                    info = proc.info
                    memory = info["memory_info"]
                    if memory is not None:
                        processes.append((info["name"] or "Unknown", info["pid"], memory.rss))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            processes.sort(key=lambda item: item[2], reverse=True)
            self.updated.emit(processes)
            for _ in range(80):
                if not self.running:
                    return
                self.msleep(100)


class PettableTuft(QLabel):
    petted = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.petted.emit()
        super().mousePressEvent(event)


class TuftController:
    ROWS = {"normal": 0, "concerned": 3, "angry": 6, "confused": 5, "sleeping": 2, "happy": 1}
    IDLE_LINES = [
        "i am supervising. unfortunately.",
        "did you know closing programs is free?",
        "your computer is suspiciously quiet.",
        "i deserve a raise for this.",
        "meowtop is judging you. professionally."
    ]

    def __init__(self, image, mood_label, text_label):
        self.image = image
        self.mood_label = mood_label
        self.text_label = text_label
        self.sheet = QPixmap(str(Path(__file__).with_name("tuft-sprites.png")))
        self.frames = {}
        if not self.sheet.isNull():
            w, h = self.sheet.width() // 4, self.sheet.height() // 8
            for mood, row in self.ROWS.items():
                self.frames[mood] = [
                    self.sheet.copy(i * w, row * h, w, h).scaled(
                        120, 110, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.FastTransformation
                    ) for i in range(4)
                ]
        self.mood = "normal"
        self.frame = 0
        self.current_event = None
        self.last_reaction = time.monotonic()
        self.last_speech = time.monotonic()
        self.idle_lines_spoken = 0
        self.temporary_until = 0
        self.draw()

    def draw(self):
        if not self.frames:
            self.image.setText("=^.^=")
            return
        self.image.setPixmap(self.frames[self.mood][self.frame])

    def animate(self):
        self.frame = (self.frame + 1) % 4
        self.draw()

    def set_mood(self, mood):
        if self.mood != mood:
            self.mood = mood
            self.frame = 0
            self.mood_label.setText(mood.upper())
            self.draw()

    def say(self, message):
        self.text_label.setText(message)
        self.last_speech = time.monotonic()

    def temporary_reaction(self, mood, line, seconds):
        self.set_mood(mood)
        self.say(line)
        self.temporary_until = time.monotonic() + seconds

    def pet(self):
        self.temporary_reaction("happy", random.choice([
            "mrrrp :3", "purrrrr...", "okay fine. that was nice.",
            "you may pet me again.", "meow! :3"
        ]), 3)

    def react(self, cpu, ram, top_process):
        # he gets used to the chaos after a bit instead of being confused forever
        now = time.monotonic()
        if now < self.temporary_until:
            return
        if self.temporary_until:
            self.temporary_until = 0
            self.current_event = None

        if ram >= 90:
            event, mood, line = "ram_critical", "angry", "90% ram. WHAT ARE YOU DOING."
        elif cpu >= 95:
            event, mood, line = "cpu_critical", "angry", "your cpu is fighting for its life."
        elif ram >= 75:
            event, mood, line = "ram_high", "concerned", "your ram is getting crowded."
        elif cpu >= 75:
            event, mood, line = "cpu_high", "concerned", "are you rendering the entire universe?"
        elif top_process and top_process[2] >= 2 * 1024 ** 3:
            event, mood = f"huge_{top_process[1]}", "confused"
            line = f"{top_process[0]} is using {format_bytes(top_process[2])}. excuse me?"
        else:
            event, mood, line = "normal", "normal", "everything looks suspiciously normal."

        if event != self.current_event:
            self.current_event = event
            self.last_reaction = now
            self.idle_lines_spoken = 0
            self.set_mood(mood)
            self.say(line)
            return

        if event != "normal":
            if now - self.last_reaction >= 20 and self.mood != "sleeping":
                self.set_mood("sleeping")
                self.say("whatever. wake me up if something changes. zzZ...")
            return

        if self.mood == "sleeping":
            return
        if now - self.last_speech >= 35:
            self.idle_lines_spoken += 1
            if self.idle_lines_spoken >= 3:
                self.set_mood("sleeping")
                self.say("zzZ...")
            else:
                self.set_mood("normal")
                self.say(random.choice(self.IDLE_LINES))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("meowtop")
        self.resize(1080, 735)
        self.setMinimumSize(830, 610)
        self.settings = QSettings("meowtop", "meowtop")
        self.processes = []
        self.alerts = []
        self.last_alert = 0
        self.alert_armed = True
        self.build_ui()
        self.setup_tray()
        psutil.cpu_percent(interval=None)

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.tuft.animate)
        self.animation_timer.start(350)
        self.worker = ProcessWorker()
        self.worker.updated.connect(self.update_processes)
        self.worker.start()
        self.update_stats()

    def title(self, text, description):
        title = QLabel(text)
        title.setObjectName("pageTitle")
        subtitle = QLabel(description)
        subtitle.setObjectName("detail")
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return layout

    def panel(self):
        panel = QFrame()
        panel.setObjectName("panel")
        return panel

    def make_table(self):
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(["PROCESS", "PID", "MEMORY"])
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().hide()
        table.verticalHeader().setDefaultSectionSize(32)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(1, 100)
        table.setColumnWidth(2, 125)
        return table

    def fill_table(self, table, processes):
        table.setUpdatesEnabled(False)
        try:
            table.setRowCount(len(processes))
            for row, (name, pid, memory) in enumerate(processes):
                for col, value in enumerate((name, str(pid), format_bytes(memory))):
                    item = QTableWidgetItem(value)
                    if col == 2:
                        item.setData(Qt.ItemDataRole.UserRole, memory)
                    if col > 0:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    table.setItem(row, col, item)
        finally:
            table.setUpdatesEnabled(True)

    def build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(188)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(15, 24, 15, 20)
        nav.setSpacing(7)
        brand = QLabel("meowtop")
        brand.setObjectName("brand")
        nav.addWidget(brand)
        caption = QLabel("a very judgmental cat")
        caption.setObjectName("subtitle")
        nav.addWidget(caption)
        nav.addSpacing(25)

        self.stack = QStackedWidget()
        self.nav_buttons = []
        for index, name in enumerate(("Overview", "Processes", "History", "Settings")):
            btn = QPushButton(name)
            btn.setObjectName("nav")
            btn.setProperty("active", index == 0)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=index: self.change_page(i))
            nav.addWidget(btn)
            self.nav_buttons.append(btn)
        nav.addStretch()
        version = QLabel("meowtop  /  v0.4")
        version.setObjectName("detail")
        nav.addWidget(version)

        outer.addWidget(sidebar)
        outer.addWidget(self.stack, 1)
        self.build_overview()
        self.build_processes()
        self.build_history()
        self.build_settings()

    def page_layout(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 25, 28, 23)
        layout.setSpacing(16)
        self.stack.addWidget(page)
        return layout

    def build_overview(self):
        page = self.page_layout()
        page.addLayout(self.title("Overview", "your computer, under judgment"))
        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.cpu_card = ResourceCard("Processor")
        self.ram_card = ResourceCard("Memory")
        self.disk_card = ResourceCard("System drive")
        for card in (self.cpu_card, self.ram_card, self.disk_card):
            cards.addWidget(card)
        page.addLayout(cards)

        tuft_panel = QFrame()
        tuft_panel.setObjectName("tuftPanel")
        tuft_layout = QHBoxLayout(tuft_panel)
        tuft_layout.setContentsMargins(18, 13, 18, 13)
        tuft_layout.setSpacing(16)
        self.tuft_image = PettableTuft()
        self.tuft_image.setFixedSize(124, 112)
        self.tuft_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tuft_image.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tuft_image.setToolTip("pet tuft :3")
        tuft_layout.addWidget(self.tuft_image)
        speech = QVBoxLayout()
        speech.setSpacing(8)
        heading = QHBoxLayout()
        tuft_title = QLabel("tuft")
        tuft_title.setObjectName("tuftTitle")
        self.mood_label = QLabel("NORMAL")
        self.mood_label.setObjectName("detail")
        heading.addWidget(tuft_title)
        heading.addStretch()
        heading.addWidget(self.mood_label)
        self.tuft_text = QLabel("examining your computer...")
        self.tuft_text.setObjectName("tuftText")
        self.tuft_text.setWordWrap(True)
        speech.addLayout(heading)
        speech.addWidget(self.tuft_text)
        speech.addStretch()
        tuft_layout.addLayout(speech, 1)
        page.addWidget(tuft_panel)
        self.tuft = TuftController(self.tuft_image, self.mood_label, self.tuft_text)
        self.tuft_image.petted.connect(self.tuft.pet)

        process_panel = self.panel()
        container = QVBoxLayout(process_panel)
        container.setContentsMargins(13, 12, 13, 12)
        line = QHBoxLayout()
        label = QLabel("TOP PROCESSES")
        label.setObjectName("heading")
        view_all = QPushButton("View all")
        view_all.clicked.connect(lambda: self.change_page(1))
        line.addWidget(label)
        line.addStretch()
        line.addWidget(view_all)
        container.addLayout(line)
        self.top_table = self.make_table()
        container.addWidget(self.top_table)
        page.addWidget(process_panel, 1)
        bottom = QHBoxLayout()
        bottom.addStretch()
        roast = QPushButton("Roast my PC")
        roast.clicked.connect(self.roast_pc)
        bottom.addWidget(roast)
        page.addLayout(bottom)

    def build_processes(self):
        page = self.page_layout()
        page.addLayout(self.title("Processes", "all the things your computer insists on running"))
        searchbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search by name or PID...")
        self.search.textChanged.connect(self.filter_processes)
        self.process_count = QLabel("Loading...")
        self.process_count.setObjectName("detail")
        searchbar.addWidget(self.search, 1)
        searchbar.addWidget(self.process_count)
        page.addLayout(searchbar)
        frame = self.panel()
        content = QVBoxLayout(frame)
        content.setContentsMargins(9, 9, 9, 9)
        self.full_table = self.make_table()
        self.full_table.setSortingEnabled(True)
        self.full_table.horizontalHeader().setSortIndicator(2, Qt.SortOrder.DescendingOrder)
        content.addWidget(self.full_table)
        page.addWidget(frame, 1)

    def build_history(self):
        page = self.page_layout()
        page.addLayout(self.title("History", "ram warnings from this session"))
        frame = self.panel()
        content = QVBoxLayout(frame)
        content.setContentsMargins(18, 18, 18, 18)
        self.history_label = QLabel("no warnings yet. suspiciously peaceful.")
        self.history_label.setObjectName("detail")
        self.history_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.history_label.setWordWrap(True)
        content.addWidget(self.history_label)
        content.addStretch()
        page.addWidget(frame, 1)

    def build_settings(self):
        page = self.page_layout()
        page.addLayout(self.title("Settings", "how much should tuft bother you"))
        frame = self.panel()
        content = QVBoxLayout(frame)
        content.setContentsMargins(20, 20, 20, 20)
        content.setSpacing(15)
        heading = QLabel("RAM WARNING AT")
        heading.setObjectName("heading")
        self.threshold = QSpinBox()
        self.threshold.setRange(50, 99)
        self.threshold.setSuffix("%")
        self.threshold.setValue(int(self.settings.value("threshold", 90)))
        self.threshold.valueChanged.connect(self.save_settings)
        self.notify = QCheckBox("Windows notifications")
        self.notify.setChecked(self.settings.value("notify", "true") == "true")
        self.notify.toggled.connect(self.save_settings)
        content.addWidget(heading)
        content.addWidget(self.threshold)
        content.addWidget(self.notify)
        note = QLabel("notifications only fire again after ram drops below the reset point and crosses the limit again.")
        note.setObjectName("detail")
        note.setWordWrap(True)
        content.addWidget(note)
        content.addStretch()
        page.addWidget(frame, 1)

    def change_page(self, index):
        # yes this is literally just switching which page is visible
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            button.setProperty("active", i == index)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.tray.setToolTip("meowtop")
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def save_settings(self, *_):
        self.settings.setValue("threshold", self.threshold.value())
        self.settings.setValue("notify", "true" if self.notify.isChecked() else "false")

    def update_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory()
            drive = os.environ.get("SystemDrive", "C:") + "\\"
            disk = psutil.disk_usage(drive)
            self.cpu_card.update_usage(cpu, f"{psutil.cpu_count()} logical processors")
            self.ram_card.update_usage(ram.percent, f"{format_bytes(ram.used)} / {format_bytes(ram.total)}")
            self.disk_card.update_usage(disk.percent, f"{format_bytes(disk.free)} available")
            self.tuft.react(cpu, ram.percent, self.processes[0] if self.processes else None)
            self.check_alert(ram.percent)
        except (OSError, RuntimeError) as error:
            self.tuft.say(f"couldn't read system stats: {error}")

    def update_processes(self, processes):
        self.processes = processes
        self.process_count.setText(f"{len(processes)} running")
        self.fill_table(self.top_table, processes[:5])
        self.filter_processes()

    def filter_processes(self):
        term = self.search.text().strip().lower()
        filtered = [p for p in self.processes if term in p[0].lower() or term in str(p[1])]
        sort_col = self.full_table.horizontalHeader().sortIndicatorSection()
        sort_order = self.full_table.horizontalHeader().sortIndicatorOrder()
        self.full_table.setSortingEnabled(False)
        self.fill_table(self.full_table, filtered)
        self.full_table.setSortingEnabled(True)
        self.full_table.sortItems(sort_col, sort_order)

    def check_alert(self, ram):
        # please do not notify me 400 times because ram is at 90%
        threshold = self.threshold.value()
        if ram <= threshold - 5:
            self.alert_armed = True
        now = time.monotonic()
        if ram >= threshold and self.alert_armed and now - self.last_alert >= 300:
            self.alert_armed = False
            self.last_alert = now
            stamp = time.strftime("%H:%M:%S")
            self.alerts.insert(0, f"{stamp}  /  RAM reached {ram:.0f}%")
            self.history_label.setText("\n\n".join(self.alerts[:30]))
            if self.notify.isChecked() and self.tray.isVisible() and QSystemTrayIcon.supportsMessages():
                self.tray.showMessage(
                    "meowtop · RAM warning",
                    f"RAM reached {ram:.0f}%. tuft is disappointed.",
                    QSystemTrayIcon.MessageIcon.Warning, 6000
                )

    def roast_pc(self):
        lines = [
            "have you considered closing a program?",
            "this computer deserves better.",
            "i want hazard pay for monitoring this thing.",
            "your task manager needs a task manager.",
            "the amount of chrome processes is a personal attack.",
            "i'm telling your cpu what you've done.",
            "revoking computer privileges.",
            "enough."
        ]
        self.tuft.temporary_reaction("confused", random.choice(lines), 6)

    def closeEvent(self, event):
        self.worker.running = False
        self.worker.wait()
        self.tray.hide()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
