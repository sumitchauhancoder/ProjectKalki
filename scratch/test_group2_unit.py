import re

SHORTCUTS_MAP = {
    "copy": ("ctrl", "c"),
    "copy that": ("ctrl", "c"),
    "press copy": ("ctrl", "c"),
    "paste": ("ctrl", "v"),
    "paste that": ("ctrl", "v"),
    "press paste": ("ctrl", "v"),
    "cut": ("ctrl", "x"),
    "press cut": ("ctrl", "x"),
    "undo": ("ctrl", "z"),
    "press undo": ("ctrl", "z"),
    "redo": ("ctrl", "y"),
    "press redo": ("ctrl", "y"),
    "select all": ("ctrl", "a"),
    "select everything": ("ctrl", "a"),
    "save": ("ctrl", "s"),
    "save file": ("ctrl", "s"),
    "save this": ("ctrl", "s"),
    "new tab": ("ctrl", "t"),
    "open new tab": ("ctrl", "t"),
    "close tab": ("ctrl", "w"),
    "refresh": ("f5",),
    "reload page": ("f5",),
    "go back": ("alt", "left"),
    "browser back": ("alt", "left"),
    "go forward": ("alt", "right"),
    "browser forward": ("alt", "right"),
    "zoom in": ("ctrl", "+"),
    "zoom out": ("ctrl", "-"),
    "fullscreen": ("f11",),
    "full screen": ("f11",),
    "minimize": ("win", "down"),
    "minimise": ("win", "down"),
    "maximize": ("win", "up"),
    "maximise": ("win", "up"),
    "switch window": ("alt", "tab"),
    "alt tab": ("alt", "tab"),
    "show desktop": ("win", "d"),
    "desktop": ("win", "d"),
    "press enter": ("enter",),
    "hit enter": ("enter",),
    "enter key": ("enter",),
    "press escape": ("esc",),
    "escape": ("esc",),
    "press esc": ("esc",),
    "press space": ("space",),
    "spacebar": ("space",),
    "press tab": ("tab",),
}

ALLOWED_PRESS_KEYS = {
    "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "home", "end", "pageup", "pagedown", "insert", "delete", "backspace",
    "numlock", "capslock", "scrolllock", "printscreen", "pause"
}

def test_commands():
    # Test shortcuts
    assert "copy" in SHORTCUTS_MAP
    assert SHORTCUTS_MAP["press copy"] == ("ctrl", "c")
    assert SHORTCUTS_MAP["refresh"] == ("f5",)

    # Test typing parsing
    test_cases = [
        ("type hello world", "hello world"),
        ("write notes", "notes"),
        ("enter 1234", "1234"),
        ("type this important", "important"),
        ("type", ""),
    ]
    for prompt, expected in test_cases:
        txt = None
        for prefix in ["type this ", "type ", "write ", "enter "]:
            if prompt.startswith(prefix):
                txt = prompt[len(prefix):].strip()
                break
        if prompt in ["type", "write", "enter", "type this"]:
            txt = ""
        assert txt == expected, f"Failed for {prompt}: got {txt}"

    # Test open path detection
    paths = [
        (r"open file C:\test\file.txt", True, False),
        (r"open \\network\share", True, True),
        (r"open calculator", False, False),
        (r"open /var/log", True, False),
    ]
    for p, should_match, is_net in paths:
        m = re.match(r'^(?:open\s+(?:file\s+|folder\s+)?)(.+)$', p)
        if m:
            cand = m.group(1).strip().strip("\"'")
            matched = ("\\" in cand) or ("/" in cand) or bool(re.match(r'^[a-zA-Z]:', cand))
            assert matched == should_match, f"Failed path match on {p}"
            if matched:
                net = cand.startswith(r"\\") or cand.startswith("//")
                assert net == is_net, f"Failed net check on {p}"

    print("All unit logic assertions passed!")

if __name__ == "__main__":
    test_commands()
