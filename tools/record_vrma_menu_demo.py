import time
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pyautogui
import pygetwindow as gw
from PIL import Image, ImageDraw, ImageFont, ImageGrab


FPS = 15
OUTPUT = Path(__file__).resolve().parents[1] / "demo_assets" / "vrma_effect_recording.mp4"
FRAMES_DIR = Path(__file__).resolve().parents[1] / "demo_assets" / "vrma_effect_frames"


def get_font(size=28):
    for name in ("C:/Windows/Fonts/msjh.ttc", "C:/Windows/Fonts/segoeui.ttf"):
        path = Path(name)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def draw_cursor(draw, x, y, color=(255, 220, 60)):
    r = 10
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color, outline=(0, 0, 0), width=2)
    draw.polygon([(x, y), (x + 9, y + 19), (x + 19, y + 9)], fill=(255, 60, 60), outline=(0, 0, 0))


def draw_label(image, text):
    draw = ImageDraw.Draw(image)
    font = get_font(26)
    pad = 14
    box = [20, 20, image.width - 20, 78]
    draw.rounded_rectangle(box, radius=10, fill=(0, 0, 0, 168), outline=(255, 255, 255, 80), width=1)
    draw.text((box[0] + pad, box[1] + 12), text, fill=(255, 255, 255), font=font)


def wait_for_window(timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        windows = gw.getWindowsWithTitle("VRM_Desktop_Helper")
        if windows:
            return windows[0]
        time.sleep(0.5)
    raise RuntimeError("找不到 VRM_Desktop_Helper 視窗，請先啟動 python app.py")


def capture_frame(region, cursor, label):
    screenshot = ImageGrab.grab(bbox=region).convert("RGBA")
    draw_label(screenshot, label)
    draw = ImageDraw.Draw(screenshot)
    draw_cursor(draw, cursor[0] - region[0], cursor[1] - region[1])
    return np.array(screenshot.convert("RGB"))


def save_frame(frame, frame_index):
    path = FRAMES_DIR / f"frame_{frame_index:05d}.png"
    Image.fromarray(frame).save(path)


def record_segment(frames, seconds, region, cursor, label):
    for _ in range(int(seconds * FPS)):
        frames.append(capture_frame(region, cursor, label))
        time.sleep(1 / FPS)


def encode_video(frame_count):
    ffmpeg = shutil.which("ffmpeg") or r"C:\Users\ky\AppData\Local\Programs\Thonny\Scripts\ffmpeg.exe"
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        str(FPS),
        "-i",
        str(FRAMES_DIR / "frame_%05d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        str(OUTPUT),
    ]
    subprocess.run(cmd, check=True)
    if frame_count <= 0 or not OUTPUT.exists():
        raise RuntimeError("影片輸出失敗")


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for old_frame in FRAMES_DIR.glob("frame_*.png"):
        old_frame.unlink()

    win = wait_for_window()

    if win.left < 80 or win.top < 80:
        try:
            win.moveTo(160, 90)
            time.sleep(0.5)
        except Exception:
            pass
    win = wait_for_window(timeout=5)

    margin = 90
    region = (
        max(0, win.left - margin),
        max(0, win.top - margin),
        min(pyautogui.size().width, win.left + win.width + margin),
        min(pyautogui.size().height, win.top + win.height + margin),
    )

    menu_x = win.left + max(60, min(180, win.width // 3))
    menu_y = win.top + max(90, min(220, win.height // 3))
    cursor = (menu_x, menu_y)

    frames = []
    pyautogui.moveTo(*cursor)
    record_segment(frames, 1.2, region, cursor, "Python VRM Desktop Helper 執行中")

    pyautogui.click(*cursor, button="right")
    record_segment(frames, 1.1, region, cursor, "右鍵開啟 VRMA 動作選單")

    angry_click = (menu_x + 50, menu_y + 18)
    pyautogui.click(*angry_click)
    record_segment(frames, 3.0, region, angry_click, "選擇 Angry.vrma，立即播放動畫")

    pyautogui.moveTo(*cursor)
    pyautogui.click(*cursor, button="right")
    record_segment(frames, 1.0, region, cursor, "再次右鍵，選單自動列出 VRMA 資料夾所有動作")

    goodbye_click = (menu_x + 56, menu_y + 108)
    pyautogui.click(*goodbye_click)
    record_segment(frames, 3.0, region, goodbye_click, "選擇 Goodbye.vrma，切換播放效果")

    for index, frame in enumerate(frames):
        save_frame(frame, index)
    encode_video(len(frames))

    print(OUTPUT)


if __name__ == "__main__":
    main()
