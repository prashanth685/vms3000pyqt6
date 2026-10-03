"""
icons.py — VMS 3000 full-color toolbar icon painter

Requires:
    PyQt6

Font:
    MaterialIcons-Regular.ttf

Place the font in either:
    ./MaterialIcons-Regular.ttf
or:
    ./icons/MaterialIcons-Regular.ttf

Design:
    Every toolbar icon has its own color.

    New          -> Violet
    Open         -> Amber
    Save         -> Green
    Print        -> Slate
    Settings     -> Blue
    Cut          -> Orange
    Copy         -> Indigo
    Paste        -> Teal
    Upload       -> Cyan
    Download     -> Blue
    Refresh      -> Sky
    Security     -> Purple
    Help         -> Blue
    Connection   -> Emerald
    Network      -> Cyan
    Disconnect   -> Red

Supports:
    normal
    hover
    active
    disabled

And connection/status states:
    connected
    connecting
    warning
    error
"""


import os
from typing import Optional

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QColor, QFont, QFontDatabase, QGuiApplication, QIcon, QPainter, QPixmap,
)


# ============================================================================
# MATERIAL ICON CODEPOINTS
# ============================================================================

_CODEPOINTS: dict[str, str] = {

    # ------------------------------------------------------------------------
    # Files / documents
    # ------------------------------------------------------------------------

    "add":            "\ue145",
    "note_add":       "\ue89c",
    "description":    "\ue873",
    "folder_open":    "\ue2c7",
    "save":           "\ue161",
    "print":          "\ue8ad",

    # ------------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------------

    "content_cut":    "\ue14e",
    "content_copy":   "\ue14d",
    "content_paste":  "\ue14f",

    # ------------------------------------------------------------------------
    # Transfer
    # ------------------------------------------------------------------------

    "upload":         "\ue2c6",
    "download":       "\ue2c4",

    # ------------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------------

    "refresh":        "\ue5d5",
    "settings":       "\ue8b8",
    "help":           "\ue887",

    # ------------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------------

    "vpn_key":        "\ue0da",

    # ------------------------------------------------------------------------
    # Network / connection
    # ------------------------------------------------------------------------

    "router":         "\ue328",
    "device_hub":     "\ue335",
    "wifi":           "\ue1e9",
    "link":           "\ue157",
    "link_off":       "\ue157",

    # ------------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------------

    "check":          "\ue5ca",
    "close":          "\ue5cd",
    "warning":        "\ue002",
    "error":          "\ue000",
    "info":           "\ue88e",
}


# ============================================================================
# TOOLBAR ICON MAP
# ============================================================================

_ICON_MAP: dict[str, str] = {

    "new":          "note_add",
    "open":         "folder_open",
    "save":         "save",
    "print":        "print",

    "settings":     "settings",
    "help":         "help",

    "cut":          "content_cut",
    "copy":         "content_copy",
    "paste":        "content_paste",

    "upload":       "upload",
    "download":     "download",

    "refresh":      "refresh",

    "key":          "vpn_key",

    "connection":   "router",
    "network":      "wifi",
    "disconnect":   "link_off",

    "connected":    "check",
    "connecting":   "refresh",
    "warning":      "warning",
    "error":        "error",
    "info":         "info",
}


# ============================================================================
# VMS 3000 UI COLORS
# ============================================================================

# Toolbar background
_DEFAULT_BG = "#F4F6F9"


# ---------------------------------------------------------------------------
# Individual icon colors
# ---------------------------------------------------------------------------

_ICON_COLORS: dict[str, str] = {

    # File / document
    "new":          "#7C3AED",     # Violet
    "open":         "#D97706",     # Amber
    "save":         "#16A34A",     # Green
    "print":        "#475569",     # Slate

    # System
    "settings":     "#2563EB",     # Blue
    "help":         "#0284C7",     # Sky blue
    "refresh":      "#0EA5E9",     # Cyan / sky

    # Editing
    "cut":          "#EA580C",     # Orange
    "copy":         "#4F46E5",     # Indigo
    "paste":        "#0D9488",     # Teal

    # Transfer
    "upload":       "#0891B2",     # Cyan
    "download":     "#2563EB",     # Blue

    # Security
    "key":          "#9333EA",     # Purple

    # Network
    "connection":   "#059669",     # Emerald
    "network":      "#0284C7",     # Sky
    "disconnect":   "#DC2626",     # Red

    # Status
    "connected":    "#16A34A",     # Green
    "connecting":   "#F59E0B",     # Amber
    "warning":      "#F59E0B",     # Amber
    "error":        "#DC2626",     # Red
    "info":         "#2563EB",     # Blue
}


# ---------------------------------------------------------------------------
# State colors
# ---------------------------------------------------------------------------

_HOVER_LIGHTEN = {
    "#7C3AED": "#8B5CF6",
    "#D97706": "#F59E0B",
    "#16A34A": "#22C55E",
    "#475569": "#64748B",
    "#2563EB": "#3B82F6",
    "#0284C7": "#0EA5E9",
    "#0EA5E9": "#38BDF8",
    "#EA580C": "#F97316",
    "#4F46E5": "#6366F1",
    "#0D9488": "#14B8A6",
    "#0891B2": "#06B6D4",
    "#9333EA": "#A855F7",
    "#059669": "#10B981",
    "#DC2626": "#EF4444",
    "#F59E0B": "#FBBF24",
}


_DISABLED_COLOR = "#CBD5E1"

_ACTIVE_COLOR = "#1E40AF"


# ============================================================================
# FONT SEARCH
# ============================================================================

_FONT_FAMILY: Optional[str] = None
_FONT_TRIED = False


def _font_candidates() -> list:
    """Common locations for MaterialIcons-Regular.ttf."""

    base_dir = os.path.dirname(os.path.abspath(__file__))

    return [
        # Same directory
        os.path.join(base_dir, "MaterialIcons-Regular.ttf"),

        # icons sub-folder
        os.path.join(base_dir, "icons", "MaterialIcons-Regular.ttf"),

        # Current working directory
        "MaterialIcons-Regular.ttf",

        # Windows
        r"C:\Windows\Fonts\MaterialIcons-Regular.ttf",

        # Linux
        "/usr/share/fonts/truetype/material-design-icons/"
        "MaterialIcons-Regular.ttf",
        "/usr/share/fonts/MaterialIcons-Regular.ttf",

        # macOS
        "/Library/Fonts/MaterialIcons-Regular.ttf",
        os.path.expanduser("~/Library/Fonts/MaterialIcons-Regular.ttf"),
    ]


def _find_font_family() -> Optional[str]:
    """
    Register MaterialIcons-Regular.ttf with Qt (once) and return its family
    name, or None when the font could not be found/loaded.

    Must be called after the QGuiApplication exists.
    """
    global _FONT_FAMILY, _FONT_TRIED

    if _FONT_TRIED:
        return _FONT_FAMILY
    _FONT_TRIED = True

    for path in _font_candidates():

        if not os.path.exists(path):
            continue

        font_id = QFontDatabase.addApplicationFont(path)

        if font_id < 0:
            print(f"[WARN] Could not load font '{path}'")
            continue

        families = QFontDatabase.applicationFontFamilies(font_id)

        if families:
            _FONT_FAMILY = families[0]
            print(f"[OK] Material Icons font loaded: {path}")
            return _FONT_FAMILY

    print("[WARN] MaterialIcons-Regular.ttf not found.")
    print("       Put MaterialIcons-Regular.ttf beside icons.py.")
    return None


# ============================================================================
# ICON PAINTER
# ============================================================================

class IconPainter:
    """
    Full-color Material Icon renderer for VMS 3000.

    Example:

        icons = IconPainter()

        pixmap = icons.get("save")          # QPixmap
        button.setIcon(icons.get_icon("save"))   # QIcon
    """

    # Rendered glyph size
    SZ = 26

    # Transparent-looking padding
    PAD = 3

    def __init__(
        self,
        bg_hex: str = _DEFAULT_BG,
        transparent: bool = True,
    ):
        """
        bg_hex       background colour used when transparent=False
        transparent  render on a transparent canvas (default) so hover /
                     pressed button backgrounds show through the icon
        """
        self.bg_hex = bg_hex
        self.transparent = transparent

        self._cache: dict[tuple[str, str], QPixmap] = {}

        self._family = _find_font_family()

        screen = QGuiApplication.primaryScreen()
        self._dpr = screen.devicePixelRatio() if screen is not None else 1.0

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def get(
        self,
        name: str,
        state: str = "normal",
    ) -> QPixmap:
        """
        Return an icon.

        Supported states:

            normal
            hover
            active
            disabled
            connected
            connecting
            warning
            error
            info
        """

        key = (name, state)

        if key not in self._cache:
            self._cache[key] = self._render(name, state)

        return self._cache[key]

    def get_icon(self, name: str) -> QIcon:
        """QIcon with normal / hover(active) / disabled variants."""
        icon = QIcon()
        icon.addPixmap(self.get(name, "normal"), QIcon.Mode.Normal)
        icon.addPixmap(self.get(name, "hover"), QIcon.Mode.Active)
        icon.addPixmap(self.get(name, "disabled"), QIcon.Mode.Disabled)
        return icon

    # ========================================================================
    # SHORTCUTS
    # ========================================================================

    def normal(self, name: str) -> QPixmap:
        return self.get(name, "normal")

    def hover(self, name: str) -> QPixmap:
        return self.get(name, "hover")

    def active(self, name: str) -> QPixmap:
        return self.get(name, "active")

    def disabled(self, name: str) -> QPixmap:
        return self.get(name, "disabled")

    def connected(self, name: str = "connection") -> QPixmap:
        return self.get(name, "connected")

    def connecting(self, name: str = "connection") -> QPixmap:
        return self.get(name, "connecting")

    def warning(self, name: str = "connection") -> QPixmap:
        return self.get(name, "warning")

    def error(self, name: str = "connection") -> QPixmap:
        return self.get(name, "error")

    # ========================================================================
    # RENDER
    # ========================================================================

    def _render(self, name: str, state: str) -> QPixmap:

        # --------------------------------------------------------------------
        # Find codepoint
        # --------------------------------------------------------------------

        cp_key = _ICON_MAP.get(name)

        if cp_key is None:
            print(f"[WARN] Unknown icon: {name}")
            cp_key = "error"

        char = _CODEPOINTS.get(cp_key, _CODEPOINTS["error"])

        # --------------------------------------------------------------------
        # Canvas
        # --------------------------------------------------------------------

        total = self.SZ + self.PAD * 2
        dpr = self._dpr

        pm = QPixmap(int(round(total * dpr)), int(round(total * dpr)))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent if self.transparent
                else QColor(self.bg_hex))

        # --------------------------------------------------------------------
        # Color
        # --------------------------------------------------------------------

        colour = self._get_colour(name, state)

        # --------------------------------------------------------------------
        # Draw
        # --------------------------------------------------------------------

        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        if self._family:
            font = QFont(self._family)
            font.setPixelSize(self.SZ)
            p.setFont(font)
            p.setPen(QColor(colour))
            p.drawText(
                QRectF(0, 0, total, total),
                Qt.AlignmentFlag.AlignCenter,
                char,
            )
        else:
            self._draw_fallback(p, total, colour)

        p.end()

        return pm

    # ========================================================================
    # COLOR SELECTION
    # ========================================================================

    def _get_colour(self, name: str, state: str) -> str:

        state = state.lower().strip()

        # --------------------------------------------------------------------
        # Disabled
        # --------------------------------------------------------------------

        if state == "disabled":
            return _DISABLED_COLOR

        # --------------------------------------------------------------------
        # Connection states
        # --------------------------------------------------------------------

        if state == "connected":
            return "#16A34A"

        if state == "connecting":
            return "#F59E0B"

        if state == "warning":
            return "#F59E0B"

        if state == "error":
            return "#DC2626"

        if state == "info":
            return "#2563EB"

        # --------------------------------------------------------------------
        # Active
        # --------------------------------------------------------------------

        if state == "active":
            return _ACTIVE_COLOR

        # --------------------------------------------------------------------
        # Base icon color
        # --------------------------------------------------------------------

        base_colour = _ICON_COLORS.get(name, "#475569")

        # --------------------------------------------------------------------
        # Hover
        # --------------------------------------------------------------------

        if state == "hover":
            return _HOVER_LIGHTEN.get(base_colour, base_colour)

        # --------------------------------------------------------------------
        # Normal
        # --------------------------------------------------------------------

        return base_colour

    # ========================================================================
    # FALLBACK  (used only when the Material Icons font is unavailable)
    # ========================================================================

    def _draw_fallback(self, painter: QPainter, size: int, colour: str) -> None:

        margin = max(4, size // 4)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colour))
        painter.drawRoundedRect(
            QRectF(margin, margin, size - 2 * margin, size - 2 * margin),
            5, 5,
        )


# ============================================================================
# VMS 3000 TOOLBAR ICON COLLECTION
# ============================================================================

class ToolbarIcons:
    """
    Preloads the complete VMS 3000 colorful toolbar.

    Example:

        icons = ToolbarIcons()

        button.setIcon(QIcon(icons.save))
    """

    def __init__(
        self,
        bg_hex: str = _DEFAULT_BG,
    ):

        self.painter = IconPainter(bg_hex=bg_hex)

        # --------------------------------------------------------------------
        # FILE
        # --------------------------------------------------------------------

        self.new = self.painter.get("new")
        self.open = self.painter.get("open")
        self.save = self.painter.get("save")
        self.print = self.painter.get("print")

        # --------------------------------------------------------------------
        # SYSTEM
        # --------------------------------------------------------------------

        self.settings = self.painter.get("settings")
        self.help = self.painter.get("help")
        self.refresh = self.painter.get("refresh")

        # --------------------------------------------------------------------
        # EDITING
        # --------------------------------------------------------------------

        self.cut = self.painter.get("cut")
        self.copy = self.painter.get("copy")
        self.paste = self.painter.get("paste")

        # --------------------------------------------------------------------
        # TRANSFER
        # --------------------------------------------------------------------

        self.upload = self.painter.get("upload")
        self.download = self.painter.get("download")

        # --------------------------------------------------------------------
        # SECURITY
        # --------------------------------------------------------------------

        self.key = self.painter.get("key")

        # --------------------------------------------------------------------
        # NETWORK
        # --------------------------------------------------------------------

        self.connection = self.painter.get("connection")
        self.network = self.painter.get("network")
        self.disconnect = self.painter.get("disconnect")

        # --------------------------------------------------------------------
        # STATUS
        # --------------------------------------------------------------------

        self.connected = self.painter.get("connection", "connected")
        self.connecting = self.painter.get("connection", "connecting")
        self.warning = self.painter.get("connection", "warning")
        self.error = self.painter.get("connection", "error")
        self.info = self.painter.get("connection", "info")


# ============================================================================
# OPTIONAL COLOR LOOKUP
# ============================================================================

def get_icon_colour(name: str) -> str:
    """
    Return the normal color assigned to an icon.

    Useful if your toolbar also needs matching
    text/indicator colors.
    """

    return _ICON_COLORS.get(name, "#475569")


# ============================================================================
# MODULE TEST
# ============================================================================

if __name__ == "__main__":

    import sys

    from PyQt6.QtWidgets import (
        QApplication, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget,
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = QWidget()
    win.setWindowTitle("VMS 3000 Icon Test")
    win.setStyleSheet(f"background:{_DEFAULT_BG};")

    layout = QVBoxLayout(win)

    icons = ToolbarIcons()

    # ------------------------------------------------------------------------
    # Toolbar row
    # ------------------------------------------------------------------------

    toolbar = QHBoxLayout()

    for name in ("new", "open", "save", "print", "settings", "help",
                 "cut", "copy", "paste", "upload", "download", "refresh",
                 "key", "connection", "network", "disconnect"):

        button = QToolButton()
        button.setIcon(icons.painter.get_icon(name))
        button.setIconSize(icons.painter.get(name).size() / icons.painter._dpr)
        button.setToolTip(name)
        toolbar.addWidget(button)

    toolbar.addStretch(1)
    layout.addLayout(toolbar)

    # ------------------------------------------------------------------------
    # Status row
    # ------------------------------------------------------------------------

    status = QHBoxLayout()

    for label, pixmap in (
        ("Connected", icons.connected),
        ("Connecting", icons.connecting),
        ("Warning", icons.warning),
        ("Error", icons.error),
        ("Info", icons.info),
    ):
        icon_label = QLabel()
        icon_label.setPixmap(pixmap)
        status.addWidget(icon_label)
        status.addWidget(QLabel(label))
        status.addSpacing(12)

    status.addStretch(1)
    layout.addLayout(status)

    win.show()
    sys.exit(app.exec())
