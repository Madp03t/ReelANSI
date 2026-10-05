import os 
import sys
import re

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QScrollArea,
)
from PySide6.QtCore import Qt
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

def parse_ansi(text, fixed_width=80):
    text = text.replace("\x00", " ")
    pattern = re.compile(r"(\x1b\[[0-9;]*[A-Za-z])")
    parts = pattern.split(text)

    y, x = 0, 0
    current_fg, current_bg = 7, 0
    lines = {}

    for part in parts:
        if not part:
            continue

        if part.startswith("\x1b["):
            match = re.match(r"\x1b\[([0-9;]*)([A-Za-z])", part)
            if not match:
                continue

            params, cmd = match.groups()
            nums = [int(n) for n in params.split(";") if n] if params else []

            if cmd == "m":
                for n in nums or [0]:
                    if n == 0:
                        current_fg, current_bg = 7, 0
                    elif n == 1:
                        if current_fg < 8:
                            current_fg += 8
                    elif 30 <= n <= 37:
                        current_fg = n - 30
                    elif 40 <= n <= 47:
                        current_bg = n - 40

            elif cmd == "H" and len(nums) >= 2:
                y, x = nums[0] - 1, nums[1] - 1

            elif cmd == "A":
                y = max(0, y - (nums[0] if nums else 1))

            elif cmd == "B":
                y += nums[0] if nums else 1

            elif cmd == "C":
                x += nums[0] if nums else 1

            elif cmd == "D":
                x = max(0, x - (nums[0] if nums else 1))

            continue

        for ch in part:
            if ch == "\n":
                y += 1
                x = 0
                continue

            if x >= fixed_width:
                y += 1
                x = 0

            lines.setdefault(y, []).append((x, ch, current_fg, current_bg))
            x += 1

    return lines

class ANSIViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.lines = {}
        self.cell_width = 9
        self.cell_height = 16

        font_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "fonts",
            "Px437_IBM_VGA_9x16.ttf",
        )

        font_id = QFontDatabase.addApplicationFont(font_path)
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

        self.font = QFont(font_family)
        self.font.setPixelSize(16)

    def set_ansi(self, lines):
        self.lines = lines

        if lines:
            width = max(
                (x for cells in lines.values() for x, *_ in cells),
                default=0,
            ) + 1
            height = max(lines.keys()) + 1

            self.setFixedSize(
                width * self.cell_width,
                height * self.cell_height,
            )

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
        painter.setFont(self.font)

        for y, cells in self.lines.items():
            for x, ch, fg, bg in cells:
                fg_color = QColor(*VGA_COLORS[fg])
                bg_color = QColor(*VGA_COLORS[bg])

                left = x * self.cell_width
                top = y * self.cell_height

                painter.fillRect(
                    left,
                    top,
                    self.cell_width,
                    self.cell_height,
                    bg_color,
                )

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

        file_menu = self.menuBar().addMenu("&File")

        open_action = QAction("&Open ANSI...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_ansi)
        file_menu.addAction(open_action)

        self.setWindowTitle("ReelANSI v0.1  •  by Madp03t")
        self.resize(1000, 700)

        container = QWidget()
        layout = QVBoxLayout(container)

        self.viewer = ANSIViewer()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.viewer)
        self.scroll_area.setWidgetResizable(False)

        layout.addWidget(self.scroll_area, 1)
        self.file_info = QLabel("No file open")
        layout.addWidget(self.file_info)

        self.setCentralWidget(container)

    def open_ansi(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open ANSI File",
            "",
            "ANSI Files (*.ans *.ANS)",
        )

        if filename:
            with open(filename, "rb") as file:
                ansi_data = file.read()
            sauce = read_sauce(ansi_data)
            print(f"SAUCE: {sauce}")

            print(f"Read {len(ansi_data)} bytes from {filename}")
            print(repr(ansi_data[:200]))
            sauce_position = ansi_data.rfind(b"SAUCE00")
            ansi_content = ansi_data[:sauce_position] if sauce_position != -1 else ansi_data
            ansi_content = ansi_content.rstrip(b"\x1a")
            print(f"ANSI content: {len(ansi_content)} bytes")
            decoded = ansi_content.decode("cp437")
            print(decoded)
            width = sauce["width"] if sauce else 80
            parsed = parse_ansi(decoded, width)
            print(f"Parsed ANSI: {parsed}")
            self.viewer.set_ansi(parsed)
            name = os.path.basename(filename)
            height = sauce["height"] if sauce else len(parsed)
            self.file_info.setText(f"{name}   •   {width} × {height}")
            print(f"SAUCE starts at byte: {sauce_position}")


def main():
    app = QApplication(sys.argv)

    window = ReelANSI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
