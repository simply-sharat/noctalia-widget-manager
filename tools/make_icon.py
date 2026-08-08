#!/usr/bin/env python3
"""Render the app icon (three columns: left / center / right) to PNG."""

import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPen

SIZE = 256
OUT = Path(__file__).resolve().parent.parent / "data" / "noctalia-widget-manager.png"


def main():
    app = QGuiApplication(sys.argv)

    img = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    bg = QRectF(8, 8, SIZE - 16, SIZE - 16)
    grad = QLinearGradient(bg.topLeft(), bg.bottomRight())
    grad.setColorAt(0.0, QColor("#2a3140"))
    grad.setColorAt(1.0, QColor("#0e1117"))
    p.setPen(QPen(QColor("#3b4252"), 3))
    p.setBrush(grad)
    p.drawRoundedRect(bg, 34, 34)

    for x, color in ((36, "#4c8bf5"), (106, "#6be1a2"), (176, "#f5a14c")):
        col = QRectF(x, 64, 44, 128)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(color))
        p.drawRoundedRect(col, 12, 12)

    p.end()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not img.save(str(OUT)):
        print("failed to write icon", file=sys.stderr)
        return 1
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
