import tkinter.font as tkfont

# Surfaces (from the design brief)
BG = "#F1F5FB"
HEADER_BG = "#EAF1FF"
CARD_BG = "#F7F9FF"
DECK_BG = "#E8F1FF"
INPUT_BG = "#FFFFFF"
BORDER = "#D7E2F2"
TRACK = "#D4DEEF"

# Blue family
BLUE = "#2563EB"
BLUE_HOVER = "#1D4ED8"
BLUE_PRESSED = "#1E40AF"
SECONDARY_BG = "#EAF1FF"
SECONDARY_HOVER = "#DCE8FF"
SECONDARY_PRESSED = "#C9DBFB"

# Text. TEXT_MUTED and the *_TEXT colors are darker than the brief's values so they pass WCAG AA.
TEXT = "#172554"
TEXT_MUTED = "#475569"
GREEN = "#16A34A"
GREEN_TEXT = "#15803D"
RED = "#DC2626"
RED_HOVER = "#B91C1C"
RED_PRESSED = "#991B1B"
RED_TEXT = "#B91C1C"
RED_SOFT = "#FEE2E2"
RED_RING = "#FCA5A5"

# Input borders (3:1 or better against white and the card color)
INPUT_BORDER = "#7A8EAD"

# Disabled controls, status dot, microphone circle
DISABLED_BG = "#C9D7F1"
DISABLED_TEXT = "#5B6B82"
GRAY_DOT = "#94A3B8"
MIC_FILL = "#DCEAFE"
MIC_RING = "#BBD3FA"

# Waveform bars
BAR_IDLE = "#A5BEF0"
BAR_ACTIVE = "#5B8DEF"
BAR_SUBDUED = "#C7D6F0"

# Sizes at 100% display scaling, in pixels
WINDOW_WIDTH = 550
HEADER_HEIGHT = 58
PAGE_PAD = 14
GAP = 12
CARD_HEIGHT = 128
CARD_RADIUS = 12
DECK_HEIGHT = 212
DECK_RADIUS = 22

FONT_CHOICES = ("Segoe UI Variable Text", "Segoe UI Variable", "Segoe UI", "Inter")


class Theme:
    def __init__(self, root, scale):
        """
        This function is about holding the display scale and the font choice for one window.
        The variable used in this code are:
        root: the tkinter root window (needed to list the installed fonts)
        scale: display scaling factor, 1.0 at 100%

        The flow process of this codes are as follows:
        1. Store the scale
        2. Pick the first installed font from FONT_CHOICES, or Segoe UI if none is found

        The result of this function are as follows:
        (none, builds the theme helper)
        """

        # 1. Store the scale
        self.scale = scale

        # 2. Pick the first installed font
        installed = set(tkfont.families(root))
        self.family = next((name for name in FONT_CHOICES if name in installed), "Segoe UI")

    def px(self, pixels):
        """
        This function is about scaling a size from 100% display scaling to this screen.
        The variable used in this code are:
        pixels: the size in pixels at 100% display scaling

        The flow process of this codes are as follows:
        1. Multiply by the scale and round to a whole pixel

        The result of this function are as follows:
        scaled: the size in pixels for this screen
        """

        # 1. Multiply by the scale and round
        return round(pixels * self.scale)

    def font(self, size, bold=False):
        """
        This function is about building a tkinter font tuple sized in pixels (so it scales exactly).
        The variable used in this code are:
        size: the text height in pixels at 100% display scaling
        bold: True for bold text

        The flow process of this codes are as follows:
        1. Return (family, negative pixel size, optional "bold"); a negative size means pixels

        The result of this function are as follows:
        font: the font tuple to pass to a tkinter widget
        """

        # 1. Build the font tuple
        if bold:
            return (self.family, -self.px(size), "bold")
        return (self.family, -self.px(size))
