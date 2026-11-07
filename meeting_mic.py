import time

import comtypes
import comtypes.client

comtypes.client.GetModule("UIAutomationCore.dll")
from comtypes.gen import UIAutomationClient as UIA

CLSID_UIAUTOMATION = "{ff48dba4-60ef-4201-aa87-54103eef594e}"
CHECK_SECONDS = 1
ABSENT_SECONDS = 3
WINDOW_WORD = "meet"
MIC_IS_ON_LABEL = "turn off microphone"
MIC_IS_OFF_LABEL = "turn on microphone"


def read_meet_mic(uia):
    """
    This function is about reading whether you are unmuted in a Google Meet window.
    The variable used in this code are:
    uia: the Windows UI Automation object

    The flow process of this codes are as follows:
    1. List the top-level windows and keep those whose title contains "Meet"
    2. Read every button in them and look for Meet's exact mute button names
    3. "Turn off microphone" means the mic is ON; "Turn on microphone" means it is OFF

    The result of this function are as follows:
    state: "on", "off", or None if no Meet mute button can be read right now
    """

    # 1. List the top-level windows and keep the Meet ones
    root = uia.GetRootElement()
    windows = root.FindAll(UIA.TreeScope_Children, uia.CreateTrueCondition())
    button_condition = uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, UIA.UIA_ButtonControlTypeId)

    for i in range(windows.Length):
        window = windows.GetElement(i)
        if WINDOW_WORD not in (window.CurrentName or "").lower():
            continue

        # 2. Read every button and look for the exact mute button names
        buttons = window.FindAll(UIA.TreeScope_Descendants, button_condition)
        for j in range(buttons.Length):
            try:
                name = (buttons.GetElement(j).CurrentName or "").lower()
            except comtypes.COMError:
                continue

            # 3. Turn the button name into on/off
            if name.startswith(MIC_IS_ON_LABEL):
                return "on"
            if name.startswith(MIC_IS_OFF_LABEL):
                return "off"
    return None


def watch_meet_mic(stop_event, on_change):
    """
    This function is about watching Google Meet's mute button and reporting each change, until stopped.
    The variable used in this code are:
    stop_event: threading.Event; the watcher exits when it is set (when the recording stops)
    on_change: function called with True (mic on) or False (mic off) whenever the wanted state changes

    The flow process of this codes are as follows:
    1. Prepare Windows UI Automation for this thread
    2. Once per second read the Meet mute button
    3. If the button is read, follow it; if it is missing for more than ABSENT_SECONDS, treat the mic
       as off (short gaps while Chrome redraws are ignored)
    4. Call on_change only when the wanted state changes, then release UI Automation on exit

    The result of this function are as follows:
    (none, runs until stop_event is set)
    """

    # 1. Prepare Windows UI Automation for this thread
    comtypes.CoInitialize()
    try:
        uia = comtypes.client.CreateObject(CLSID_UIAUTOMATION, interface=UIA.IUIAutomation)
        state = None
        last_seen = time.time()

        while not stop_event.is_set():
            # 2. Read the Meet mute button (skip this tick if Chrome is mid-redraw)
            try:
                reading = read_meet_mic(uia)
            except comtypes.COMError:
                stop_event.wait(CHECK_SECONDS)
                continue

            # 3. Follow the button, or switch off if it stays missing
            wanted = state
            if reading is not None:
                last_seen = time.time()
                wanted = reading == "on"
            elif time.time() - last_seen > ABSENT_SECONDS:
                wanted = False

            # 4. Report only real changes
            if wanted is not None and wanted != state:
                state = wanted
                on_change(wanted)
            stop_event.wait(CHECK_SECONDS)
    finally:
        comtypes.CoUninitialize()
