from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image, ImageGrab, ImageStat

ROOT = Path(__file__).resolve().parents[1]
user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32),
        ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32),
        ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16),
        ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32),
        ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32),
        ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


def _window_rect(hwnd: int) -> wintypes.RECT:
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise OSError("GetWindowRect failed")
    return rect


def _capture_window(hwnd: int) -> Image.Image:
    rect = _window_rect(hwnd)
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    hwnd_dc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
    gdi32.SelectObject(mem_dc, bitmap)
    render_flags = 2
    if user32.PrintWindow(hwnd, mem_dc, render_flags) != 1:
        raise OSError(f"PrintWindow failed for hwnd={hwnd}")
    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = 0
    buffer = ctypes.create_string_buffer(width * height * 4)
    if gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(header), 0) == 0:
        raise OSError("GetDIBits failed")
    image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)
    return image


def _capture_screen_region(hwnd: int) -> Image.Image:
    rect = _window_rect(hwnd)
    user32.ShowWindow(hwnd, 5)
    user32.SetForegroundWindow(hwnd)
    time.sleep(2)
    return ImageGrab.grab(
        bbox=(rect.left, rect.top, rect.right, rect.bottom),
        all_screens=True,
    ).convert("RGBA")


def _assess_image(image: Image.Image) -> dict[str, object]:
    rgba = image.convert("RGBA")
    colors = rgba.getcolors(maxcolors=10_000_000)
    unique_colors = len(colors) if colors else -1
    extrema = rgba.getextrema()
    stat = ImageStat.Stat(rgba)
    means = [round(float(value), 3) for value in stat.mean]
    stddev = [round(float(value), 3) for value in stat.stddev]
    max_channel_spread = max(high - low for (low, high) in extrema[:3])
    visually_useful = unique_colors != 1 and max_channel_spread > 8 and max(stddev[:3]) > 3.0
    return {
        "size": [rgba.size[0], rgba.size[1]],
        "unique_colors": unique_colors,
        "extrema": extrema,
        "mean": means,
        "stddev": stddev,
        "max_channel_spread": max_channel_spread,
        "visually_useful": visually_useful,
    }


def _find_window_for_pid(pid: int) -> int:
    best_hwnd = 0
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _lparam):
        nonlocal best_hwnd
        if not user32.IsWindowVisible(hwnd):
            return True
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value != pid:
            return True
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, 256)
        if "Chrome_WidgetWin_1" not in class_name.value:
            return True
        best_hwnd = hwnd
        return False

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return int(best_hwnd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profile-dir", required=True)
    parser.add_argument("--assessment-output")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--wait-seconds", type=int, default=12)
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    assessment_output = Path(args.assessment_output).resolve() if args.assessment_output else output_path.with_name(output_path.stem + "-assessment.json")
    assessment_output.parent.mkdir(parents=True, exist_ok=True)
    profile_dir = Path(args.profile_dir).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    proc = subprocess.Popen(
        [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--new-window",
            f"--window-size={args.width},{args.height}",
            args.url,
        ],
        cwd=ROOT,
    )
    try:
        hwnd = 0
        for _ in range(max(1, args.wait_seconds)):
            time.sleep(1)
            hwnd = _find_window_for_pid(proc.pid)
            if hwnd:
                break
        if not hwnd:
            raise RuntimeError(f"No Edge window handle found for pid={proc.pid}")
        attempts: list[dict[str, object]] = []
        image: Image.Image | None = None
        for method_name, capture_fn in (
            ("image_grab", _capture_screen_region),
            ("print_window", _capture_window),
        ):
            try:
                candidate = capture_fn(hwnd)
                assessment = _assess_image(candidate)
                attempts.append({"method": method_name, **assessment})
                if bool(assessment["visually_useful"]):
                    image = candidate
                    break
                image = candidate
            except Exception as exc:
                attempts.append({"method": method_name, "error": f"{type(exc).__name__}: {exc}"})
        if image is None:
            raise RuntimeError("No capture method produced an image")
        image.save(output_path)
        assessment_output.write_text(
            json.dumps(
                {
                    "url": args.url,
                    "output": str(output_path),
                    "attempts": attempts,
                    "accepted": next((attempt for attempt in attempts if attempt.get("visually_useful")), None),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if not any(bool(attempt.get("visually_useful")) for attempt in attempts):
            raise RuntimeError(f"Capture image failed visual sanity check; see {assessment_output}")
        print(str(output_path))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
