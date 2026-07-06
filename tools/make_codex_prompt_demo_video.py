import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "demo_assets"
SOURCE_FRAMES = ASSETS / "vrma_effect_frames"
OUTPUT_FRAMES = ASSETS / "codex_prompt_demo_frames"
OUTPUT_VIDEO = ASSETS / "codex_vrma_prompt_demo.mp4"

FPS = 15
WIDTH = 1280
HEIGHT = 720


def font(size=32, bold=False):
    candidates = [
        "C:/Windows/Fonts/msjhbd.ttc" if bold else "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = font(46, True)
FONT_SUBTITLE = font(28)
FONT_BODY = font(24)
FONT_SMALL = font(19)
FONT_CODE = font(21)


def wrap_text(draw, text, max_width, fnt):
    lines = []
    for raw_line in text.splitlines():
        if not raw_line:
            lines.append("")
            continue
        current = ""
        for char in raw_line:
            test = current + char
            if draw.textbbox((0, 0), test, font=fnt)[2] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = char
        if current:
            lines.append(current)
    return lines


def background():
    img = Image.new("RGB", (WIDTH, HEIGHT), (20, 22, 27))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        shade = int(18 + y / HEIGHT * 18)
        draw.line([(0, y), (WIDTH, y)], fill=(shade, shade + 2, shade + 7))
    draw.rectangle([0, 0, WIDTH, 84], fill=(28, 31, 38))
    draw.rectangle([0, 84, WIDTH, 88], fill=(66, 132, 180))
    return img


def draw_card(draw, box, fill=(35, 39, 48), outline=(72, 83, 98)):
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=outline, width=1)


def add_header(draw, title, subtitle=None):
    draw.text((56, 24), title, font=FONT_TITLE, fill=(245, 248, 252))
    if subtitle:
        draw.text((58, 96), subtitle, font=FONT_SUBTITLE, fill=(190, 204, 216))


def add_lines(draw, lines, xy, max_width, fnt=FONT_BODY, fill=(232, 236, 241), line_gap=12):
    x, y = xy
    for line in lines:
        wrapped = wrap_text(draw, line, max_width, fnt)
        for part in wrapped:
            draw.text((x, y), part, font=fnt, fill=fill)
            y += fnt.size + line_gap
    return y


def save_frames(frames, start_index):
    for offset, frame in enumerate(frames):
        frame.save(OUTPUT_FRAMES / f"frame_{start_index + offset:05d}.png")
    return start_index + len(frames)


def make_static_frame(title, subtitle, sections):
    img = background()
    draw = ImageDraw.Draw(img)
    add_header(draw, title, subtitle)
    for section in sections:
        draw_card(draw, section["box"], fill=section.get("fill", (35, 39, 48)))
        if section.get("heading"):
            draw.text((section["box"][0] + 24, section["box"][1] + 22), section["heading"], font=FONT_SUBTITLE, fill=(255, 255, 255))
            text_y = section["box"][1] + 70
        else:
            text_y = section["box"][1] + 24
        add_lines(
            draw,
            section["lines"],
            (section["box"][0] + 24, text_y),
            section["box"][2] - section["box"][0] - 48,
            section.get("font", FONT_BODY),
            section.get("text_fill", (232, 236, 241)),
            section.get("line_gap", 12),
        )
    return img


def repeat_frame(img, seconds):
    return [img.copy() for _ in range(int(seconds * FPS))]


def make_recording_frames():
    frame_paths = sorted(SOURCE_FRAMES.glob("frame_*.png"))
    if not frame_paths:
        raise RuntimeError("找不到實機錄影影格，請先執行 tools/record_vrma_menu_demo.py")

    output = []
    for index, path in enumerate(frame_paths):
        img = background()
        draw = ImageDraw.Draw(img)
        draw.text((52, 24), "執行效果錄影", font=FONT_TITLE, fill=(245, 248, 252))
        draw.text((56, 98), "右鍵選單列出 VRMA 資料夾動作，選擇後即時播放", font=FONT_SUBTITLE, fill=(190, 204, 216))

        source = Image.open(path).convert("RGB")
        max_w, max_h = 740, 560
        source.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        sx = 500 + (max_w - source.width) // 2
        sy = 130 + (max_h - source.height) // 2
        draw_card(draw, [sx - 10, sy - 10, sx + source.width + 10, sy + source.height + 10], fill=(8, 10, 14), outline=(92, 112, 132))
        img.paste(source, (sx, sy))

        steps = [
            "1. 啟動 python app.py",
            "2. 右鍵開啟 VRMA 選單",
            "3. 選 Angry / Goodbye",
            "4. 動作立刻套用到 VRM",
        ]
        draw_card(draw, [54, 160, 436, 420], fill=(33, 39, 48))
        draw.text((78, 186), "Demo 重點", font=FONT_SUBTITLE, fill=(255, 255, 255))
        y = 242
        for step in steps:
            draw.text((82, y), step, font=FONT_BODY, fill=(226, 235, 242))
            y += 48
        draw.text((58, 650), f"錄影片段 {index + 1}/{len(frame_paths)}", font=FONT_SMALL, fill=(150, 165, 178))
        output.append(img)
    return output


def encode_video():
    ffmpeg = shutil.which("ffmpeg") or r"C:\Users\ky\AppData\Local\Programs\Thonny\Scripts\ffmpeg.exe"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(OUTPUT_FRAMES / "frame_%05d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(OUTPUT_VIDEO),
        ],
        check=True,
    )


def main():
    ASSETS.mkdir(exist_ok=True)
    OUTPUT_FRAMES.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_FRAMES.glob("frame_*.png"):
        old.unlink()

    frame_index = 0

    intro = make_static_frame(
        "Codex Prompt Demo",
        "把 python_vrm_helper 升級成可播放 vrm-viewer 的 VRMA 動作",
        [
            {
                "box": [70, 170, 1210, 610],
                "heading": "目標",
                "lines": [
                    "基底專案：ai-ky/python_vrm_helper",
                    "參考來源：tk256ailab/vrm-viewer/tree/main",
                    "任務：把 VRMA 動作整合到 Python 桌面 VRM 助手，並用右鍵選單播放。",
                    "素材位置：Downloads/python_vrm_helper-master.zip 與 Downloads/vrm-viewer-main.zip",
                ],
            }
        ],
    )
    frame_index = save_frames(repeat_frame(intro, 3.0), frame_index)

    prompt = make_static_frame(
        "如何下 Prompt",
        "把需求、來源、互動方式與驗收標準一次講清楚",
        [
            {
                "box": [70, 145, 1210, 642],
                "heading": "可直接貼給 Codex 的 prompt",
                "font": FONT_CODE,
                "line_gap": 10,
                "fill": (30, 34, 42),
                "lines": [
                    "請以 ai-ky/python_vrm_helper 為基底，讀取 Downloads 裡的 python_vrm_helper-master.zip。",
                    "參考 tk256ailab/vrm-viewer/tree/main 的 VRMA 載入方式，將 VRMA 資料夾內所有 .vrma 動作整合進 Python 版。",
                    "需求：右鍵點擊角色時顯示選單，選單自動列出 VRMA/*.vrma；點選後播放該動作。",
                    "請保留原本透明視窗、左鍵拖曳、右鍵拖曳旋轉、滾輪縮放與雙擊 pose 切換。",
                    "完成後請執行 python app.py，並展示 Angry 與 Goodbye 的播放效果。",
                ],
            }
        ],
    )
    frame_index = save_frames(repeat_frame(prompt, 5.0), frame_index)

    workflow = make_static_frame(
        "Codex 實作流程",
        "先理解專案，再把網頁版 VRMA 概念移植到 PySide6 WebView",
        [
            {
                "box": [70, 150, 600, 615],
                "heading": "後端 Python",
                "lines": [
                    "解壓專案並檢查 app.py / index.html。",
                    "新增 listVrmaFiles()，掃描 VRMA 資料夾。",
                    "用 QWebChannel 讓前端取得本地 .vrma 清單與二進位內容。",
                ],
            },
            {
                "box": [680, 150, 1210, 615],
                "heading": "前端 Three.js",
                "lines": [
                    "加入 @pixiv/three-vrm-animation。",
                    "使用 VRMAnimationLoaderPlugin 與 createVRMAnimationClip。",
                    "右鍵選單動態建立按鈕，點擊後載入並播放對應 VRMA。",
                    "對缺 specVersion 的 VRMA 做記憶體內補丁。",
                ],
            },
        ],
    )
    frame_index = save_frames(repeat_frame(workflow, 5.0), frame_index)

    filemap = make_static_frame(
        "修改結果",
        "Codex 完成後的專案形狀",
        [
            {
                "box": [70, 145, 1210, 642],
                "heading": "關鍵檔案",
                "font": FONT_CODE,
                "lines": [
                    "app.py",
                    "  - listVrmaFiles(): 回傳 VRMA/*.vrma 清單",
                    "  - readBinaryFile(): 讓 JS 讀取本地 VRM / VRMA",
                    "",
                    "index.html",
                    "  - 動態右鍵選單",
                    "  - VRMAnimationLoaderPlugin + createVRMAnimationClip",
                    "  - patchVrmaSpecVersion(): 修正缺少 specVersion 的 VRMA",
                    "",
                    "VRMA/",
                    "  - Angry, Blush, Clapping, Goodbye, Jump, LookAround, Relax, Sad, Sleepy, Surprised, Thinking",
                ],
            }
        ],
    )
    frame_index = save_frames(repeat_frame(filemap, 5.0), frame_index)

    frame_index = save_frames(make_recording_frames(), frame_index)

    outro = make_static_frame(
        "完成",
        "重新啟動 app.py 後，新增 VRMA 檔只要放入 VRMA/ 就會自動出現在右鍵選單",
        [
            {
                "box": [90, 190, 1190, 560],
                "heading": "驗收重點",
                "lines": [
                    "右鍵點擊：顯示所有 VRMA 動作。",
                    "選擇動作：即時載入並循環播放。",
                    "原互動保留：拖曳、旋轉、縮放、雙擊 pose 切換仍可使用。",
                    "這就是用 Codex 把網頁版 VRMA 功能移植到 Python 桌面助手的完整流程。",
                ],
            }
        ],
    )
    frame_index = save_frames(repeat_frame(outro, 3.0), frame_index)

    encode_video()
    print(OUTPUT_VIDEO)


if __name__ == "__main__":
    main()
