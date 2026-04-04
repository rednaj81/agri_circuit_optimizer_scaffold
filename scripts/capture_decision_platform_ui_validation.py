from __future__ import annotations

import ctypes
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import ImageGrab


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "output" / "decision_platform" / "ui_validation"
README_PATH = OUTPUT_DIR / "README.md"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
URL = "http://127.0.0.1:8050"

WM_CLOSE = 0x0010
SW_RESTORE = 9
HWND_TOPMOST = -1
SWP_SHOWWINDOW = 0x0040

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800

KEYEVENTF_KEYUP = 0x0002
VK_BACK = 0x08
VK_TAB = 0x09
VK_RETURN = 0x0D
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_HOME = 0x24
VK_LEFT = 0x25
VK_UP = 0x26
VK_RIGHT = 0x27
VK_DOWN = 0x28
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_0 = 0x30
VK_1 = 0x31
VK_2 = 0x32
VK_3 = 0x33
VK_4 = 0x34
VK_5 = 0x35
VK_6 = 0x36
VK_7 = 0x37
VK_8 = 0x38
VK_9 = 0x39
VK_A = 0x41


user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def _enum_windows() -> list[WindowInfo]:
    enum_windows = user32.EnumWindows
    is_window_visible = user32.IsWindowVisible
    get_window_text_length = user32.GetWindowTextLengthW
    get_window_text = user32.GetWindowTextW
    get_window_rect = user32.GetWindowRect
    enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    windows: list[WindowInfo] = []

    def foreach(hwnd: int, _lparam: int) -> bool:
        if not is_window_visible(hwnd):
            return True
        length = get_window_text_length(hwnd)
        if length == 0:
            return True
        buffer = ctypes.create_unicode_buffer(length + 1)
        get_window_text(hwnd, buffer, length + 1)
        title = buffer.value
        rect = RECT()
        get_window_rect(hwnd, ctypes.byref(rect))
        windows.append(WindowInfo(hwnd, title, rect.left, rect.top, rect.right, rect.bottom))
        return True

    enum_windows(enum_windows_proc(foreach), 0)
    return windows


def _dash_windows() -> list[WindowInfo]:
    accepted_titles = ("Dash", "127.0.0.1", "127.0.0.1:8050")
    return [window for window in _enum_windows() if any(token in window.title for token in accepted_titles)]


def _error_windows() -> list[WindowInfo]:
    return [window for window in _enum_windows() if "Erro de Aplicativo" in window.title]


def close_existing_dash_windows() -> None:
    for window in _dash_windows():
        user32.PostMessageW(window.hwnd, WM_CLOSE, 0, 0)
    for window in _error_windows():
        user32.PostMessageW(window.hwnd, WM_CLOSE, 0, 0)
    time.sleep(2)


def launch_browser() -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        [
            CHROME_PATH,
            f"--app={URL}",
            "--window-position=0,0",
            "--window-size=1500,1400",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def find_dash_window(timeout_seconds: float = 30.0) -> WindowInfo:
    deadline = time.time() + timeout_seconds
    last_seen: WindowInfo | None = None
    while time.time() < deadline:
        for window in _dash_windows():
            if window.right > 0 and window.bottom > 0:
                last_seen = window
                break
        if last_seen is not None:
            return last_seen
        time.sleep(0.5)
    raise RuntimeError("Dash window not found.")


def focus_and_resize(window: WindowInfo, *, width: int = 1500, height: int = 1400) -> WindowInfo:
    user32.ShowWindow(window.hwnd, SW_RESTORE)
    user32.SetWindowPos(window.hwnd, HWND_TOPMOST, 0, 0, width, height, SWP_SHOWWINDOW)
    user32.SetForegroundWindow(window.hwnd)
    time.sleep(2)
    return find_dash_window(timeout_seconds=5)


def _move_mouse(x: int, y: int) -> None:
    user32.SetCursorPos(x, y)
    time.sleep(0.15)


def click(window: WindowInfo, rel_x: int, rel_y: int, delay: float = 2.0) -> None:
    x = window.left + rel_x
    y = window.top + rel_y
    _move_mouse(x, y)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(delay)


def wheel(window: WindowInfo, rel_x: int, rel_y: int, delta: int, delay: float = 1.5) -> None:
    x = window.left + rel_x
    y = window.top + rel_y
    _move_mouse(x, y)
    user32.mouse_event(MOUSEEVENTF_WHEEL, x, y, delta, 0)
    time.sleep(delay)


def key(vk_code: int, delay: float = 0.08) -> None:
    user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(delay)
    user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(delay)


def chord(*vk_codes: int, delay: float = 0.08) -> None:
    for vk_code in vk_codes:
        user32.keybd_event(vk_code, 0, 0, 0)
        time.sleep(delay)
    for vk_code in reversed(vk_codes):
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
        time.sleep(delay)
    time.sleep(0.2)


def type_digits(text: str) -> None:
    vk_map = {
        "0": VK_0,
        "1": VK_1,
        "2": VK_2,
        "3": VK_3,
        "4": VK_4,
        "5": VK_5,
        "6": VK_6,
        "7": VK_7,
        "8": VK_8,
        "9": VK_9,
    }
    for char in text:
        if char not in vk_map:
            raise ValueError(f"Unsupported typed character: {char!r}")
        key(vk_map[char])


def replace_input(window: WindowInfo, rel_x: int, rel_y: int, value: str, *, settle_seconds: float = 3.0) -> None:
    click(window, rel_x, rel_y, delay=0.5)
    chord(VK_CONTROL, VK_A)
    key(VK_BACK)
    type_digits(value)
    key(VK_RETURN)
    time.sleep(settle_seconds)


def select_next_dropdown_option(window: WindowInfo, rel_x: int, rel_y: int, *, steps: int = 1, settle_seconds: float = 3.0) -> None:
    click(window, rel_x, rel_y, delay=0.5)
    for _ in range(steps):
        key(VK_DOWN)
    key(VK_RETURN)
    time.sleep(settle_seconds)


def capture(window: WindowInfo, filename: str, *, crop_top: int = 0, crop_bottom: int = 0) -> Path:
    current = find_dash_window(timeout_seconds=5)
    bbox = (
        current.left,
        current.top + crop_top,
        current.right,
        current.bottom - crop_bottom,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    ImageGrab.grab(bbox=bbox).save(path)
    return path


def _write_readme(entries: Iterable[tuple[str, str]]) -> None:
    lines = [
        "# UI Validation",
        "",
        f"- URL validada: `{URL}`",
        f"- Pasta de saída: `{OUTPUT_DIR.as_posix()}`",
        "",
        "## Prints",
        "",
    ]
    for name, description in entries:
        lines.append(f"- `{name}`: {description}")
    README_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    close_existing_dash_windows()
    launch_browser()
    time.sleep(15)

    window = focus_and_resize(find_dash_window())
    click(window, 390, 78, delay=4.0)
    shot_01 = capture(window, "01_home_or_initial_state.png")

    click(window, 640, 78, delay=4.0)
    shot_02 = capture(window, "02_catalog_with_default_profile.png")

    replace_input(window, 150, 458, "1200", settle_seconds=4.0)
    replace_input(window, 150, 503, "50", settle_seconds=4.0)
    shot_03 = capture(window, "03_filters_applied.png")

    replace_input(window, 150, 700, "1", settle_seconds=4.0)
    replace_input(window, 150, 747, "0", settle_seconds=4.0)
    shot_04 = capture(window, "04_weights_changed.png")

    select_next_dropdown_option(window, 150, 324, steps=1, settle_seconds=4.0)
    shot_10 = capture(window, "10_profile_changed.png")

    click(window, 1120, 78, delay=4.0)
    select_next_dropdown_option(window, 220, 324, steps=1, settle_seconds=5.0)
    shot_05 = capture(window, "05_selected_candidate_changed.png")
    shot_09 = capture(window, "09_export_or_final_selection_state.png", crop_bottom=250)

    wheel(window, 700, 1100, -3000, delay=2.0)
    shot_06 = capture(window, "06_circuit_view_selected_candidate.png", crop_top=350)

    click(window, 1360, 78, delay=4.0)
    shot_07 = capture(window, "07_score_breakdown_selected_candidate.png")

    click(window, 880, 78, delay=4.0)
    shot_08 = capture(window, "08_comparison_or_decision_view.png")

    entries = [
        (shot_01.name, "Tela inicial na aba de execução com candidato inicial e perfil padrão reportados."),
        (shot_02.name, "Catálogo carregado com o perfil padrão e a visão inicial do ranking."),
        (shot_03.name, "Catálogo após filtros numéricos aplicados."),
        (shot_04.name, "Catálogo após alteração manual dos pesos dinâmicos."),
        (shot_05.name, "Mudança explícita do candidato selecionado na aba de circuito."),
        (shot_06.name, "Visualização 2D do circuito do candidato selecionado."),
        (shot_07.name, "Breakdown do score na aba de escolha final."),
        (shot_08.name, "Visão de comparação entre candidatos."),
        (shot_09.name, "Estado final com candidato atual e ação de exportação disponível."),
        (shot_10.name, "Print extra evidenciando mudança de perfil na UI."),
    ]
    _write_readme(entries)
    print(OUTPUT_DIR)


if __name__ == "__main__":
    main()
