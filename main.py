#!/usr/bin/env python3
"""Noctalia Widget Manager.

View and reorder the bar widgets (left / center / right) in Noctalia's
settings.json. Changes are written back with a backup taken first.
"""

import json
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

CONFIG_PATH = Path.home() / ".config/noctalia/settings.json"
BACKUP_PATH = CONFIG_PATH.with_suffix(".json.bak")
SECTIONS = ["left", "center", "right"]
SECTION_TITLES = {"left": "Left", "center": "Center", "right": "Right"}


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(path, data):
    if path.exists():
        shutil.copy2(path, BACKUP_PATH)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


class SectionPanel(QFrame):
    def __init__(self, title, move_cb, parent=None):
        super().__init__(parent)
        self.move_cb = move_cb

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel(title)
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.DragDrop)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setAlternatingRowColors(True)
        layout.addWidget(self.list)

        buttons = QHBoxLayout()
        buttons.setSpacing(4)
        self.up_btn = self._button("Up", "▲", lambda: self.move_cb("up"))
        self.down_btn = self._button("Down", "▼", lambda: self.move_cb("down"))
        self.left_btn = self._button("To Left", "◀", lambda: self.move_cb("left"))
        self.right_btn = self._button("To Right", "▶", lambda: self.move_cb("right"))
        buttons.addWidget(self.up_btn)
        buttons.addWidget(self.down_btn)
        buttons.addWidget(self.left_btn)
        buttons.addWidget(self.right_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _button(self, tooltip, glyph, handler):
        btn = QPushButton(glyph)
        btn.setToolTip(tooltip)
        btn.setFixedWidth(40)
        btn.clicked.connect(handler)
        return btn


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Noctalia Widget Manager")
        self.resize(780, 460)

        self.data = None
        self.path = CONFIG_PATH

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        rows = QHBoxLayout()
        rows.setSpacing(10)
        self.panels = []
        for i, section in enumerate(SECTIONS):
            panel = SectionPanel(SECTION_TITLES[section], lambda action, idx=i: self._move(idx, action))
            panel.left_btn.setEnabled(i > 0)
            panel.right_btn.setEnabled(i < len(SECTIONS) - 1)
            panel.list.model().rowsInserted.connect(lambda *_, p=panel: self._sync_panel_buttons(p))
            panel.list.model().rowsRemoved.connect(lambda *_, p=panel: self._sync_panel_buttons(p))
            self.panels.append(panel)
            rows.addWidget(panel, 1)
        outer.addLayout(rows, 1)

        actions = QHBoxLayout()
        reload_btn = QPushButton("Reload from Disk")
        reload_btn.clicked.connect(self.reload)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save)
        actions.addStretch()
        actions.addWidget(reload_btn)
        actions.addWidget(save_btn)
        outer.addLayout(actions)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("")

        self.load()

    # ---- loading / saving -------------------------------------------------

    def load(self):
        try:
            self.data = load_config(self.path)
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"Config not found:\n{self.path}")
            return
        except json.JSONDecodeError as exc:
            QMessageBox.critical(self, "Error", f"Invalid JSON in {self.path}:\n{exc}")
            return

        widgets = self.data.get("bar", {}).get("widgets", {})
        for i, section in enumerate(SECTIONS):
            self.panels[i].list.clear()
            for entry in widgets.get(section, []):
                self._add_item(self.panels[i].list, entry)
        self.statusBar().showMessage(f"Loaded {self.path}", 4000)

    def reload(self):
        self.load()

    def save(self):
        if self.data is None:
            return
        widgets = self.data.setdefault("bar", {}).setdefault("widgets", {})
        for i, section in enumerate(SECTIONS):
            widgets[section] = [self._item_payload(self.panels[i].list.item(r))
                                for r in range(self.panels[i].list.count())]
        try:
            save_config(self.path, self.data)
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Could not write {self.path}:\n{exc}")
            return
        self.statusBar().showMessage(
            f"Saved (backup written to {BACKUP_PATH.name})", 6000)

    # ---- item helpers -----------------------------------------------------

    def _add_item(self, lst, entry):
        widget_id = entry.get("id", "?")
        item = QListWidgetItem(widget_id)
        item.setData(Qt.ItemDataRole.UserRole, entry)
        item.setToolTip(self._describe(entry))
        lst.addItem(item)

    @staticmethod
    def _item_payload(item):
        if item is None:
            return None
        payload = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(payload, dict):
            return payload
        return {"id": item.text()}

    @staticmethod
    def _describe(entry):
        if entry.get("id", "").startswith("plugin:"):
            return f"Plugin widget: {entry['id'][7:]}"
        return entry.get("id", "")

    # ---- reordering -------------------------------------------------------

    def _move(self, section_idx, action):
        lst = self.panels[section_idx].list
        row = lst.currentRow()
        if row < 0:
            self.statusBar().showMessage("Select a widget first", 2500)
            return

        if action == "up" and row > 0:
            item = lst.takeItem(row)
            lst.insertItem(row - 1, item)
            lst.setCurrentRow(row - 1)
        elif action == "down" and row < lst.count() - 1:
            item = lst.takeItem(row)
            lst.insertItem(row + 1, item)
            lst.setCurrentRow(row + 1)
        elif action == "left" and section_idx > 0:
            self._move_across(section_idx, section_idx - 1)
        elif action == "right" and section_idx < len(SECTIONS) - 1:
            self._move_across(section_idx, section_idx + 1)

    def _move_across(self, src_idx, dst_idx):
        src = self.panels[src_idx].list
        dst = self.panels[dst_idx].list
        row = src.currentRow()
        item = src.takeItem(row)
        dst.addItem(item)
        dst.setCurrentItem(item)

    def _sync_panel_buttons(self, panel):
        lst = panel.list
        has_items = lst.count() > 0
        panel.up_btn.setEnabled(has_items)
        panel.down_btn.setEnabled(has_items)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
