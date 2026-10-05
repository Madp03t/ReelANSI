"""
ReelANSI
A lightweight Linux ANSI art viewer.

Code by Eric Montgomery (Madp03t)
"""

import os
import sys
import re

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QFontDatabase, QPainter

ANSI_COLOR_MAP = {
    30: 0,
    31: 1,
    32: 2,
    33: 3,
    34: 4,
    35: 5,
    36: 6,
    37: 7,
    90: 0,
    91: 1,
    92: 2,
    93: 3,
    94: 4,
    95: 5,
    96: 6,
    97: 7,
}

VGA_COLORS = [
    (0, 0, 0),
    (170, 0, 0),
    (0, 170, 0),
    (170, 85, 0),
    (0, 0, 170),
    (170, 0, 170),
    (0, 170, 170),
    (170, 170, 170),
    (85, 85, 85),
    (255, 85, 85),
    (85, 255, 85),
    (255, 255, 85),
    (85, 85, 255),
    (255, 85, 255),
    (85, 255, 255),
    (255, 255, 255),
]

def read_sauce(data: bytes):
    if len(data) < 128:
        return None

    trailer = data[data.rfind(b"SAUCE00"):]
    if trailer[:5] != b"SAUCE":
        return None

    return {
        "width": int.from_bytes(trailer[96:98], "little"),
        "height": int.from_bytes(trailer[98:100], "little"),
    }

class ANSIStreamParser:
    """Incremental ANSI terminal parser for static art and ansimation playback."""

    def __init__(self, width=80, height=25):
        self.width = max(1, width or 80)
        self.height = max(1, height or 25)
        self.reset()

    def reset(self):
        self.x = 0
        self.y = 0
        self.fg = 7
        self.bg = 0
        self.saved_x = 0
        self.saved_y = 0
        self.cells = {}
        self.escape = None

    def feed(self, text):
        for ch in text:
            self.feed_char(ch)

    def feed_char(self, ch):
        if self.escape is not None:
            self.escape += ch
            if len(self.escape) == 2 and ch != "[":
                self.escape = None
                return
            if len(self.escape) >= 3 and self.escape.startswith("\x1b["):
                if "@" <= ch <= "~":
                    self._handle_csi(self.escape)
                    self.escape = None
                elif len(self.escape) > 64:
                    self.escape = None
            return

        if ch == "\x1b":
            self.escape = "\x1b"
            return
        if ch == "\x00":
            ch = " "
        if ch == "\r":
            self.x = 0
            return
        if ch == "\n":
            self.y += 1
            self.x = 0
            return
        if ch == "\b":
            self.x = max(0, self.x - 1)
            return
        if ch == "\t":
            self.x = min(self.width - 1, ((self.x // 8) + 1) * 8)
            return
        if ord(ch) < 32:
            return

        if self.x >= self.width:
            self.x = 0
            self.y += 1

        self.cells[(self.x, self.y)] = (ch, self.fg, self.bg)
        self.x += 1

    def _handle_csi(self, sequence):
        match = re.match(r"\x1b\[([0-9;?]*)([@-~])$", sequence)
        if not match:
            return

        params, cmd = match.groups()
        clean = params.lstrip("?")
        nums = [int(n) if n else 0 for n in clean.split(";")] if clean else []
        amount = nums[0] if nums and nums[0] else 1

        if cmd == "m":
            for n in nums or [0]:
                if n == 0:
                    self.fg, self.bg = 7, 0
                elif n == 1:
                    if self.fg < 8:
                        self.fg += 8
                elif n == 22:
                    if self.fg >= 8:
                        self.fg -= 8
                elif 30 <= n <= 37:
                    self.fg = n - 30
                elif 40 <= n <= 47:
                    self.bg = n - 40
                elif 90 <= n <= 97:
                    self.fg = n - 90 + 8
                elif 100 <= n <= 107:
                    self.bg = n - 100 + 8
        elif cmd in ("H", "f"):
            row = nums[0] if len(nums) >= 1 and nums[0] else 1
            col = nums[1] if len(nums) >= 2 and nums[1] else 1
            self.y = max(0, row - 1)
            self.x = max(0, col - 1)
        elif cmd == "A":
            self.y = max(0, self.y - amount)
        elif cmd == "B":
            self.y += amount
        elif cmd == "C":
            self.x += amount
        elif cmd == "D":
            self.x = max(0, self.x - amount)
        elif cmd == "E":
            self.y += amount
            self.x = 0
        elif cmd == "F":
            self.y = max(0, self.y - amount)
            self.x = 0
        elif cmd == "G":
            self.x = max(0, amount - 1)
        elif cmd == "J":
            mode = nums[0] if nums else 0
            if mode in (2, 3):
                self.cells.clear()
            elif mode == 0:
                self.cells = {
                    pos: cell for pos, cell in self.cells.items()
                    if pos[1] < self.y or (pos[1] == self.y and pos[0] < self.x)
                }
            elif mode == 1:
                self.cells = {
                    pos: cell for pos, cell in self.cells.items()
                    if pos[1] > self.y or (pos[1] == self.y and pos[0] > self.x)
                }
        elif cmd == "K":
            mode = nums[0] if nums else 0
            if mode == 0:
                self.cells = {
                    pos: cell for pos, cell in self.cells.items()
                    if pos[1] != self.y or pos[0] < self.x
                }
            elif mode == 1:
                self.cells = {
                    pos: cell for pos, cell in self.cells.items()
                    if pos[1] != self.y or pos[0] > self.x
                }
            elif mode == 2:
                self.cells = {pos: cell for pos, cell in self.cells.items() if pos[1] != self.y}
        elif cmd == "s":
            self.saved_x, self.saved_y = self.x, self.y
        elif cmd == "u":
            self.x, self.y = self.saved_x, self.saved_y


def parse_ansi(text, fixed_width=80, fixed_height=25):
    parser = ANSIStreamParser(fixed_width, fixed_height)
    parser.feed(text)
    return parser.cells


def looks_animated(text):
    # Ansimation files commonly use repeated cursor-save sequences as timing
    # padding, or repeatedly clear/reposition the terminal after drawing begins.
    if text.count("\x1b[s") >= 10:
        return True
    if text.count("\x1b[2J") >= 2:
        return True
    return False


class ANSIViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.cell_width = 9
        self.cell_height = 16
        self.screen_width = 80
        self.screen_height = 25

        font_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "fonts",
            "Px437_IBM_VGA_9x16.ttf",
        )

        font_id = QFontDatabase.addApplicationFont(font_path)
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

        self.font = QFont(font_family)
        self.font.setPixelSize(16)

    def set_screen(self, cells, width=None, height=None):
        self.cells = dict(cells)
        if width:
            self.screen_width = width
        if height:
            self.screen_height = height

        max_x = max((x for x, _ in self.cells), default=self.screen_width - 1)
        max_y = max((y for _, y in self.cells), default=self.screen_height - 1)
        display_width = max(self.screen_width, max_x + 1)
        display_height = max(self.screen_height, max_y + 1)
        self.setFixedSize(display_width * self.cell_width, display_height * self.cell_height)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
        painter.setFont(self.font)
        painter.fillRect(self.rect(), QColor(*VGA_COLORS[0]))

        for (x, y), (ch, fg, bg) in self.cells.items():
            fg_color = QColor(*VGA_COLORS[fg])
            bg_color = QColor(*VGA_COLORS[bg])
            left = x * self.cell_width
            top = y * self.cell_height
            painter.fillRect(left, top, self.cell_width, self.cell_height, bg_color)
            painter.setPen(fg_color)
            painter.drawText(
                left,
                top,
                self.cell_width,
                self.cell_height,
                Qt.AlignmentFlag.AlignCenter,
                ch,
            )


class ReelANSI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.current_file = None
        self.ansi_files = []
        self.ansi_text = ""
        self.ansi_width = 80
        self.ansi_height = 25
        self.stream_parser = None
        self.playback_position = 0
        self.playback_remainder = 0.0
        self.is_playing = False
        self.is_animation = False

        self.playback_timer = QTimer(self)
        self.playback_timer.setInterval(16)
        self.playback_timer.timeout.connect(self.playback_tick)

        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open ANSI...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_ansi)
        file_menu.addAction(open_action)

        open_folder_action = QAction("Open &Folder...", self)
        open_folder_action.setShortcut("Ctrl+Shift+O")
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)

        previous_action = QAction("Previous ANSI", self)
        previous_action.setShortcut(Qt.Key.Key_Left)
        previous_action.triggered.connect(self.previous_ansi)
        self.addAction(previous_action)

        next_action = QAction("Next ANSI", self)
        next_action.setShortcut(Qt.Key.Key_Right)
        next_action.triggered.connect(self.next_ansi)
        self.addAction(next_action)

        self.setWindowTitle("ReelANSI v0.1  •  by Madp03t")
        self.resize(1000, 700)

        container = QWidget()
        layout = QVBoxLayout(container)

        self.viewer = ANSIViewer()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.viewer)
        self.scroll_area.setWidgetResizable(False)

        layout.addWidget(self.scroll_area, 1)

        playback_layout = QHBoxLayout()
        playback_layout.setContentsMargins(0, 0, 0, 0)

        self.play_button = QPushButton("▶ Play")
        self.play_button.setToolTip("Play or pause ANSI animation")
        self.play_button.clicked.connect(self.toggle_playback)

        self.restart_button = QPushButton("↻ Restart")
        self.restart_button.setToolTip("Restart ANSI animation")
        self.restart_button.clicked.connect(self.restart_playback)

        self.speed_label = QLabel("Playback")
        self.speed_combo = QComboBox()
        self.speed_combo.addItem("300 baud", 300)
        self.speed_combo.addItem("1200 baud", 1200)
        self.speed_combo.addItem("2400 baud", 2400)
        self.speed_combo.addItem("9600 baud", 9600)
        self.speed_combo.addItem("14.4K", 14400)
        self.speed_combo.addItem("28.8K", 28800)
        self.speed_combo.addItem("56K", 56000)
        self.speed_combo.addItem("Instant", 0)
        self.speed_combo.setCurrentIndex(3)
        self.speed_combo.currentIndexChanged.connect(self.playback_speed_changed)

        playback_layout.addWidget(self.play_button)
        playback_layout.addWidget(self.restart_button)
        playback_layout.addStretch(1)
        playback_layout.addWidget(self.speed_label)
        playback_layout.addWidget(self.speed_combo)
        layout.addLayout(playback_layout)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)

        self.file_info = QLabel("No file open")
        self.folder_info = QLabel("")
        self.folder_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.previous_button = QLabel("◀")
        self.previous_button.setToolTip("Previous ANSI (Left Arrow)")
        self.previous_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.previous_button.mousePressEvent = lambda event: self.previous_ansi()

        self.position_info = QLabel("0 / 0")
        self.position_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.next_button = QLabel("▶")
        self.next_button.setToolTip("Next ANSI (Right Arrow)")
        self.next_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_button.mousePressEvent = lambda event: self.next_ansi()

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(8)
        nav_layout.addWidget(self.previous_button)
        nav_layout.addWidget(self.position_info)
        nav_layout.addWidget(self.next_button)

        status_layout.addWidget(self.file_info)
        status_layout.addStretch(1)
        status_layout.addWidget(self.folder_info)
        status_layout.addStretch(1)
        status_layout.addLayout(nav_layout)

        layout.addLayout(status_layout)

        self.setCentralWidget(container)

    def ansi_files_in_folder(self, folder):
        return sorted(
            (
                os.path.join(folder, file)
                for file in os.listdir(folder)
                if file.lower().endswith(".ans")
            ),
            key=lambda path: os.path.basename(path).lower(),
        )

    def open_ansi(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open ANSI File",
            "",
            "ANSI Files (*.ans *.ANS)",
        )

        if filename:
            folder = os.path.dirname(filename)
            self.ansi_files = self.ansi_files_in_folder(folder)
            self.load_ansi(filename)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Open ANSI Folder",
            "",
        )

        if folder:
            ansi_files = self.ansi_files_in_folder(folder)

            if ansi_files:
                self.ansi_files = ansi_files
                self.load_ansi(self.ansi_files[0])

    def load_ansi(self, filename):
        self.stop_playback()

        with open(filename, "rb") as file:
            ansi_data = file.read()

        sauce = read_sauce(ansi_data)
        sauce_position = ansi_data.rfind(b"SAUCE00")
        ansi_content = ansi_data[:sauce_position] if sauce_position != -1 else ansi_data
        ansi_content = ansi_content.rstrip(b"\x1a")

        self.ansi_text = ansi_content.decode("cp437")
        self.ansi_width = sauce["width"] if sauce and sauce["width"] else 80
        sauce_height = sauce["height"] if sauce and sauce["height"] else 0
        self.ansi_height = sauce_height or 25
        self.is_animation = looks_animated(self.ansi_text)

        self.current_file = filename
        name = os.path.basename(filename)
        folder = os.path.dirname(filename)

        if self.is_animation:
            self.restart_playback(auto_play=True)
        else:
            parsed = parse_ansi(self.ansi_text, self.ansi_width, self.ansi_height)
            rendered_height = max((y for _, y in parsed), default=self.ansi_height - 1) + 1
            self.ansi_height = max(self.ansi_height, rendered_height)
            self.viewer.set_screen(parsed, self.ansi_width, self.ansi_height)
            self.play_button.setText("▶ Play")

        display_height = sauce_height or self.ansi_height
        self.file_info.setText(f"{name}   •   {self.ansi_width} × {display_height}")
        self.folder_info.setText(folder)

        try:
            current_index = self.ansi_files.index(filename)
            self.position_info.setText(f"{current_index + 1} / {len(self.ansi_files)}")
        except ValueError:
            self.position_info.setText("0 / 0")

        QApplication.processEvents()
        self.scroll_area.horizontalScrollBar().setValue(0)
        self.scroll_area.verticalScrollBar().setValue(0)

    def stop_playback(self):
        self.playback_timer.stop()
        self.is_playing = False
        if hasattr(self, "play_button"):
            self.play_button.setText("▶ Play")

    def restart_playback(self, auto_play=False):
        if not self.ansi_text:
            return

        self.stop_playback()
        self.stream_parser = ANSIStreamParser(self.ansi_width, self.ansi_height)
        self.playback_position = 0
        self.playback_remainder = 0.0
        self.viewer.set_screen({}, self.ansi_width, self.ansi_height)

        if self.speed_combo.currentData() == 0:
            self.finish_instantly()
            return

        if auto_play or self.is_animation:
            self.start_playback()

    def start_playback(self):
        if not self.ansi_text:
            return
        if self.stream_parser is None or self.playback_position >= len(self.ansi_text):
            self.stream_parser = ANSIStreamParser(self.ansi_width, self.ansi_height)
            self.playback_position = 0
            self.playback_remainder = 0.0
            self.viewer.set_screen({}, self.ansi_width, self.ansi_height)

        if self.speed_combo.currentData() == 0:
            self.finish_instantly()
            return

        self.is_playing = True
        self.play_button.setText("⏸ Pause")
        self.playback_timer.start()

    def toggle_playback(self):
        if not self.ansi_text:
            return
        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()

    def finish_instantly(self):
        if not self.ansi_text:
            return
        if self.stream_parser is None:
            self.stream_parser = ANSIStreamParser(self.ansi_width, self.ansi_height)
        remaining = self.ansi_text[self.playback_position:]
        self.stream_parser.feed(remaining)
        self.playback_position = len(self.ansi_text)
        self.viewer.set_screen(self.stream_parser.cells, self.ansi_width, self.ansi_height)
        self.stop_playback()

    def playback_tick(self):
        if not self.is_playing or self.stream_parser is None:
            return

        baud = self.speed_combo.currentData()
        if baud == 0:
            self.finish_instantly()
            return

        # Serial links conventionally use roughly 10 transmitted bits per byte
        # (start bit + 8 data bits + stop bit), so baud / 10 approximates CPS.
        chars_per_second = baud / 10.0
        self.playback_remainder += chars_per_second * (self.playback_timer.interval() / 1000.0)
        count = int(self.playback_remainder)
        if count < 1:
            return
        self.playback_remainder -= count

        end = min(len(self.ansi_text), self.playback_position + count)
        self.stream_parser.feed(self.ansi_text[self.playback_position:end])
        self.playback_position = end
        self.viewer.set_screen(self.stream_parser.cells, self.ansi_width, self.ansi_height)

        if self.playback_position >= len(self.ansi_text):
            self.stop_playback()

    def playback_speed_changed(self):
        if not self.ansi_text:
            return
        if self.speed_combo.currentData() == 0:
            self.finish_instantly()
        elif self.is_playing:
            self.playback_remainder = 0.0

    def previous_ansi(self):
        if not self.current_file or not self.ansi_files:
            return

        try:
            current_index = self.ansi_files.index(self.current_file)
        except ValueError:
            return

        previous_index = (current_index - 1) % len(self.ansi_files)
        self.load_ansi(self.ansi_files[previous_index])

    def next_ansi(self):
        if not self.current_file or not self.ansi_files:
            return

        try:
            current_index = self.ansi_files.index(self.current_file)
        except ValueError:
            return

        next_index = (current_index + 1) % len(self.ansi_files)
        self.load_ansi(self.ansi_files[next_index])

def main():
    app = QApplication(sys.argv)

    window = ReelANSI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
