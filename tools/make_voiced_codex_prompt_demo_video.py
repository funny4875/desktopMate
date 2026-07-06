import math
import shutil
import subprocess
import time
import wave
from pathlib import Path

import pyttsx3
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "demo_assets"
SOURCE_FRAMES = ASSETS / "vrma_effect_frames"
OUTPUT_FRAMES = ASSETS / "codex_prompt_demo_voiced_frames"
NARRATION_DIR = ASSETS / "narration"
NARRATION_WAV = ASSETS / "codex_vrma_prompt_demo_narration.wav"
OUTPUT_VIDEO = ASSETS / "codex_vrma_prompt_demo_voiced.mp4"

FPS = 15
WIDTH = 1280
HEIGHT = 720
PAUSE_MS = 450


def get_font(size=30, bold=False):
    candidates = [
        "C:/Windows/Fonts/msjhbd.ttc" if bold else "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


FONT_TITLE = get_font(44, True)
FONT_SUBTITLE = get_font(27)
FONT_BODY = get_font(23)
FONT_SMALL = get_font(18)
FONT_CODE = get_font(20)
FONT_CAPTION = get_font(24, True)


SEGMENTS = [
    {
        "kind": "slide",
        "title": "Demo 目標",
        "subtitle": "用 Codex 把網頁版 VRMA 功能移植到 Python 桌面助手",
        "heading": "這支影片會示範什麼",
        "bullets": [
            "以 ai-ky/python_vrm_helper 為基底專案。",
            "參考 tk256ailab/vrm-viewer 的 VRMA 載入方式。",
            "用 Codex 下 prompt，完成右鍵選單與 VRMA 動作播放。",
            "最後展示實際執行 python app.py 的操作效果。",
        ],
        "narration": "這支影片示範如何透過 Codex 下 prompt，把 python VRM helper 升級成可以播放 VRMA 動作的桌面助手。基底是 ai ky 的 python VRM helper，參考來源是 tk 二五六 ai lab 的 vrm viewer。",
    },
    {
        "kind": "prompt",
        "title": "第一步：把需求寫清楚",
        "subtitle": "prompt 要同時包含基底、參考來源、素材位置與驗收方式",
        "prompt": [
            "請以 ai-ky/python_vrm_helper 為基底，讀取 Downloads 裡的 python_vrm_helper-master.zip。",
            "參考 tk256ailab/vrm-viewer/tree/main 的 VRMA 載入方式。",
            "將 VRMA 資料夾內所有 .vrma 動作整合進 Python 版。",
            "右鍵點擊角色時顯示選單，選單自動列出 VRMA/*.vrma。",
            "點選選單項目後播放該 VRMA，並保留拖曳、旋轉、縮放與雙擊 pose 切換。",
            "完成後執行 python app.py，展示 Angry 與 Goodbye 播放效果。",
        ],
        "narration": "下 prompt 的重點，是讓 Codex 同時知道四件事。第一，基底專案在哪裡。第二，要參考哪個 GitHub 專案。第三，VRMA 素材放在哪裡。第四，完成後要怎麼驗收。這樣 Codex 就不只是猜功能，而是能照著明確目標實作。",
    },
    {
        "kind": "slide",
        "title": "第二步：Codex 讀專案",
        "subtitle": "先理解既有架構，再決定最小修改點",
        "heading": "Codex 會先檢查",
        "bullets": [
            "app.py：PySide6 透明視窗與 QWebChannel。",
            "index.html：Three.js、three-vrm、滑鼠互動與 pose 套用。",
            "VRMA/：Angry、Goodbye、Jump、Relax 等動作檔。",
            "保留既有互動：左鍵拖曳、右鍵拖曳旋轉、滾輪縮放、雙擊切 pose。",
        ],
        "narration": "接著 Codex 會先讀本地專案，而不是直接硬改。它會看到 app.py 負責 PySide6 視窗和 QWebChannel，index.html 負責 Three.js 和 VRM 渲染。這一步的目標，是找出最小而且不破壞原本互動的修改位置。",
    },
    {
        "kind": "split",
        "title": "第三步：移植 VRMA 功能",
        "subtitle": "後端提供檔案清單，前端負責載入與播放",
        "left_heading": "Python 端",
        "left": [
            "新增 listVrmaFiles()。",
            "掃描 VRMA/*.vrma。",
            "透過 QWebChannel 回傳檔名與路徑。",
            "沿用 readBinaryFile() 讀取本地二進位檔。",
        ],
        "right_heading": "JavaScript 端",
        "right": [
            "加入 @pixiv/three-vrm-animation。",
            "註冊 VRMAnimationLoaderPlugin。",
            "createVRMAnimationClip() 轉成 AnimationClip。",
            "建立右鍵選單，點選後播放對應動作。",
        ],
        "narration": "實作時分成兩邊。Python 端新增 list VRMA files，負責掃描 VRMA 資料夾。JavaScript 端加入 three VRM animation，並在右鍵選單中動態建立按鈕。按下按鈕後，讀取對應的 VRMA，轉成 AnimationClip，再交給 AnimationMixer 播放。",
    },
    {
        "kind": "slide",
        "title": "第四步：處理相容性",
        "subtitle": "讓下載來的 VRMA 可以被新版 loader 正常讀取",
        "heading": "遇到的問題與修正",
        "bullets": [
            "部分 VRMA 檔案缺少 VRMC_vrm_animation.specVersion。",
            "loader 會回報 Unknown spec version，導致讀不到 vrmAnimations。",
            "修正方式：載入前在記憶體中補上 specVersion: 1.0。",
            "不修改原始 .vrma 檔案，避免破壞素材。",
        ],
        "narration": "過程中有一個關鍵問題。VRMA 檔案本身是標準 GLB，但是缺少 spec version 欄位。新版 loader 因此無法建立 vrm animations。修正方式是在載入前，於記憶體中補上 spec version 一點零。這樣不會改到原始檔案，也能讓 loader 正常工作。",
    },
    {
        "kind": "recording",
        "title": "第五步：執行程式",
        "subtitle": "啟動 python app.py，確認右鍵選單出現",
        "record_range": [0, 36],
        "steps": [
            "執行 python app.py。",
            "角色以透明桌面助手形式出現。",
            "在角色上按右鍵。",
            "選單列出 VRMA 資料夾裡的所有動作。",
        ],
        "narration": "現在進入實際操作。執行 python app.py 後，角色會以透明桌面助手的形式出現。在角色身上按右鍵，就會看到 Codex 新增的 VRMA 選單。選單內容不是寫死的，而是自動掃描 VRMA 資料夾。",
    },
    {
        "kind": "recording",
        "title": "第六步：播放 Angry",
        "subtitle": "從右鍵選單點選 Angry.vrma",
        "record_range": [36, 82],
        "steps": [
            "點選 Angry。",
            "前端讀取 VRMA/Angry.vrma。",
            "轉成 VRM AnimationClip。",
            "AnimationMixer 開始循環播放。",
        ],
        "narration": "接著點選 Angry。前端會透過 QWebChannel 讀取 VRMA 資料夾裡的 Angry 點 vrma，補上相容性欄位後交給 loader。完成後角色立刻切換成 Angry 動作，並且持續循環播放。",
    },
    {
        "kind": "recording",
        "title": "第七步：切換 Goodbye",
        "subtitle": "再次右鍵，選擇另一個 VRMA 動作",
        "record_range": [82, 139],
        "steps": [
            "再次右鍵開啟選單。",
            "點選 Goodbye。",
            "停止前一個 action。",
            "載入並播放新的 Goodbye 動作。",
        ],
        "narration": "再按一次右鍵，可以選擇另一個動作。這裡切換到 Goodbye。程式會先停止前一個 action，再載入 Goodbye 點 vrma，角色就會改成新的動畫。這證明右鍵選單和 VRMA 播放流程已經串起來。",
    },
    {
        "kind": "slide",
        "title": "完成驗收",
        "subtitle": "流程清楚、互動保留、素材可擴充",
        "heading": "最後確認",
        "bullets": [
            "右鍵點擊會顯示 VRMA 動作選單。",
            "選單自動列出 VRMA/ 裡所有 .vrma 檔。",
            "點選後能即時播放對應動作。",
            "原本的拖曳、旋轉、縮放、雙擊 pose 切換仍保留。",
            "之後新增動作，只要放進 VRMA/ 並重新啟動即可。",
        ],
        "narration": "最後驗收四件事。右鍵選單可以顯示所有 VRMA 動作，點選後可以即時播放，原本的滑鼠互動仍然保留，而且未來只要把新的 VRMA 檔放進 VRMA 資料夾，重新啟動後就會自動出現在選單中。",
    },
]


def wrap_text(draw, text, max_width, fnt):
    result = []
    for raw_line in text.splitlines():
        if not raw_line:
            result.append("")
            continue
        current = ""
        for char in raw_line:
            test = current + char
            width = draw.textbbox((0, 0), test, font=fnt)[2]
            if width <= max_width:
                current = test
            else:
                if current:
                    result.append(current)
                current = char
        if current:
            result.append(current)
    return result


def draw_rounded(draw, box, fill, outline=(78, 91, 108), width=1, radius=10):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def background():
    img = Image.new("RGB", (WIDTH, HEIGHT), (18, 21, 27))
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        shade = int(18 + y / HEIGHT * 20)
        draw.line([(0, y), (WIDTH, y)], fill=(shade, shade + 2, shade + 7))
    draw.rectangle([0, 0, WIDTH, 88], fill=(29, 33, 41))
    draw.rectangle([0, 88, WIDTH, 92], fill=(64, 143, 196))
    return img


def draw_header(draw, title, subtitle):
    draw.text((54, 22), title, font=FONT_TITLE, fill=(248, 250, 252))
    draw.text((58, 100), subtitle, font=FONT_SUBTITLE, fill=(190, 207, 220))


def draw_caption(draw, caption):
    box = [44, 608, WIDTH - 44, 694]
    draw_rounded(draw, box, fill=(6, 10, 16), outline=(88, 118, 148), width=1, radius=8)
    draw.text((66, 626), "旁白", font=FONT_SMALL, fill=(124, 204, 255))
    lines = wrap_text(draw, caption, WIDTH - 190, FONT_CAPTION)
    y = 648
    for line in lines[:2]:
        draw.text((66, y), line, font=FONT_CAPTION, fill=(245, 248, 252))
        y += 30


def draw_bullets(draw, x, y, bullets, max_width, fnt=FONT_BODY, gap=18):
    for bullet in bullets:
        wrapped = wrap_text(draw, bullet, max_width - 36, fnt)
        draw.text((x, y), "•", font=fnt, fill=(107, 200, 255))
        for i, line in enumerate(wrapped):
            draw.text((x + 34, y + i * (fnt.size + 8)), line, font=fnt, fill=(236, 240, 245))
        y += max(1, len(wrapped)) * (fnt.size + 8) + gap
    return y


def draw_slide(segment):
    img = background()
    draw = ImageDraw.Draw(img)
    draw_header(draw, segment["title"], segment["subtitle"])
    draw_rounded(draw, [70, 158, 1210, 580], fill=(34, 39, 49))
    draw.text((98, 188), segment["heading"], font=FONT_SUBTITLE, fill=(255, 255, 255))
    draw_bullets(draw, 104, 246, segment["bullets"], 1040)
    draw_caption(draw, segment["narration"])
    return img


def draw_prompt(segment):
    img = background()
    draw = ImageDraw.Draw(img)
    draw_header(draw, segment["title"], segment["subtitle"])
    draw_rounded(draw, [66, 138, 1214, 584], fill=(29, 34, 43), outline=(82, 95, 112))
    draw.text((94, 164), "可直接貼給 Codex 的 prompt", font=FONT_SUBTITLE, fill=(255, 255, 255))
    y = 218
    for line in segment["prompt"]:
        wrapped = wrap_text(draw, line, 1030, FONT_CODE)
        draw.text((94, y), ">", font=FONT_CODE, fill=(105, 202, 255))
        for part in wrapped:
            draw.text((124, y), part, font=FONT_CODE, fill=(232, 238, 244))
            y += 29
        y += 8
    draw_caption(draw, segment["narration"])
    return img


def draw_split(segment):
    img = background()
    draw = ImageDraw.Draw(img)
    draw_header(draw, segment["title"], segment["subtitle"])
    draw_rounded(draw, [66, 152, 606, 578], fill=(34, 40, 50))
    draw_rounded(draw, [674, 152, 1214, 578], fill=(34, 40, 50))
    draw.text((96, 184), segment["left_heading"], font=FONT_SUBTITLE, fill=(255, 255, 255))
    draw.text((704, 184), segment["right_heading"], font=FONT_SUBTITLE, fill=(255, 255, 255))
    draw_bullets(draw, 100, 244, segment["left"], 450)
    draw_bullets(draw, 708, 244, segment["right"], 450)
    draw_caption(draw, segment["narration"])
    return img


def get_source_frame_paths():
    paths = sorted(SOURCE_FRAMES.glob("frame_*.png"))
    if not paths:
        raise RuntimeError("找不到 demo_assets/vrma_effect_frames，請先執行 tools/record_vrma_menu_demo.py")
    return paths


def draw_recording(segment, source_paths, progress):
    start, end = segment["record_range"]
    end = min(end, len(source_paths))
    start = min(start, end - 1)
    source_index = start + min(end - start - 1, int(progress * max(1, end - start - 1)))
    source = Image.open(source_paths[source_index]).convert("RGB")

    img = background()
    draw = ImageDraw.Draw(img)
    draw_header(draw, segment["title"], segment["subtitle"])

    max_w, max_h = 745, 472
    source.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    sx = 486 + (max_w - source.width) // 2
    sy = 138 + (max_h - source.height) // 2
    draw_rounded(draw, [sx - 10, sy - 10, sx + source.width + 10, sy + source.height + 10], fill=(8, 10, 14), outline=(99, 119, 138))
    img.paste(source, (sx, sy))

    draw_rounded(draw, [54, 154, 438, 580], fill=(33, 39, 49))
    draw.text((82, 184), "操作流程", font=FONT_SUBTITLE, fill=(255, 255, 255))
    y = 242
    for step in segment["steps"]:
        wrapped = wrap_text(draw, step, 300, FONT_BODY)
        draw.text((84, y), "•", font=FONT_BODY, fill=(107, 200, 255))
        for line in wrapped:
            draw.text((116, y), line, font=FONT_BODY, fill=(236, 240, 245))
            y += 31
        y += 16

    draw_caption(draw, segment["narration"])
    return img


def select_voice(engine):
    voices = engine.getProperty("voices")
    for voice in voices:
        if "Hanhan" in voice.name:
            engine.setProperty("voice", voice.id)
            return
    for voice in voices:
        if "zh" in voice.id.lower() or "chinese" in voice.name.lower():
            engine.setProperty("voice", voice.id)
            return


def synthesize(segment, index):
    path = NARRATION_DIR / f"segment_{index:02d}.wav"
    if path.exists():
        path.unlink()

    engine = pyttsx3.init()
    select_voice(engine)
    engine.setProperty("rate", 158)
    engine.setProperty("volume", 1.0)
    engine.save_to_file(segment["narration"], str(path))
    engine.runAndWait()

    deadline = time.time() + 10
    while time.time() < deadline:
        if path.exists() and path.stat().st_size > 1024:
            return path
        time.sleep(0.1)
    raise RuntimeError(f"TTS 輸出失敗：{path}")


def wav_duration(path):
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


def save_frame(img, index):
    img.save(OUTPUT_FRAMES / f"frame_{index:05d}.png")


def append_segment_frames(frame_index, segment, duration, source_paths):
    frame_count = max(1, math.ceil(duration * FPS))
    for i in range(frame_count):
        progress = i / max(1, frame_count - 1)
        if segment["kind"] == "slide":
            frame = draw_slide(segment)
        elif segment["kind"] == "prompt":
            frame = draw_prompt(segment)
        elif segment["kind"] == "split":
            frame = draw_split(segment)
        elif segment["kind"] == "recording":
            frame = draw_recording(segment, source_paths, progress)
        else:
            raise ValueError(segment["kind"])
        save_frame(frame, frame_index)
        frame_index += 1
    return frame_index


def concat_audio(paths):
    combined = AudioSegment.silent(duration=0)
    for path in paths:
        combined += AudioSegment.from_wav(path)
        combined += AudioSegment.silent(duration=PAUSE_MS)
    combined.export(NARRATION_WAV, format="wav")
    return len(combined) / 1000


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
            "-i",
            str(NARRATION_WAV),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-shortest",
            str(OUTPUT_VIDEO),
        ],
        check=True,
    )


def main():
    ASSETS.mkdir(exist_ok=True)
    NARRATION_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FRAMES.mkdir(parents=True, exist_ok=True)
    for old in OUTPUT_FRAMES.glob("frame_*.png"):
        old.unlink()

    source_paths = get_source_frame_paths()

    narration_paths = []
    segment_durations = []
    for index, segment in enumerate(SEGMENTS):
        audio_path = synthesize(segment, index)
        narration_paths.append(audio_path)
        segment_durations.append(wav_duration(audio_path) + PAUSE_MS / 1000)

    frame_index = 0
    for segment, duration in zip(SEGMENTS, segment_durations):
        frame_index = append_segment_frames(frame_index, segment, duration, source_paths)

    audio_duration = concat_audio(narration_paths)
    video_duration = frame_index / FPS
    if video_duration + 0.5 < audio_duration:
        raise RuntimeError("影片影格長度短於音訊")

    encode_video()
    print(OUTPUT_VIDEO)


if __name__ == "__main__":
    main()
