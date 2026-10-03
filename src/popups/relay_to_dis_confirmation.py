"""
relay_to_dis_confirmation.py — VMS 3000  •  Relay to 3000/12M/DIS Confirmation Popup
Confirmation dialog when switching from Relay module to 3000/12M/DIS
"""

from .module_switch_confirmation import ModuleSwitchConfirmationPopup

# Palette used by this popup (matches the main theme's navy)
PALETTE = {
    "win_bg":       "#f5f7fa",
    "titlebar":     "#1a3a5c",
    "btn_face":     "#e4e9f0",
    "btn_hover":    "#d0e4f8",
    "btn_border":   "#b4bfcc",
    "text":         "#1a2533",
    "text_white":   "#ffffff",
    "text_dim":     "#6b7280",
    "accent":       "#1a4fa0",
    "accent_light": "#3a6fcc",
    "accent_teal":  "#0891b2",
}


class RelayToDISConfirmationPopup(ModuleSwitchConfirmationPopup):
    """
    Confirmation popup when switching from Relay module to 3000/12M/DIS.

    Same dialog as the generic module-switch confirmation, with wording
    specific to the relay → DIS switch.
    """

    SUBTEXT = "As it's the same relay, the rest will remain the same."
    PALETTE = PALETTE


if __name__ == "__main__":
    from qt_common import ensure_qapp, make_fonts

    app = ensure_qapp()
    popup = RelayToDISConfirmationPopup(
        None, make_fonts(), "3000/RLY", "3000/12M/DIS",
        lambda c: print(f"Confirmed: {c}"),
    )
    print(f"Result: {popup.show()}")
