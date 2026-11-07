import tkinter as tk
import tkinter.font as tkfont

import ui_theme as t

ANIMATION_STEPS = 6
ANIMATION_MS = 14
SIMPLE_MESSAGES = ("", "Idle", "Recording...", "Transcribing...", "Done")
STATE_WORDS = {
    "IDLE": "Idle",
    "RECORDING": "Recording",
    "TRANSCRIBING": "Transcribing",
    "DONE": "Done",
    "ERROR": "Error",
}
STATE_DOT = {
    "IDLE": t.GRAY_DOT,
    "RECORDING": t.RED,
    "TRANSCRIBING": t.BLUE,
    "DONE": t.GREEN,
    "ERROR": t.RED,
}
STATE_BAR = {"ERROR": t.RED, "DONE": t.GREEN}


def lerp_color(start, end, amount):
    """
    This function is about mixing two hex colors.
    The variable used in this code are:
    start: the first color, like "#2563EB"
    end: the second color
    amount: 0.0 returns start, 1.0 returns end

    The flow process of this codes are as follows:
    1. Split both colors into red, green and blue
    2. Blend each channel and join them back into a hex color

    The result of this function are as follows:
    color: the blended hex color
    """

    # 1. Split both colors into channels
    a = [int(start[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(end[i : i + 2], 16) for i in (1, 3, 5)]

    # 2. Blend each channel
    mixed = [round(x + (y - x) * amount) for x, y in zip(a, b)]
    return "#{:02X}{:02X}{:02X}".format(*mixed)


def rounded_rect(canvas, x1, y1, x2, y2, radius, **options):
    """
    This function is about drawing a rounded rectangle on a canvas.
    The variable used in this code are:
    canvas: the tkinter canvas to draw on
    x1, y1, x2, y2: the rectangle corners
    radius: the corner radius
    options: fill, outline, tags and other canvas options

    The flow process of this codes are as follows:
    1. Keep the radius no bigger than half of the shorter side
    2. Build a smoothed polygon whose corners are rounded

    The result of this function are as follows:
    item: the canvas item id
    """

    # 1. Limit the radius
    radius = max(0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))

    # 2. Build the smoothed polygon
    points = [
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **options)


def draw_play(canvas, cx, cy, size, color, tags=None):
    """
    This function is about drawing a play triangle icon.
    The variable used in this code are:
    canvas: the canvas to draw on
    cx, cy: the center of the icon
    size: the icon height in pixels
    color: the fill color
    tags: optional canvas tags

    The flow process of this codes are as follows:
    1. Draw a right-pointing triangle centered on cx, cy

    The result of this function are as follows:
    (none)
    """

    # 1. Draw the triangle
    half = size / 2
    canvas.create_polygon(
        cx - half * 0.7, cy - half, cx - half * 0.7, cy + half, cx + half * 0.9, cy,
        fill=color, outline=color, tags=tags,
    )


def draw_stop(canvas, cx, cy, size, color, tags=None):
    """
    This function is about drawing a stop square icon.
    The variable used in this code are:
    canvas: the canvas to draw on
    cx, cy: the center of the icon
    size: the icon height in pixels
    color: the fill color
    tags: optional canvas tags

    The flow process of this codes are as follows:
    1. Draw a small rounded square centered on cx, cy

    The result of this function are as follows:
    (none)
    """

    # 1. Draw the rounded square
    half = size * 0.42
    rounded_rect(canvas, cx - half, cy - half, cx + half, cy + half, size * 0.12, fill=color, outline=color, tags=tags)


def draw_mic(canvas, cx, cy, size, color, tags=None):
    """
    This function is about drawing a microphone icon.
    The variable used in this code are:
    canvas: the canvas to draw on
    cx, cy: the center of the icon
    size: the icon height in pixels
    color: the icon color
    tags: optional canvas tags

    The flow process of this codes are as follows:
    1. Draw the rounded microphone body
    2. Draw the U-shaped holder, the stem and the base

    The result of this function are as follows:
    (none)
    """
    line = max(2, size * 0.085)
    top = cy - size * 0.37
    body_w = size * 0.36
    body_h = size * 0.58

    # 1. The rounded microphone body
    rounded_rect(canvas, cx - body_w / 2, top, cx + body_w / 2, top + body_h, body_w / 2, fill=color, outline=color, tags=tags)

    # 2. The U-shaped holder, the stem and the base
    radius = size * 0.28
    middle = top + body_h * 0.62
    canvas.create_arc(
        cx - radius, middle - radius, cx + radius, middle + radius,
        start=180, extent=180, style="arc", outline=color, width=line, tags=tags,
    )
    stem_top = middle + radius
    stem_bottom = stem_top + size * 0.1
    canvas.create_line(cx, stem_top, cx, stem_bottom, fill=color, width=line, capstyle="round", tags=tags)
    canvas.create_line(
        cx - size * 0.14, stem_bottom, cx + size * 0.14, stem_bottom,
        fill=color, width=line, capstyle="round", tags=tags,
    )


def draw_equalizer(canvas, cx, cy, size, color):
    """
    This function is about drawing the small equalizer bars used as the app icon.
    The variable used in this code are:
    canvas: the canvas to draw on
    cx, cy: the center of the icon
    size: the icon height in pixels
    color: the bar color

    The flow process of this codes are as follows:
    1. Draw four rounded vertical bars of different heights

    The result of this function are as follows:
    (none)
    """

    # 1. Draw the bars
    gap = size * 0.26
    for index, height in enumerate((0.45, 0.95, 0.65, 0.35)):
        x = cx + (index - 1.5) * gap
        half = size * height / 2
        canvas.create_line(x, cy - half, x, cy + half, fill=color, width=max(2, size * 0.14), capstyle="round")


class RoundedPanel(tk.Canvas):
    def __init__(self, parent, width, height, radius, fill, outline="", surround=t.BG):
        """
        This function is about building a rounded panel that other widgets can sit on.
        The variable used in this code are:
        parent: the widget that holds the panel
        width, height: the panel size in pixels
        radius: the corner radius in pixels
        fill: the panel color
        outline: optional border color
        surround: the color behind the rounded corners (the parent's color)

        The flow process of this codes are as follows:
        1. Create the canvas using the surrounding color
        2. Draw the rounded rectangle

        The result of this function are as follows:
        (none, builds the panel)
        """

        # 1. Create the canvas
        super().__init__(parent, width=width, height=height, bg=surround, highlightthickness=0)
        self.panel_width = width
        self.panel_height = height
        self._windows = []

        # 2. Draw the rounded rectangle
        rounded_rect(self, 1, 1, width - 1, height - 1, radius, fill=fill, outline=outline or fill)

    def place_widget(self, widget, x, y, anchor="nw", width=None, height=None):
        """
        This function is about putting a widget onto the panel at a fixed position.
        The variable used in this code are:
        widget: the widget to place (must have the panel as its parent)
        x, y: the position in pixels
        anchor: which point of the widget sits at x, y
        width, height: optional widget size in pixels

        The flow process of this codes are as follows:
        1. Create a canvas window holding the widget

        The result of this function are as follows:
        window: the canvas window id
        """

        # 1. Create the canvas window
        options = {"window": widget, "anchor": anchor}
        if width:
            options["width"] = width
        if height:
            options["height"] = height
        window = self.create_window(x, y, **options)
        self._windows.append(widget)
        return window


class PillButton(tk.Canvas):
    def __init__(self, parent, theme, text, command, width, height, style="primary", surround=t.BG, font_size=14):
        """
        This function is about building a rounded button with hover, pressed, focus and disabled looks.
        The variable used in this code are:
        parent: the widget that holds the button
        theme: the Theme object (scale and font)
        text: the button text; "Stop..." makes a primary button red with a stop icon, otherwise blue with a play icon
        command: the function called when the button is clicked
        width, height: the button size in pixels
        style: "primary" (solid, with icon) or "secondary" (light, text only)
        surround: the color behind the rounded corners
        font_size: text height in pixels at 100% display scaling

        The flow process of this codes are as follows:
        1. Store the settings and create the canvas
        2. Bind mouse and keyboard events
        3. Draw the button in its normal state

        The result of this function are as follows:
        (none, builds the button)
        """

        # 1. Store the settings and create the canvas
        super().__init__(parent, width=width, height=height, bg=surround, highlightthickness=0, cursor="hand2", takefocus=1)
        self.theme = theme
        self.command = command
        self.text = text
        self.style = style
        self.enabled = True
        self.hover = False
        self.pressed = False
        self.focused = False
        self.button_width = width
        self.button_height = height
        self.font = tkfont.Font(root=self, font=theme.font(font_size, bold=True))
        self._after_id = None
        self._fill = self._target_fill()

        # 2. Bind events
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Return>", self._on_key)
        self.bind("<space>", self._on_key)

        # 3. Draw the button
        self._draw()

    def _is_stop(self):
        """
        This function is about telling whether this primary button currently reads "Stop".
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Check the start of the text

        The result of this function are as follows:
        is_stop: True for a stop button
        """

        # 1. Check the start of the text
        return self.style == "primary" and self.text.lower().startswith("stop")

    def _palette(self):
        """
        This function is about choosing the colors for the current style and mode.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Pick the normal, hover, pressed, border and text colors

        The result of this function are as follows:
        palette: tuple (normal, hover, pressed, border, text color)
        """

        # 1. Pick the colors
        if self.style == "secondary":
            return t.SECONDARY_BG, t.SECONDARY_HOVER, t.SECONDARY_PRESSED, t.BLUE, t.TEXT
        if self._is_stop():
            return t.RED, t.RED_HOVER, t.RED_PRESSED, t.RED, "#FFFFFF"
        return t.BLUE, t.BLUE_HOVER, t.BLUE_PRESSED, t.BLUE, "#FFFFFF"

    def _target_fill(self):
        """
        This function is about choosing the fill color for the current hover, pressed and enabled state.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Disabled gets the grey-blue color, otherwise pressed, hover or normal

        The result of this function are as follows:
        fill: the hex color
        """

        # 1. Choose the fill
        normal, hover, pressed, _, _ = self._palette()
        if not self.enabled:
            return t.DISABLED_BG
        if self.pressed:
            return pressed
        return hover if self.hover else normal

    def _draw(self):
        """
        This function is about drawing the button: rounded body, optional icon, text and focus ring.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Clear the canvas and draw the rounded body (with a border for secondary buttons)
        2. Work out the text color and measure the content
        3. Draw the icon (primary buttons) and the text, centered together
        4. Draw a focus ring when the button has keyboard focus

        The result of this function are as follows:
        (none)
        """

        # 1. Clear the canvas and draw the rounded body
        self.delete("all")
        w, h = self.button_width, self.button_height
        _, _, _, border, text_color = self._palette()
        outline = border if (self.style == "secondary" and self.enabled) else self._fill
        rounded_rect(self, 1, 1, w - 1, h - 1, h / 2 if self.style == "primary" else self.theme.px(8), fill=self._fill, outline=outline)

        # 2. Work out the text color and measure the content
        if not self.enabled:
            text_color = t.DISABLED_TEXT
        label = self.text.upper() if self.style == "primary" else self.text
        text_width = self.font.measure(label)
        icon_size = h * 0.34 if self.style == "primary" else 0
        gap = self.theme.px(10) if icon_size else 0
        start = (w - (icon_size + gap + text_width)) / 2

        # 3. Draw the icon and the text
        if icon_size:
            icon_cx = start + icon_size / 2
            if self._is_stop():
                draw_stop(self, icon_cx, h / 2, icon_size, text_color)
            else:
                draw_play(self, icon_cx, h / 2, icon_size, text_color)
        self.create_text(start + icon_size + gap, h / 2, text=label, anchor="w", fill=text_color, font=self.font)

        # 4. Focus ring
        if self.focused:
            rounded_rect(self, 3, 3, w - 3, h - 3, h / 2 - 2, fill="", outline=t.TEXT, width=2)

    def _animate_to(self, target):
        """
        This function is about fading the fill color to a new color in a few quick steps.
        The variable used in this code are:
        target: the color to fade to

        The flow process of this codes are as follows:
        1. Cancel any fade that is still running
        2. Step the color from the current one to the target, redrawing each step

        The result of this function are as follows:
        (none)
        """

        # 1. Cancel any running fade
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        start = self._fill

        # 2. Step toward the target
        def step(index):
            try:
                self._fill = lerp_color(start, target, index / ANIMATION_STEPS)
                self._draw()
                if index < ANIMATION_STEPS:
                    self._after_id = self.after(ANIMATION_MS, step, index + 1)
                else:
                    self._after_id = None
            except tk.TclError:
                self._after_id = None

        step(1)

    def _refresh(self, animate=True):
        """
        This function is about updating the button after its state changed.
        The variable used in this code are:
        animate: True to fade, False to switch at once

        The flow process of this codes are as follows:
        1. Fade or jump to the fill color for the new state

        The result of this function are as follows:
        (none)
        """

        # 1. Fade or jump
        if animate:
            self._animate_to(self._target_fill())
        else:
            self._fill = self._target_fill()
            self._draw()

    def _on_enter(self, event):
        """
        This function is about reacting to the mouse entering the button.
        The variable used in this code are:
        event: the mouse event

        The flow process of this codes are as follows:
        1. Remember the hover and fade to the hover color

        The result of this function are as follows:
        (none)
        """

        # 1. Hover
        self.hover = True
        self._refresh()

    def _on_leave(self, event):
        """
        This function is about reacting to the mouse leaving the button.
        The variable used in this code are:
        event: the mouse event

        The flow process of this codes are as follows:
        1. Clear hover and pressed, then fade back

        The result of this function are as follows:
        (none)
        """

        # 1. Leave
        self.hover = False
        self.pressed = False
        self._refresh()

    def _on_press(self, event):
        """
        This function is about reacting to the mouse button going down on the button.
        The variable used in this code are:
        event: the mouse event

        The flow process of this codes are as follows:
        1. Take keyboard focus (when enabled) and show the pressed color

        The result of this function are as follows:
        (none)
        """

        # 1. Pressed look
        if self.enabled:
            self.focus_set()
            self.pressed = True
            self._refresh(animate=False)

    def _on_release(self, event):
        """
        This function is about running the command when the mouse is released on the button.
        The variable used in this code are:
        event: the mouse release event

        The flow process of this codes are as follows:
        1. Clear the pressed look
        2. Run the command only if the button is enabled and the release happened inside it

        The result of this function are as follows:
        (none)
        """

        # 1. Clear the pressed look
        was_pressed = self.pressed
        self.pressed = False
        self._refresh(animate=False)

        # 2. Run the command
        inside = 0 <= event.x <= self.button_width and 0 <= event.y <= self.button_height
        if self.enabled and was_pressed and inside:
            self.command()

    def _on_focus_in(self, event):
        """
        This function is about showing the focus ring.
        The variable used in this code are:
        event: the focus event

        The flow process of this codes are as follows:
        1. Remember the focus and redraw

        The result of this function are as follows:
        (none)
        """

        # 1. Focus ring on
        self.focused = True
        self._draw()

    def _on_focus_out(self, event):
        """
        This function is about hiding the focus ring.
        The variable used in this code are:
        event: the focus event

        The flow process of this codes are as follows:
        1. Forget the focus and redraw

        The result of this function are as follows:
        (none)
        """

        # 1. Focus ring off
        self.focused = False
        self._draw()

    def _on_key(self, event):
        """
        This function is about pressing the button with the Enter or Space key.
        The variable used in this code are:
        event: the key event

        The flow process of this codes are as follows:
        1. Run the command when the button is enabled

        The result of this function are as follows:
        (none)
        """

        # 1. Run the command
        if self.enabled:
            self.command()

    def config(self, text=None, state=None):
        """
        This function is about changing the button text or enabled state like a normal button.
        The variable used in this code are:
        text: the new text, or None to keep it
        state: "normal" or "disabled", or None to keep it

        The flow process of this codes are as follows:
        1. Store the new text and state
        2. Redraw with the matching colors and cursor

        The result of this function are as follows:
        (none)
        """

        # 1. Store the new text and state
        if text is not None:
            self.text = text
        if state is not None:
            self.enabled = state == "normal"
            self.hover = self.hover and self.enabled
            self.pressed = False

        # 2. Redraw
        self._refresh(animate=False)
        super().config(cursor="hand2" if self.enabled else "arrow")


class ToggleControl(tk.Canvas):
    def __init__(self, parent, theme, text, variable, kind="check", value=None, command=None, surround=t.CARD_BG):
        """
        This function is about building a checkbox or a radio button with a clear tick or dot.
        The variable used in this code are:
        parent: the widget that holds the control
        theme: the Theme object (scale and font)
        text: the label shown next to the indicator
        variable: the tkinter variable it reads and writes (BooleanVar for a checkbox, StringVar for radios)
        kind: "check" for a checkbox, "radio" for a radio button
        value: for a radio button, the value it sets when chosen
        command: function called after the user changes it (checkboxes)
        surround: the color behind the control

        The flow process of this codes are as follows:
        1. Store the settings, measure the label and create the canvas
        2. Redraw whenever the variable changes, and bind mouse and keyboard events
        3. Draw the control

        The result of this function are as follows:
        (none, builds the control)
        """

        # 1. Store the settings and create the canvas
        self.theme = theme
        self.text = text
        self.variable = variable
        self.kind = kind
        self.value = value
        self.command = command
        self.enabled = True
        self.hover = False
        self.focused = False
        self.box = theme.px(18)
        self.font = tkfont.Font(root=parent, font=theme.font(12))
        super().__init__(parent, width=self._needed_width(), height=theme.px(26), bg=surround, highlightthickness=0, cursor="hand2", takefocus=1)

        # 2. Redraw on variable changes and bind events
        self.variable.trace_add("write", lambda *args: self._draw())
        self.bind("<Enter>", lambda event: self._set_hover(True))
        self.bind("<Leave>", lambda event: self._set_hover(False))
        self.bind("<ButtonRelease-1>", self._on_click)
        self.bind("<FocusIn>", lambda event: self._set_focus(True))
        self.bind("<FocusOut>", lambda event: self._set_focus(False))
        self.bind("<space>", self._on_click)
        self.bind("<Return>", self._on_click)

        # 3. Draw the control
        self._draw()

    def _needed_width(self):
        """
        This function is about working out how wide the control must be for its label.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Add the indicator, the gap and the measured label width

        The result of this function are as follows:
        width: the width in pixels
        """

        # 1. Add the parts
        return self.box + self.theme.px(8) + self.font.measure(self.text) + self.theme.px(6)

    def _is_selected(self):
        """
        This function is about telling whether the control is currently ticked or chosen.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. A checkbox is selected when its variable is true; a radio when its variable equals its value

        The result of this function are as follows:
        selected: True when ticked or chosen
        """

        # 1. Compare
        if self.kind == "check":
            return bool(self.variable.get())
        return self.variable.get() == self.value

    def _draw(self):
        """
        This function is about drawing the indicator (box with tick, or circle with dot) and the label.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Clear the canvas and choose colors for the enabled, hover and selected state
        2. Draw the box or circle, then the tick or the dot
        3. Draw the label and a thin focus ring when the control has keyboard focus

        The result of this function are as follows:
        (none)
        """

        # 1. Clear and choose colors
        self.delete("all")
        selected = self._is_selected()
        height = int(self["height"])
        top = (height - self.box) / 2
        left = 1
        if not self.enabled:
            fill, border, mark, text_color = t.TRACK, "#B8C4D6", t.DISABLED_TEXT, t.DISABLED_TEXT
        else:
            border = t.BLUE if (selected or self.hover) else t.INPUT_BORDER
            fill = t.BLUE if (selected and self.kind == "check") else t.INPUT_BG
            mark = "#FFFFFF" if self.kind == "check" else t.BLUE
            text_color = t.TEXT

        # 2. The indicator
        width = max(1, self.theme.px(2) if selected else self.theme.px(1))
        if self.kind == "check":
            rounded_rect(self, left, top, left + self.box, top + self.box, self.theme.px(5), fill=fill, outline=border, width=width)
            if selected:
                b = self.box
                self.create_line(
                    left + b * 0.26, top + b * 0.52, left + b * 0.43, top + b * 0.70, left + b * 0.76, top + b * 0.32,
                    fill=mark, width=max(2, self.theme.px(2)), capstyle="round", joinstyle="round",
                )
        else:
            self.create_oval(left, top, left + self.box, top + self.box, fill=fill, outline=border, width=width)
            if selected:
                inset = self.box * 0.28
                self.create_oval(left + inset, top + inset, left + self.box - inset, top + self.box - inset, fill=mark, outline=mark)

        # 3. The label and the focus ring
        self.create_text(left + self.box + self.theme.px(8), height / 2, text=self.text, anchor="w", fill=text_color, font=self.font)
        if self.focused:
            rounded_rect(self, 0, 1, int(self["width"]) - 1, height - 1, self.theme.px(6), fill="", outline=t.BLUE)

    def _set_hover(self, hover):
        """
        This function is about showing or clearing the hover look.
        The variable used in this code are:
        hover: True when the mouse is over the control

        The flow process of this codes are as follows:
        1. Store the hover and redraw

        The result of this function are as follows:
        (none)
        """

        # 1. Store and redraw
        self.hover = hover and self.enabled
        self._draw()

    def _set_focus(self, focused):
        """
        This function is about showing or clearing the keyboard focus ring.
        The variable used in this code are:
        focused: True when the control has keyboard focus

        The flow process of this codes are as follows:
        1. Store the focus and redraw

        The result of this function are as follows:
        (none)
        """

        # 1. Store and redraw
        self.focused = focused
        self._draw()

    def _on_click(self, event):
        """
        This function is about toggling or choosing the control on a click or a key press.
        The variable used in this code are:
        event: the mouse or key event

        The flow process of this codes are as follows:
        1. Ignore the event when the control is disabled
        2. A checkbox flips; a radio sets its value
        3. Run the command (if any) after the change

        The result of this function are as follows:
        (none)
        """

        # 1. Ignore when disabled
        if not self.enabled:
            return

        # 2. Change the variable
        if self.kind == "check":
            self.variable.set(not self.variable.get())
        else:
            self.variable.set(self.value)

        # 3. Run the command
        if self.command:
            self.command()

    def instate(self, states):
        """
        This function is about answering ttk-style state questions, so tests and old code keep working.
        The variable used in this code are:
        states: a list of state names, like ["disabled"]

        The flow process of this codes are as follows:
        1. Return True when asked about "disabled" and the control is disabled

        The result of this function are as follows:
        answer: True or False
        """

        # 1. Answer for "disabled"
        return "disabled" in states and not self.enabled

    def config(self, text=None, state=None):
        """
        This function is about changing the label or the enabled state like a normal checkbox.
        The variable used in this code are:
        text: the new label, or None to keep it
        state: "normal" or "disabled", or None to keep it

        The flow process of this codes are as follows:
        1. Store the new text and resize the canvas to fit it
        2. Store the new enabled state and the matching cursor
        3. Redraw

        The result of this function are as follows:
        (none)
        """

        # 1. New text
        if text is not None:
            self.text = text
            tk.Canvas.configure(self, width=self._needed_width())

        # 2. New state
        if state is not None:
            self.enabled = state == "normal"
            self.hover = self.hover and self.enabled
            tk.Canvas.configure(self, cursor="hand2" if self.enabled else "arrow")

        # 3. Redraw
        self._draw()


class RoundedProgress(tk.Canvas):
    def __init__(self, parent, theme, height=8, surround=t.BG):
        """
        This function is about building a thin rounded progress bar with a normal and a moving (indeterminate) mode.
        The variable used in this code are:
        parent: the widget that holds the bar
        theme: the Theme object (scale)
        height: the bar height in pixels at 100% display scaling
        surround: the color behind the bar

        The flow process of this codes are as follows:
        1. Create the canvas, which stretches with its parent
        2. Redraw whenever the size changes

        The result of this function are as follows:
        (none, builds the bar)
        """

        # 1. Create the canvas
        self.bar_height = theme.px(height)
        super().__init__(parent, height=self.bar_height, bg=surround, highlightthickness=0)
        self.value = 0.0
        self.color = t.BLUE
        self._moving = False
        self._phase = 0.0
        self._job = None

        # 2. Redraw on resize
        self.bind("<Configure>", lambda event: self._draw())

    def __setitem__(self, key, value):
        """
        This function is about letting the code set progress['value'] like a normal progress bar.
        The variable used in this code are:
        key: the option name; only "value" is handled here
        value: the new value, 0 to 100

        The flow process of this codes are as follows:
        1. A real value stops the moving mode and redraws; other options go to the canvas

        The result of this function are as follows:
        (none)
        """

        # 1. Handle "value"
        if key == "value":
            self.value = max(0.0, min(100.0, float(value)))
            self.stop_indeterminate()
            self._draw()
        else:
            super().__setitem__(key, value)

    def set_color(self, color):
        """
        This function is about changing the fill color of the bar.
        The variable used in this code are:
        color: the new hex color

        The flow process of this codes are as follows:
        1. Store the color and redraw

        The result of this function are as follows:
        (none)
        """

        # 1. Store the color and redraw
        self.color = color
        self._draw()

    def start_indeterminate(self):
        """
        This function is about showing a moving bar when no real percentage is known yet.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Switch to moving mode and start the animation loop

        The result of this function are as follows:
        (none)
        """

        # 1. Start moving
        if not self._moving:
            self._moving = True
            self._animate()

    def stop_indeterminate(self):
        """
        This function is about stopping the moving bar.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Leave moving mode and cancel the animation loop

        The result of this function are as follows:
        (none)
        """

        # 1. Stop moving
        self._moving = False
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def _animate(self):
        """
        This function is about moving the bar one step and scheduling the next step.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Advance the position and redraw
        2. Schedule the next step while still moving

        The result of this function are as follows:
        (none)
        """

        # 1. Advance and redraw
        if not self._moving:
            return
        self._phase = (self._phase + 0.025) % 1.0
        self._draw()

        # 2. Schedule the next step
        self._job = self.after(30, self._animate)

    def _draw(self):
        """
        This function is about drawing the track and the filled part.
        The variable used in this code are:
        (none)

        The flow process of this codes are as follows:
        1. Clear the canvas and draw the pale rounded track
        2. In moving mode draw a short bar sliding across; otherwise draw the filled part

        The result of this function are as follows:
        (none)
        """

        # 1. Clear and draw the track
        self.delete("all")
        w, h = self.winfo_width(), self.bar_height
        if w < 4:
            return
        rounded_rect(self, 0, 0, w, h, h / 2, fill=t.TRACK, outline=t.TRACK)

        # 2. Moving bar or filled part
        if self._moving:
            segment = w * 0.3
            left = -segment + (w + segment) * self._phase
            x1, x2 = max(0, left), min(w, left + segment)
        else:
            x1, x2 = 0, w * self.value / 100.0
            if x2 > 0:
                x2 = max(x2, h)
        if x2 - x1 >= 2:
            rounded_rect(self, x1, 0, x2, h, h / 2, fill=self.color, outline=self.color)


class AppHeader(tk.Canvas):
    def __init__(self, parent, theme):
        """
        This function is about building the header: blue equalizer icon, app name and tagline.
        The variable used in this code are:
        parent: the widget that holds the header
        theme: the Theme object (scale and font)

        The flow process of this codes are as follows:
        1. Create the full-width header canvas
        2. Draw the rounded blue icon with the equalizer bars
        3. Draw "AUDIO TRANSCRIBER" and the muted "Local AI Recording" under it

        The result of this function are as follows:
        (none, builds the header)
        """

        # 1. Create the canvas
        width = theme.px(t.WINDOW_WIDTH)
        height = theme.px(t.HEADER_HEIGHT)
        super().__init__(parent, width=width, height=height, bg=t.HEADER_BG, highlightthickness=0)

        # 2. The rounded blue icon
        px = theme.px
        left, top, size = px(18), px(11), px(36)
        rounded_rect(self, left, top, left + size, top + size, px(10), fill=t.BLUE, outline=t.BLUE)
        draw_equalizer(self, left + size / 2, top + size / 2, size * 0.5, "#FFFFFF")

        # 3. The title and the tagline
        text_x = left + size + px(12)
        self.create_text(text_x, px(22), text="AUDIO TRANSCRIBER", anchor="w", fill=t.TEXT, font=theme.font(15, bold=True))
        self.create_text(text_x, px(41), text="Local AI Recording", anchor="w", fill=t.TEXT_MUTED, font=theme.font(11))


class ConfigSection(tk.Frame):
    def __init__(self, parent, theme, folder_var, device_var, gpu_available, mic_var, auto_var, commands):
        """
        This function is about building the two side-by-side cards: OUTPUT and DEVICE.
        The variable used in this code are:
        parent: the widget that holds the section
        theme: the Theme object (scale and font)
        folder_var: StringVar with the shown output folder
        device_var: StringVar with "cuda" or "cpu"
        gpu_available: True to show the GPU radio button
        mic_var: BooleanVar for the "My mic" checkbox
        auto_var: BooleanVar for the "Auto: follow Meet mute" checkbox
        commands: dict with the handlers "browse", "check_model", "mic", "auto"

        The flow process of this codes are as follows:
        1. Create the section and the two rounded cards of equal height
        2. Fill the OUTPUT card: heading, path box, Browse, Check Model, status dot and text
        3. Fill the DEVICE card: heading, GPU/CPU radios, mic and Auto checkboxes

        The result of this function are as follows:
        (none, builds the cards and exposes their widgets as attributes)
        """

        # 1. Create the section and the two cards
        super().__init__(parent, bg=t.BG)
        px = theme.px
        total = px(t.WINDOW_WIDTH - 2 * t.PAGE_PAD)
        gap = px(t.GAP)
        card_width = (total - gap) // 2
        card_height = px(t.CARD_HEIGHT)
        left = RoundedPanel(self, card_width, card_height, px(t.CARD_RADIUS), t.CARD_BG, t.BORDER)
        right = RoundedPanel(self, card_width, card_height, px(t.CARD_RADIUS), t.CARD_BG, t.BORDER)
        left.pack(side="left")
        right.pack(side="right")
        heading = theme.font(11, bold=True)

        # 2. The OUTPUT card
        left.create_text(px(14), px(18), text="OUTPUT", anchor="w", fill=t.TEXT_MUTED, font=heading)
        browse_width = px(68)
        entry_width = card_width - px(28) - px(8) - browse_width
        self.folder_entry = tk.Entry(
            left, textvariable=folder_var, validate="key", validatecommand=lambda: False, font=theme.font(12),
            bg=t.INPUT_BG, fg=t.TEXT, relief="flat", highlightthickness=1, highlightbackground=t.INPUT_BORDER,
            highlightcolor=t.BLUE, insertbackground=t.TEXT,
        )
        left.place_widget(self.folder_entry, px(14), px(34), width=entry_width, height=px(28))
        self.browse_button = PillButton(
            left, theme, "Browse", commands["browse"], browse_width, px(28), style="secondary", surround=t.CARD_BG, font_size=12
        )
        left.place_widget(self.browse_button, px(14) + entry_width + px(8), px(34))
        self.check_button = PillButton(
            left, theme, "Check Model", commands["check_model"], px(112), px(28), style="secondary", surround=t.CARD_BG, font_size=12
        )
        left.place_widget(self.check_button, px(14), px(74))
        dot = px(12)
        self.model_dot = tk.Canvas(left, width=dot, height=dot, bg=t.CARD_BG, highlightthickness=0)
        self.model_dot_id = self.model_dot.create_oval(1, 1, dot - 1, dot - 1, fill=t.GREEN, outline="")
        left.place_widget(self.model_dot, px(14) + px(112) + px(14), px(74) + px(14), anchor="w")
        self.model_label = tk.Label(left, text="", bg=t.CARD_BG, fg=t.GREEN_TEXT, font=theme.font(12))
        left.place_widget(self.model_label, px(14) + px(112) + px(14) + dot + px(6), px(74) + px(14), anchor="w")

        # 3. The DEVICE card
        right.create_text(px(14), px(18), text="DEVICE", anchor="w", fill=t.TEXT_MUTED, font=heading)
        radio_row = tk.Frame(right, bg=t.CARD_BG)
        self.gpu_radio = None
        if gpu_available:
            self.gpu_radio = ToggleControl(radio_row, theme, "GPU", device_var, kind="radio", value="cuda")
            self.gpu_radio.pack(side="left", padx=(0, px(14)))
        self.cpu_radio = ToggleControl(radio_row, theme, "CPU", device_var, kind="radio", value="cpu")
        self.cpu_radio.pack(side="left")
        right.place_widget(radio_row, px(14), px(32))
        self.mic_check = ToggleControl(right, theme, "My mic: OFF", mic_var, kind="check", command=commands["mic"])
        right.place_widget(self.mic_check, px(14), px(64))
        self.auto_check = ToggleControl(right, theme, "Auto: follow Meet mute", auto_var, kind="check", command=commands["auto"])
        right.place_widget(self.auto_check, px(14), px(96))


class RecordingDeck(RoundedPanel):
    def __init__(self, parent, theme, command):
        """
        This function is about building the main recording deck: mic circle, big timer, waveform and the start button.
        The variable used in this code are:
        parent: the widget that holds the deck
        theme: the Theme object (scale and font)
        command: the function called when the main button is clicked

        The flow process of this codes are as follows:
        1. Create the large rounded pale-blue panel
        2. Place the mic circle and the big timer side by side in the middle
        3. Place the waveform canvas under them and the pill button under the waveform
        4. Draw the mic in its idle look

        The result of this function are as follows:
        (none, builds the deck and exposes timer_label, wave_canvas and toggle_button)
        """

        # 1. Create the panel
        px = theme.px
        self.theme = theme
        width = px(t.WINDOW_WIDTH - 2 * t.PAGE_PAD)
        super().__init__(parent, width, px(t.DECK_HEIGHT), px(t.DECK_RADIUS), t.DECK_BG, t.BORDER)

        # 2. The mic circle and the timer
        circle = px(70)
        timer_width = px(150)
        gap = px(20)
        group_left = (width - (circle + gap + timer_width)) // 2
        self.mic_center = (group_left + circle // 2, px(14) + circle // 2)
        self.mic_diameter = circle
        self.timer_label = tk.Label(self, text="00:00", bg=t.DECK_BG, fg=t.TEXT, font=theme.font(50))
        self.place_widget(self.timer_label, group_left + circle + gap, self.mic_center[1], anchor="w")

        # 3. The waveform and the main button
        self.wave_width = width - px(44)
        self.wave_height = px(52)
        self.wave_canvas = tk.Canvas(self, width=self.wave_width, height=self.wave_height, bg=t.DECK_BG, highlightthickness=0)
        self.place_widget(self.wave_canvas, px(22), px(96))
        button_width = px(220)
        self.toggle_button = PillButton(
            self, theme, "Start Recording", command, button_width, px(44), style="primary", surround=t.DECK_BG, font_size=14
        )
        self.place_widget(self.toggle_button, (width - button_width) // 2, px(158))

        # 4. The mic in its idle look
        self.set_state("IDLE")

    def set_state(self, name):
        """
        This function is about changing the microphone circle to match the app state.
        The variable used in this code are:
        name: "IDLE", "RECORDING", "TRANSCRIBING", "DONE" or "ERROR"

        The flow process of this codes are as follows:
        1. Remove the old microphone drawing
        2. Recording gets a red ring and a red mic; every other state gets the calm blue look

        The result of this function are as follows:
        (none)
        """

        # 1. Remove the old drawing
        self.delete("mic")
        cx, cy = self.mic_center
        radius = self.mic_diameter / 2

        # 2. Draw the circle and the icon
        if name == "RECORDING":
            fill, ring, icon = t.RED_SOFT, t.RED_RING, t.RED
        else:
            fill, ring, icon = t.MIC_FILL, t.MIC_RING, t.BLUE
        self.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, fill=fill, outline=ring, width=self.theme.px(3), tags="mic")
        draw_mic(self, cx, cy, self.mic_diameter * 0.46, icon, tags="mic")


class StatusText:
    def __init__(self, section):
        """
        This function is about letting the app code use status_label.config(text=...) with the new status section.
        The variable used in this code are:
        section: the StatusSection that shows the message

        The flow process of this codes are as follows:
        1. Remember the section and start with the text "Idle"

        The result of this function are as follows:
        (none)
        """

        # 1. Remember the section
        self._section = section
        self._text = "Idle"

    def config(self, text=None, **options):
        """
        This function is about changing the status message.
        The variable used in this code are:
        text: the new message, or None to keep it
        options: ignored (kept so it can replace a normal label)

        The flow process of this codes are as follows:
        1. Store the message and let the section show it

        The result of this function are as follows:
        (none)
        """

        # 1. Store and show the message
        if text is not None:
            self._text = text
            self._section.show_message(text)

    configure = config

    def cget(self, key):
        """
        This function is about reading the current status message.
        The variable used in this code are:
        key: the option name; only "text" is supported

        The flow process of this codes are as follows:
        1. Return the stored message for "text"

        The result of this function are as follows:
        value: the message, or an empty string for other options
        """

        # 1. Return the message
        return self._text if key == "text" else ""


class StatusSection(tk.Frame):
    def __init__(self, parent, theme):
        """
        This function is about building the bottom section: status dot and word, progress bar, and the detail lines.
        The variable used in this code are:
        parent: the widget that holds the section
        theme: the Theme object (scale and font)

        The flow process of this codes are as follows:
        1. Create the row: status dot, status word and the long thin progress bar
        2. Create the detail line (shown only for messages that carry extra information)
        3. Create the footer with the percent label and the "Last saved" label (hidden when empty)

        The result of this function are as follows:
        (none, builds the section and exposes status_label, progress_bar, progress_label and saved_label)
        """

        # 1. The status row
        super().__init__(parent, bg=t.BG)
        px = theme.px
        self.theme = theme
        row = tk.Frame(self, bg=t.BG)
        row.pack(fill="x")
        dot = px(12)
        self.dot = tk.Canvas(row, width=dot, height=dot, bg=t.BG, highlightthickness=0)
        self.dot_id = self.dot.create_oval(1, 1, dot - 1, dot - 1, fill=t.GRAY_DOT, outline="")
        self.dot.pack(side="left", padx=(px(4), px(8)))
        self.state_label = tk.Label(row, text="Idle", bg=t.BG, fg=t.TEXT, font=theme.font(13, bold=True), width=12, anchor="w")
        self.state_label.pack(side="left")
        self.progress_bar = RoundedProgress(row, theme, height=8, surround=t.BG)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, px(4)))

        # 2. The detail line
        self.detail_label = tk.Label(
            self, text="", bg=t.BG, fg=t.TEXT_MUTED, font=theme.font(12), wraplength=px(500), justify="left", anchor="w"
        )
        self.status_label = StatusText(self)

        # 3. The footer
        footer = tk.Frame(self, bg=t.BG)
        footer.pack(fill="x")
        footer.columnconfigure(0, weight=1)
        self.footer = footer
        self.progress_label = tk.Label(footer, text="", bg=t.BG, fg=t.TEXT_MUTED, font=theme.font(12))
        self.progress_label.grid(row=0, column=0)
        self.saved_label = tk.Label(
            footer, text="", bg=t.BG, fg=t.TEXT_MUTED, font=theme.font(12), wraplength=px(500), justify="center"
        )
        self.saved_label.grid(row=1, column=0)
        self.progress_label.grid_remove()
        self.saved_label.grid_remove()
        self.state_name = "IDLE"

    def set_state(self, name):
        """
        This function is about changing the status dot, word and progress color to match the app state.
        The variable used in this code are:
        name: "IDLE", "RECORDING", "TRANSCRIBING", "DONE" or "ERROR"

        The flow process of this codes are as follows:
        1. Set the dot color and the status word
        2. Set the progress color (red for error, green for done, blue otherwise)
        3. While transcribing and without a real percentage yet, show the moving bar; otherwise stop it
        4. Show the detail line in red for an error and in muted gray otherwise

        The result of this function are as follows:
        (none)
        """

        # 1. Dot and word
        self.state_name = name
        self.dot.itemconfig(self.dot_id, fill=STATE_DOT[name])
        self.state_label.config(text=STATE_WORDS[name])

        # 2. Progress color
        self.progress_bar.set_color(STATE_BAR.get(name, t.BLUE))

        # 3. Moving bar only while transcribing and no percentage yet
        if name == "TRANSCRIBING" and self.progress_bar.value <= 0:
            self.progress_bar.start_indeterminate()
        else:
            self.progress_bar.stop_indeterminate()
            self.progress_bar._draw()

        # 4. Detail color
        self.detail_label.config(fg=t.RED_TEXT if name == "ERROR" else t.TEXT_MUTED)

    def show_message(self, text):
        """
        This function is about showing a status message: plain state messages stay hidden, longer ones appear under the row.
        The variable used in this code are:
        text: the message from the app, like "Recording..." or "Error: ..."

        The flow process of this codes are as follows:
        1. Hide the detail line for the simple messages the status word already says
        2. Show the detail line for every other message

        The result of this function are as follows:
        (none)
        """

        # 1. Hide for simple messages
        if text in SIMPLE_MESSAGES:
            self.detail_label.pack_forget()
            return

        # 2. Show the message
        self.detail_label.config(text=text)
        if not self.detail_label.winfo_ismapped():
            self.detail_label.pack(fill="x", pady=(self.theme.px(4), 0), before=self.footer)
