import time
from datetime import datetime

import comtypes.client

comtypes.client.GetModule("UIAutomationCore.dll")
from comtypes.gen import UIAutomationClient as UIA

LOG_FILE = "mic_probe_meet_log.txt"
CHECK_SECONDS = 1
HEARTBEAT_SECONDS = 5
WINDOW_WORDS = ("meet", "teams", "zoom")
BUTTON_WORDS = ("microphone", "mikrofon", "unmute", "mute")
CLSID_UIAUTOMATION = "{ff48dba4-60ef-4201-aa87-54103eef594e}"


def log(message):
    """
    This function is about printing a line with the time and saving it to the log file.
    The variable used in this code are:
    message: the text to show

    The flow process of this codes are as follows:
    1. Add the current time to the message
    2. Print it and append it to the log file

    The result of this function are as follows:
    (none)
    """

    # 1. Add the current time
    line = f"{datetime.now():%H:%M:%S}  {message}"

    # 2. Print it and append it to the log file
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_meeting_buttons(uia):
    """
    This function is about finding meeting windows and reading the names of their mic-related buttons.
    The variable used in this code are:
    uia: the Windows UI Automation object

    The flow process of this codes are as follows:
    1. List the top-level windows and keep those whose title has Meet, Teams or Zoom
    2. In each, read every button and keep those whose name has a microphone or mute word
    3. Count how many buttons were readable at all, to tell if the app shows its buttons to us

    The result of this function are as follows:
    found: dict of window title -> sorted list of mic-related button names
    total_buttons: how many buttons were readable in those windows (0 means we are blind)
    """

    # 1. List the top-level windows and keep the meeting ones
    root = uia.GetRootElement()
    windows = root.FindAll(UIA.TreeScope_Children, uia.CreateTrueCondition())
    button_condition = uia.CreatePropertyCondition(UIA.UIA_ControlTypePropertyId, UIA.UIA_ButtonControlTypeId)
    found = {}
    total_buttons = 0

    for i in range(windows.Length):
        window = windows.GetElement(i)
        title = window.CurrentName or ""
        if not any(word in title.lower() for word in WINDOW_WORDS):
            continue

        # 2. Read every button and keep the mic-related ones
        buttons = window.FindAll(UIA.TreeScope_Descendants, button_condition)
        names = []
        for j in range(buttons.Length):
            try:
                name = buttons.GetElement(j).CurrentName or ""
            except comtypes.COMError:
                continue
            if any(word in name.lower() for word in BUTTON_WORDS):
                names.append(name)

        # 3. Count the readable buttons
        total_buttons += buttons.Length
        found[title] = sorted(names)

    return found, total_buttons


def main():
    """
    This function is about watching the meeting windows' microphone buttons and reporting every change.
    The variable used in this code are:
    (none)

    The flow process of this codes are as follows:
    1. Explain what to do, then read the starting state
    2. Check once per second and print a line whenever a mic-related button name changes
    3. Print a "still watching" line every few seconds, including how many buttons are readable

    The result of this function are as follows:
    (none, runs until you press Ctrl+C)
    """

    # 1. Explain what to do, then read the starting state
    print("Meeting mic-button probe: watches only, changes nothing. Press Ctrl+C to stop.")
    print("Open your meeting in the VISIBLE tab, then mute and unmute a few times.")
    print(f"Every change is also saved in {LOG_FILE}.\n")
    uia = comtypes.client.CreateObject(CLSID_UIAUTOMATION, interface=UIA.IUIAutomation)
    previous, total = read_meeting_buttons(uia)
    log(f"START  windows={list(previous) or 'none found'} readable-buttons={total}")
    for title, names in previous.items():
        log(f"       {title}: {names or 'no mic button found'}")
    last_beat = time.time()

    # 2. Check once per second and print a line whenever a button name changes
    try:
        while True:
            time.sleep(CHECK_SECONDS)
            try:
                current, total = read_meeting_buttons(uia)
            except comtypes.COMError:
                continue
            if current != previous:
                for title, names in current.items():
                    log(f"CHANGE {title}: {names or 'no mic button found'}")
                if not current:
                    log("CHANGE no meeting window found")
                previous = current
                last_beat = time.time()

            # 3. Print a "still watching" line every few seconds
            elif time.time() - last_beat >= HEARTBEAT_SECONDS:
                log(f"...    readable-buttons={total} {previous if previous else 'no meeting window'}")
                last_beat = time.time()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
