#!/usr/bin/env python3
"""Steam Account Switcher — PyQt6 Desktop GUI"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QRect, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QFontMetrics, QIcon, QPainter, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# ── Constants ──────────────────────────────────────────────────────────────────

APP_NAME = "Steam Account Switcher"
APP_VERSION = "2.0.0"
CONFIG_DIR = Path.home() / ".config" / "steam-account-switcher"
CONFIG_FILE = CONFIG_DIR / "config.json"
VDF_CANDIDATES = [
    Path.home() / ".steam/root/config/loginusers.vdf",
    Path.home() / ".local/share/Steam/config/loginusers.vdf",
]
DEFAULT_ALIAS_FILE = Path.home() / "Documents/Tools/Scripts/aliases.conf"

ROLE_ACCOUNT = Qt.ItemDataRole.UserRole
ROLE_ACCOUNT_NAME = Qt.ItemDataRole.UserRole + 1
ROLE_IS_RECENT = Qt.ItemDataRole.UserRole + 2


# ── VDF Parser ─────────────────────────────────────────────────────────────────

def parse_loginusers(vdf_path: Path) -> list[dict]:
    """Extract accounts from Steam's loginusers.vdf."""
    try:
        text = vdf_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    accounts = []
    for steam_id, block in re.findall(r'"(\d+)"\s*\{([^}]+)\}', text, re.DOTALL):
        acct = re.search(r'"AccountName"\s+"([^"]+)"', block)
        persona = re.search(r'"PersonaName"\s+"([^"]+)"', block)
        recent = re.search(r'"MostRecent"\s+"([^"]+)"', block)
        if acct:
            accounts.append({
                "steam_id": steam_id,
                "account_name": acct.group(1),
                "persona_name": persona.group(1) if persona else acct.group(1),
                "most_recent": recent.group(1) == "1" if recent else False,
            })
    return accounts


# ── Alias Manager ──────────────────────────────────────────────────────────────

class AliasManager:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, str] = {}
        self.reload()

    def reload(self):
        self._data = {}
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key, sep, val = stripped.partition("=")
            if sep and key.strip():
                self._data[key.strip()] = val

    def get(self, persona: str) -> str:
        return self._data.get(persona, persona)

    def all_entries(self) -> list[tuple[str, str]]:
        return list(self._data.items())

    def set_alias(self, persona: str, label: str):
        if label:
            self._data[persona] = label
        else:
            self._data.pop(persona, None)

    def remove(self, persona: str):
        self._data.pop(persona, None)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Steam Account Aliases\n",
            "# Format: PersonaName=Friendly Label\n",
            "#\n",
        ]
        lines.extend(f"{k}={v}\n" for k, v in self._data.items())
        self.path.write_text("".join(lines), encoding="utf-8")


# ── App Config ─────────────────────────────────────────────────────────────────

class Config:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._d: dict = {
            "vdf_path": str(next((p for p in VDF_CANDIDATES if p.exists()), VDF_CANDIDATES[0])),
            "alias_file": str(DEFAULT_ALIAS_FILE),
        }
        if CONFIG_FILE.exists():
            try:
                self._d.update(json.loads(CONFIG_FILE.read_text()))
            except Exception:
                pass

    def save(self):
        CONFIG_FILE.write_text(json.dumps(self._d, indent=2))

    @property
    def vdf_path(self) -> Path:
        return Path(self._d["vdf_path"])

    @vdf_path.setter
    def vdf_path(self, v: Path):
        self._d["vdf_path"] = str(v)

    @property
    def alias_file(self) -> Path:
        return Path(self._d["alias_file"])

    @alias_file.setter
    def alias_file(self, v: Path):
        self._d["alias_file"] = str(v)


# ── Steam Helpers ──────────────────────────────────────────────────────────────

def steam_running() -> bool:
    return subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0


# ── Switch Worker Thread ───────────────────────────────────────────────────────

class SwitchWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, account_name: str):
        super().__init__()
        self.account_name = account_name

    def run(self):
        self.progress.emit("Stopping Steam…")
        subprocess.run(["pkill", "-x", "steam"], capture_output=True)
        subprocess.run(["pkill", "-x", "steam.sh"], capture_output=True)
        deadline = time.monotonic() + 15
        while steam_running() and time.monotonic() < deadline:
            time.sleep(0.5)
        if steam_running():
            self.finished.emit(False, "Steam did not stop within 15 s.")
            return
        self.progress.emit(f"Launching as {self.account_name}…")
        subprocess.Popen(
            ["steam", "-login", self.account_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        self.finished.emit(True, f"Switched to  {self.account_name}")


# ── Account List Delegate ──────────────────────────────────────────────────────

class AccountDelegate(QStyledItemDelegate):
    """Draws two-line account rows: alias name (bold) + account name (muted)."""

    ROW_H = 62

    def sizeHint(self, option, index) -> QSize:
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter: QPainter, option, index):
        painter.save()
        self.initStyleOption(option, index)

        style = option.widget.style() if option.widget else QApplication.style()
        # PE_PanelItemViewItem draws only the selection/hover background.
        # CE_ItemViewItem would also render DisplayRole text, doubling it
        # on top of the custom drawing below.
        style.drawPrimitive(
            QStyle.PrimitiveElement.PE_PanelItemViewItem, option, painter, option.widget
        )

        label: str = index.data(Qt.ItemDataRole.DisplayRole) or ""
        account_name: str = index.data(ROLE_ACCOUNT_NAME) or ""
        is_recent: bool = bool(index.data(ROLE_IS_RECENT))
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)

        pal = option.palette
        if is_selected:
            primary_color = pal.color(QPalette.ColorRole.HighlightedText)
            secondary_color = pal.color(QPalette.ColorRole.HighlightedText)
            secondary_color.setAlphaF(0.65)
        else:
            primary_color = pal.color(QPalette.ColorRole.Text)
            secondary_color = pal.color(QPalette.ColorRole.PlaceholderText)

        badge_w = 58 if is_recent else 0
        rect = option.rect.adjusted(14, 0, -(12 + badge_w), 0)

        f1 = QFont(option.font)
        f1.setPointSize(10)
        f1.setBold(True)
        fm1 = QFontMetrics(f1)

        f2 = QFont(option.font)
        f2.setPointSize(8)
        fm2 = QFontMetrics(f2)

        block_h = fm1.height() + 4 + fm2.height()
        top = option.rect.top() + (option.rect.height() - block_h) // 2

        painter.setFont(f1)
        painter.setPen(primary_color)
        painter.drawText(
            QRect(rect.left(), top, rect.width(), fm1.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            label,
        )

        painter.setFont(f2)
        painter.setPen(secondary_color)
        painter.drawText(
            QRect(rect.left(), top + fm1.height() + 4, rect.width(), fm2.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            account_name,
        )

        if is_recent:
            f3 = QFont(option.font)
            f3.setPointSize(7)
            badge_color = pal.color(QPalette.ColorRole.Highlight)
            # Anchor from the right edge of the full item rect so it never clips
            badge_rect = QRect(
                option.rect.right() - badge_w,
                option.rect.center().y() - 9,
                badge_w - 6,
                18,
            )
            painter.setFont(f3)
            painter.setPen(badge_color)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, "Recent")

        painter.restore()


# ── Alias Editor ───────────────────────────────────────────────────────────────

class AliasEditorDialog(QDialog):
    def __init__(self, alias_manager: AliasManager, accounts: list[dict], parent=None):
        super().__init__(parent)
        self.alias_manager = alias_manager
        self.accounts = accounts
        self.setWindowTitle("Manage Aliases")
        self.setMinimumSize(540, 400)
        self._build()
        self._populate()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info = QLabel(
            "Map Steam PersonaNames to friendly display labels. Emoji are supported."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["PersonaName (from Steam)", "Display Label"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Add Row")
        del_btn = QPushButton("− Delete Selected")
        add_btn.clicked.connect(self._add_row)
        del_btn.clicked.connect(self._del_row)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def _populate(self):
        existing = {p for p, _ in self.alias_manager.all_entries()}
        for persona, label in self.alias_manager.all_entries():
            self._append_row(persona, label)
        for acc in self.accounts:
            if acc["persona_name"] not in existing:
                self._append_row(acc["persona_name"], "")

    def _append_row(self, persona: str, label: str):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(persona))
        self.table.setItem(r, 1, QTableWidgetItem(label))

    def _add_row(self):
        self._append_row("", "")
        self.table.scrollToBottom()
        self.table.setCurrentCell(self.table.rowCount() - 1, 0)
        self.table.editItem(self.table.currentItem())

    def _del_row(self):
        rows = sorted({i.row() for i in self.table.selectedItems()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _save(self):
        for persona, _ in list(self.alias_manager.all_entries()):
            self.alias_manager.remove(persona)
        for r in range(self.table.rowCount()):
            p_item = self.table.item(r, 0)
            l_item = self.table.item(r, 1)
            persona = p_item.text().strip() if p_item else ""
            label = l_item.text().strip() if l_item else ""
            if persona:
                self.alias_manager.set_alias(persona, label)
        self.alias_manager.save()
        self.accept()


# ── Settings Dialog ────────────────────────────────────────────────────────────

class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self._build()

    def _build(self):
        form = QFormLayout(self)
        form.setSpacing(10)
        form.setContentsMargins(16, 16, 16, 16)

        vdf_row = QHBoxLayout()
        self.vdf_edit = QLineEdit(str(self.config.vdf_path))
        vdf_btn = QPushButton("Browse…")
        vdf_btn.clicked.connect(
            lambda: self._browse(self.vdf_edit, "VDF files (*.vdf);;All files (*)")
        )
        vdf_row.addWidget(self.vdf_edit)
        vdf_row.addWidget(vdf_btn)
        form.addRow("loginusers.vdf:", vdf_row)

        alias_row = QHBoxLayout()
        self.alias_edit = QLineEdit(str(self.config.alias_file))
        alias_btn = QPushButton("Browse…")
        alias_btn.clicked.connect(
            lambda: self._browse(self.alias_edit, "Config files (*.conf);;All files (*)")
        )
        alias_row.addWidget(self.alias_edit)
        alias_row.addWidget(alias_btn)
        form.addRow("aliases.conf:", alias_row)

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self._ok)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def _browse(self, edit: QLineEdit, filt: str):
        p, _ = QFileDialog.getOpenFileName(self, "Select file", str(Path.home()), filt)
        if p:
            edit.setText(p)

    def _ok(self):
        self.config.vdf_path = Path(self.vdf_edit.text())
        self.config.alias_file = Path(self.alias_edit.text())
        self.config.save()
        self.accept()


# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.aliases = AliasManager(self.config.alias_file)
        self.accounts: list[dict] = []
        self.worker: SwitchWorker | None = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(400, 500)
        self.resize(440, 580)

        self._build_ui()
        self._build_menu()
        self._build_tray()

        self._steam_timer = QTimer(self)
        self._steam_timer.timeout.connect(self._refresh_steam_status)
        self._steam_timer.start(3000)

        self._reload()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 10, 16, 10)

        title_col = QVBoxLayout()
        title = QLabel(APP_NAME)
        tf = title.font()
        tf.setPointSize(12)
        tf.setBold(True)
        title.setFont(tf)
        sub = QLabel("Select an account to switch")
        sf = sub.font()
        sf.setPointSize(8)
        sub.setFont(sf)
        sub.setObjectName("subtitle")
        title_col.addWidget(title)
        title_col.addWidget(sub)

        self.status_pill = QLabel("● Checking…")
        self.status_pill.setObjectName("statusOff")
        self.status_pill.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        pf = self.status_pill.font()
        pf.setPointSize(9)
        self.status_pill.setFont(pf)

        hl.addLayout(title_col)
        hl.addStretch()
        hl.addWidget(self.status_pill)
        vbox.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        vbox.addWidget(sep)

        # Body
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.setSpacing(8)

        # Top row: "Accounts" label + refresh button
        top_row = QHBoxLayout()
        acc_lbl = QLabel("Accounts")
        af = acc_lbl.font()
        af.setBold(True)
        af.setPointSize(9)
        acc_lbl.setFont(af)
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setFixedSize(28, 28)
        self.refresh_btn.setToolTip("Reload accounts from Steam")
        self.refresh_btn.clicked.connect(self._reload)
        top_row.addWidget(acc_lbl)
        top_row.addStretch()
        top_row.addWidget(self.refresh_btn)
        bl.addLayout(top_row)

        # Account list
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("accountList")
        self.list_widget.setItemDelegate(AccountDelegate(self.list_widget))
        self.list_widget.setSpacing(2)
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.itemDoubleClicked.connect(self._switch)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        bl.addWidget(self.list_widget)

        # Empty state
        self.empty_lbl = QLabel(
            "No accounts found.\nVerify your Steam installation or update Settings."
        )
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setObjectName("emptyLabel")
        self.empty_lbl.hide()
        bl.addWidget(self.empty_lbl)

        # Secondary actions row
        sec_row = QHBoxLayout()
        self.alias_btn = QPushButton("✏  Manage Aliases")
        self.settings_btn_w = QPushButton("⚙  Settings")
        self.alias_btn.clicked.connect(self._open_aliases)
        self.settings_btn_w.clicked.connect(self._open_settings)
        sec_row.addWidget(self.alias_btn)
        sec_row.addWidget(self.settings_btn_w)
        bl.addLayout(sec_row)

        # Primary switch button
        self.switch_btn = QPushButton("Switch Account")
        self.switch_btn.setObjectName("switchBtn")
        self.switch_btn.setMinimumHeight(42)
        self.switch_btn.setEnabled(False)
        self.switch_btn.clicked.connect(self._switch)
        bl.addWidget(self.switch_btn)

        vbox.addWidget(body)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    def _build_menu(self):
        mb = self.menuBar()

        fm = mb.addMenu("&File")
        qa = QAction("&Quit", self)
        qa.setShortcut("Ctrl+Q")
        qa.triggered.connect(QApplication.quit)
        fm.addAction(qa)

        em = mb.addMenu("&Edit")
        aa = QAction("Manage &Aliases…", self)
        aa.triggered.connect(self._open_aliases)
        sa = QAction("&Settings…", self)
        sa.triggered.connect(self._open_settings)
        em.addAction(aa)
        em.addSeparator()
        em.addAction(sa)

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        icon = QIcon.fromTheme("steam")
        if icon.isNull():
            icon = QIcon.fromTheme("applications-games")
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray.setIcon(icon)
        self.tray.setToolTip(APP_NAME)

        m = QMenu()
        show_act = QAction("Show", self)
        show_act.triggered.connect(self._tray_toggle)
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(QApplication.quit)
        m.addAction(show_act)
        m.addSeparator()
        m.addAction(quit_act)
        self.tray.setContextMenu(m)
        self.tray.activated.connect(
            lambda r: self._tray_toggle()
            if r == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        self.tray.show()

    # ── Data ───────────────────────────────────────────────────────────────────

    def _reload(self):
        self.aliases = AliasManager(self.config.alias_file)
        self.accounts = parse_loginusers(self.config.vdf_path)
        self.list_widget.clear()

        if not self.accounts:
            self.list_widget.hide()
            self.empty_lbl.show()
            self.switch_btn.setEnabled(False)
            self.statusBar().showMessage("No accounts found — check Settings")
            return

        self.empty_lbl.hide()
        self.list_widget.show()

        for acc in self.accounts:
            label = self.aliases.get(acc["persona_name"])
            item = QListWidgetItem(label)
            item.setData(ROLE_ACCOUNT, acc)
            item.setData(ROLE_ACCOUNT_NAME, acc["account_name"])
            item.setData(ROLE_IS_RECENT, acc["most_recent"])
            self.list_widget.addItem(item)

        self.statusBar().showMessage(f"{len(self.accounts)} account(s) loaded")
        self._refresh_steam_status()

    def _refresh_steam_status(self):
        running = steam_running()
        if running:
            self.status_pill.setText("● Steam: Running")
            self.status_pill.setObjectName("statusOn")
        else:
            self.status_pill.setText("● Steam: Stopped")
            self.status_pill.setObjectName("statusOff")
        # Force Qt to re-apply the objectName-based style
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    # ── Actions ─────────────────────────────────────────────────────────────────

    def _on_selection_changed(self):
        has_selection = len(self.list_widget.selectedItems()) > 0
        self.switch_btn.setEnabled(has_selection and not self._is_busy())

    def _is_busy(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def _switch(self):
        items = self.list_widget.selectedItems()
        if not items:
            return
        acc = items[0].data(ROLE_ACCOUNT)
        label = self.aliases.get(acc["persona_name"])

        answer = QMessageBox.question(
            self,
            "Switch Account",
            f"Switch to <b>{label}</b><br>"
            f"<small style='color:gray'>({acc['account_name']})</small><br><br>"
            "Steam will be closed and relaunched.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._set_busy(True)
        self.worker = SwitchWorker(acc["account_name"])
        self.worker.progress.connect(self.statusBar().showMessage)
        self.worker.finished.connect(self._on_switched)
        self.worker.start()

    def _on_switched(self, ok: bool, msg: str):
        self._set_busy(False)
        self.statusBar().showMessage(msg)
        if not ok:
            QMessageBox.warning(self, "Switch Failed", msg)

    def _set_busy(self, busy: bool):
        for w in (self.alias_btn, self.settings_btn_w, self.refresh_btn):
            w.setEnabled(not busy)
        self.switch_btn.setText("Switching…" if busy else "Switch Account")
        if not busy:
            self._on_selection_changed()
        else:
            self.switch_btn.setEnabled(False)

    def _open_aliases(self):
        d = AliasEditorDialog(self.aliases, self.accounts, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            self._reload()

    def _open_settings(self):
        d = SettingsDialog(self.config, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.aliases = AliasManager(self.config.alias_file)
            self._reload()

    # ── Tray / Window ──────────────────────────────────────────────────────────

    def _tray_toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(
            APP_NAME,
            "Running in the system tray.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )


# ── Stylesheet ─────────────────────────────────────────────────────────────────
# Uses palette() references so it inherits KDE's Breeze/Breeze Dark colour scheme.

QSS = """
#header {
    background-color: palette(base);
}

#subtitle {
    color: palette(mid);
}

#statusOn {
    color: #27ae60;
    font-weight: bold;
}

#statusOff {
    color: palette(mid);
}

#accountList {
    border: 1px solid palette(mid);
    border-radius: 6px;
    background-color: palette(base);
    outline: none;
}

#accountList::item {
    border-radius: 4px;
}

#accountList::item:selected {
    background-color: palette(highlight);
    color: palette(highlighted-text);
}

#accountList::item:hover:!selected {
    background-color: palette(alternate-base);
}

#switchBtn {
    background-color: palette(highlight);
    color: palette(highlighted-text);
    border: none;
    border-radius: 6px;
    font-size: 11pt;
    font-weight: bold;
}

#switchBtn:disabled {
    background-color: palette(mid);
    color: palette(dark);
}

#switchBtn:hover:!disabled {
    background-color: palette(light);
    color: palette(text);
}

#emptyLabel {
    color: palette(mid);
    font-size: 10pt;
}
"""


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("steam-account-switcher")
    app.setStyleSheet(QSS)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
