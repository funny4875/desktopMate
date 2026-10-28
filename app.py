import sys
import os
# External TLS debugging settings can point to inaccessible files and prevent
# HTTPS clients from connecting. This application does not export TLS secrets.
os.environ.pop("SSLKEYLOGFILE", None)
import json
import base64
import ctypes
import threading
import time
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QObject, Slot, QEvent, Signal, QThread
from PySide6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QDialog,
    QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtGui import QIcon, QSurfaceFormat

try:
    import speech_recognition as sr
except ImportError:
    sr = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from google import genai
except ImportError:
    genai = None

# Native Windows Constants
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
GCL_STYLE = -26
CS_DROPSHADOW = 0x00020000

ALLOWED_ANIMATIONS = {
    "Angry", "Blush", "Clapping", "Goodbye", "Jump", "LookAround",
    "Sad", "Sleepy", "Surprised", "Thinking",
}
SETTINGS_FILE = Path(os.getenv("APPDATA") or Path.home()) / "vrm_desktop_helper" / "settings.json"


def load_settings():
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_settings(settings):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def model_display_name(model):
    name = getattr(model, "name", str(model))
    display_name = getattr(model, "display_name", "")
    if display_name and display_name != name:
        return f"{name}  ({display_name})"
    return name


def model_api_name(model):
    name = getattr(model, "name", str(model))
    return name.removeprefix("models/")


def conversation_models(models):
    return [model for model in models
            if getattr(model, "name", None)
            and "generateContent" in (getattr(model, "supported_actions", None) or [])
            and not any(term in model_api_name(model).lower()
                        for term in ("image", "tts", "robotics", "computer-use"))]


def gemini_error_message(exc, api_key=""):
    code = getattr(exc, "code", None)
    detail = str(exc).replace(api_key, "[API Key]") if api_key else str(exc)
    if code == 400:
        hint = "請確認 API Key 正確、未失效，以及所在地區支援 Gemini API。"
    elif code in (401, 403):
        hint = "API Key 無效或沒有權限，請確認 Gemini API 已啟用及金鑰限制。"
    elif code == 429:
        hint = "目前配額不足或請求過多，請檢查配額後再試。"
    else:
        hint = "請確認網路、代理伺服器與 API Key，再重新驗證。"
    return f"{hint}\n\n{detail[:1200]}"


class ModelValidationWorker(QThread):
    validated = Signal(object, object)
    failed = Signal(str)

    def __init__(self, api_key, parent=None):
        super().__init__(parent)
        self.api_key = api_key

    def run(self):
        client = None
        try:
            client = genai.Client(api_key=self.api_key, vertexai=False,
                                  http_options={"api_version": "v1beta", "timeout": 20000})
            models = conversation_models(client.models.list())
            if not models:
                raise ValueError("API 未回傳支援文字對話的 generateContent 模型。")
            self.validated.emit(client, models)
        except Exception as exc:
            if client is not None:
                client.close()
            self.failed.emit(gemini_error_message(exc, self.api_key))


class GeminiSetupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DesktopMate — Gemini 設定")
        self.setMinimumWidth(500)
        self.client = None
        self.model = None
        self.worker = None
        settings = load_settings()
        self.saved_model = settings.get("model", "")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("驗證 API Key 並選擇模型後，才會顯示桌面角色。"))
        self.key_input = QLineEdit(settings.get("api_key", ""))
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("貼上 Gemini API Key")
        layout.addWidget(self.key_input)
        self.validate_button = QPushButton("驗證並取得模型")
        self.validate_button.clicked.connect(self.validate_key)
        layout.addWidget(self.validate_button)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        layout.addWidget(self.status)
        self.models = QComboBox()
        self.models.setEnabled(False)
        layout.addWidget(self.models)
        self.start_button = QPushButton("啟動桌面角色")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_character)
        layout.addWidget(self.start_button)
        self.key_input.textChanged.connect(self.invalidate_key)

    def invalidate_key(self):
        self.start_button.setEnabled(False)
        self.models.clear()
        self.models.setEnabled(False)
        if self.client is not None:
            self.client.close()
            self.client = None

    def validate_key(self):
        if genai is None:
            self.status.setText("缺少 google-genai 套件，請重新安裝或打包。")
            return
        api_key = self.key_input.text().strip()
        if not api_key:
            self.status.setText("請先輸入 API Key。")
            return
        self.invalidate_key()
        self.key_input.setEnabled(False)
        self.validate_button.setEnabled(False)
        self.status.setText("正在驗證並取得可用模型…")
        self.worker = ModelValidationWorker(api_key, self)
        self.worker.validated.connect(self.validation_succeeded)
        self.worker.failed.connect(self.status.setText)
        self.worker.finished.connect(self.validation_finished)
        self.worker.start()

    def validation_succeeded(self, client, models):
        self.client = client
        for model in models:
            self.models.addItem(model_display_name(model), model_api_name(model))
        saved_index = self.models.findData(self.saved_model)
        if saved_index >= 0:
            self.models.setCurrentIndex(saved_index)
        self.models.setEnabled(True)
        self.start_button.setEnabled(True)
        self.status.setText(f"驗證成功，取得 {len(models)} 個文字對話模型。請選擇模型後啟動。")

    def validation_finished(self):
        self.key_input.setEnabled(True)
        self.validate_button.setEnabled(True)

    def start_character(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.model = self.models.currentData()
        if self.client is None or not self.model:
            return
        try:
            save_settings({"api_key": self.key_input.text().strip(), "model": self.model})
        except OSError as exc:
            self.status.setText(f"無法儲存設定：{exc}")
            return
        self.accept()

    def reject(self):
        if self.worker is not None and self.worker.isRunning():
            self.status.setText("正在驗證，請等待連線完成或逾時後再關閉。")
            return
        if self.client is not None:
            self.client.close()
        super().reject()


def split_ai_response(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return "Thinking", "我剛剛有點恍神，再說一次給我聽好嗎？"

    animation = lines[0]
    if animation not in ALLOWED_ANIMATIONS:
        animation = "Thinking"
        reply = "\n".join(lines)
    else:
        reply = "\n".join(lines[1:]).strip()

    if not reply:
        reply = "我聽到了，讓我想一下怎麼陪你比較好。"
    return animation, reply


def choose_female_voice(engine):
    voices = engine.getProperty("voices") or []
    preferred_terms = (
        "female", "zira", "huihui", "hanhan", "yating", "hsiaochen",
        "曉臻", "雅婷", "女",
    )
    for voice in voices:
        haystack = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
        if any(term.lower() in haystack for term in preferred_terms):
            engine.setProperty("voice", voice.id)
            return
    if len(voices) > 1:
        engine.setProperty("voice", voices[1].id)

class VRMHost(QObject):
    assistantReplyReady = Signal(str, str)
    assistantStatusReady = Signal(str)

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.assistantReplyReady.connect(self.deliverAssistantReply)
        self.assistantStatusReady.connect(self.deliverAssistantStatus)

    @Slot(int, int)
    def dragWindowBy(self, dx, dy):
        pos = self.window.pos()
        self.window.move(pos.x() + dx, pos.y() + dy)

    @Slot(int, int)
    def fitWindowToModel(self, width, height):
        new_width = max(100, width)
        new_height = max(100, height)
        self.window.resize(new_width, new_height)

    @Slot(str, result=str)
    def readTextFile(self, filename):
        try:
            path = os.path.join(os.path.dirname(__file__), filename)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"Error reading text file {filename}: {e}")
        return ""

    @Slot(str, result=str)
    def readBinaryFile(self, filename):
        try:
            path = os.path.join(os.path.dirname(__file__), filename)
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"Error reading binary file {filename}: {e}")
        return ""

    @Slot(result=str)
    def listVrmaFiles(self):
        try:
            base_dir = os.path.dirname(__file__)
            vrma_dir = os.path.join(base_dir, "VRMA")
            if not os.path.isdir(vrma_dir):
                return "[]"

            files = []
            for filename in sorted(os.listdir(vrma_dir), key=str.lower):
                if filename.lower().endswith(".vrma"):
                    if os.path.splitext(filename)[0].lower() == "relax":
                        continue
                    files.append({
                        "label": os.path.splitext(filename)[0],
                        "path": f"VRMA/{filename}",
                    })
            return json.dumps(files, ensure_ascii=False)
        except Exception as e:
            print(f"Error listing VRMA files: {e}")
        return "[]"

    @Slot()
    def closeWindow(self):
        QApplication.quit()

    @Slot()
    def triggerNextPose(self):
        # 此 Slot 供前端雙擊後呼叫
        print("Received triggerNextPose from JS")
        self.window.cyclePose()

    @Slot(str)
    def updatePose(self, json_data):
        content = ""
        if isinstance(json_data, str) and not json_data.startswith('{'):
            potential_path = os.path.join(os.path.dirname(__file__), json_data)
            if os.path.exists(potential_path):
                try:
                    with open(potential_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Error reading file {potential_path}: {e}")
                    return
        else:
            content = json_data

        safe_content = json.dumps(content)
        self.window.browser.page().runJavaScript(
            f"if(window.applyPoseData) {{ window.applyPoseData({safe_content}); 'OK'; }} else {{ 'ERROR_JS_NOT_READY'; }}",
            lambda result: print(f"JS Update Result: {result}")
        )

    @Slot(str, str)
    def deliverAssistantReply(self, animation, text):
        safe_animation = json.dumps(animation)
        safe_text = json.dumps(text)
        self.window.browser.page().runJavaScript(
            "if(window.playVrmaByName) { "
            f"window.playVrmaByName({safe_animation}); "
            "} "
            "if(window.showAssistantText) { "
            f"window.showAssistantText({safe_text}); "
            "'OK'; "
            "} else { 'ERROR_JS_NOT_READY'; }",
            lambda result: print(f"Assistant JS Result: {result}")
        )

    @Slot(str)
    def deliverAssistantStatus(self, text):
        safe_text = json.dumps(text)
        self.window.browser.page().runJavaScript(
            "if(window.showAssistantText) { "
            f"window.showAssistantText({safe_text}); "
            "'OK'; "
            "} else { 'ERROR_JS_NOT_READY'; }",
            lambda result: print(f"Assistant Status JS Result: {result}")
        )


class InteractiveAssistant:
    def __init__(self, host):
        self.host = host
        self.base_dir = os.path.dirname(__file__)
        self.client = None
        self.model = None
        self.prompt_injection = ""
        self.previous_exchange = None
        self.busy_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.tts_engine = None
        self.tts_lock = threading.Lock()
        self.tts_loop_started = False

    def setup(self, parent):
        missing = []
        if genai is None:
            missing.append("google-genai")
        if sr is None:
            missing.append("SpeechRecognition")
        if pyttsx3 is None:
            missing.append("pyttsx3")
        if missing:
            self.host.assistantStatusReady.emit(
                "缺少套件：" + ", ".join(missing) + "\n請安裝後重新啟動。"
            )
            return False

        self.prompt_injection = self._read_prompt_injection()
        if not self.prompt_injection:
            self.host.assistantStatusReady.emit("找不到 promptInjection.txt，先暫停語音互動。")
            return False

        if self.client is None or not self.model:
            self.host.assistantStatusReady.emit("Gemini 尚未驗證完成。")
            return False

        try:
            self.tts_engine = pyttsx3.init()
            choose_female_voice(self.tts_engine)
            self.tts_engine.setProperty("rate", 185)
        except Exception as exc:
            self.host.assistantStatusReady.emit(f"TTS 初始化失敗：{exc}")
            return False

        return True

    def start(self):
        thread = threading.Thread(target=self._recognition_loop, daemon=True)
        thread.start()
        self.host.assistantStatusReady.emit("我在聽囉，請直接說話。")

    def stop(self):
        self.stop_event.set()

    def _read_prompt_injection(self):
        path = os.path.join(self.base_dir, "promptInjection.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except OSError as exc:
            print(f"Error reading promptInjection.txt: {exc}")
            return ""

    def _build_prompt(self, question):
        parts = [self.prompt_injection]
        if self.previous_exchange:
            parts.append(
                "上一輪對話，只能當作短期上下文：\n"
                f"使用者：{self.previous_exchange['user']}\n"
                f"助理：{self.previous_exchange['assistant']}"
            )
        parts.append(f"使用者這一輪說：{question}")
        return "\n\n".join(parts)

    def _handle_question(self, question):
        if not question.strip():
            return
        if not self.busy_lock.acquire(blocking=False):
            print("Assistant is busy; ignoring recognized speech.")
            return

        try:
            self.host.assistantStatusReady.emit(f"你說：{question}\n我想一下...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=self._build_prompt(question),
            )
            raw_text = getattr(response, "text", "") or ""
            print(raw_text)
            animation, reply = split_ai_response(raw_text)
            self.previous_exchange = {"user": question, "assistant": reply}
            self.host.assistantReplyReady.emit(animation, reply)
            self._speak(reply)
        except Exception as exc:
            message = f"我剛剛連線或回覆時出錯了：{exc}"
            print(message)
            self.host.assistantReplyReady.emit("Surprised", message)
            self._speak(message)
        finally:
            self.busy_lock.release()

    def _speak(self, text):
        if not self.tts_engine:
            return
        with self.tts_lock:
            try:
                if not self.tts_loop_started:
                    self.tts_engine.startLoop(False)
                    self.tts_loop_started = True
                self.tts_engine.say(text)
                while self.tts_engine.isBusy() and not self.stop_event.is_set():
                    self.tts_engine.iterate()
                    time.sleep(0.01)
            except Exception as exc:
                print(f"TTS error: {exc}")

    def _recognition_loop(self):
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 0.5
        recognizer.dynamic_energy_threshold = True

        while not self.stop_event.is_set():
            try:
                with sr.Microphone() as source:
                    print("正在調整環境噪音...")
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    print("請開始說話...")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)

                question = recognizer.recognize_google(audio, language="zh-TW")
                print(f"Recognized: {question}")
                threading.Thread(target=self._handle_question, args=(question,), daemon=True).start()
            except sr.WaitTimeoutError:
                pass
            except sr.UnknownValueError:
                pass
            except sr.RequestError as exc:
                print(f"Speech recognition service error: {exc}")
                self.host.assistantStatusReady.emit(f"語音辨識服務錯誤：{exc}")
                time.sleep(3)
            except Exception as exc:
                print(f"Speech recognition error: {exc}")
                self.host.assistantStatusReady.emit(f"語音辨識錯誤：{exc}")
                time.sleep(3)


class TransparentWindow(QMainWindow):
    def __init__(self, client, model):
        super().__init__()
        self.pose_index = 0
        self.poses = ["pose.json", "pose1.json", "pose2.json"]

        # 1. Window setup
        self.setWindowTitle("VRM_Desktop_Helper")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        self.resize(520, 820)

        # 2. WebEngineView setup
        self.browser = QWebEngineView(self)
        self.setCentralWidget(self.browser)
        
        self.browser.page().setBackgroundColor(Qt.transparent)
        self.browser.setAttribute(Qt.WA_TranslucentBackground)
        self.browser.setStyleSheet("background: transparent; border: none;")
        
        self.channel = QWebChannel()
        self.host_obj = VRMHost(self)
        self.channel.registerObject("vrmHost", self.host_obj)
        self.browser.page().setWebChannel(self.channel)
        self.assistant = InteractiveAssistant(self.host_obj)
        self.assistant.client = client
        self.assistant.model = model
        self.assistant_started = False

        # 改用對 focusProxy 安裝過濾器，這在某些系統上更有效
        if self.browser.focusProxy():
            self.browser.focusProxy().installEventFilter(self)
        self.browser.installEventFilter(self)

        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.ShowScrollBars, False)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "index.html"))
        local_url = QUrl.fromLocalFile(file_path)
        self.browser.loadFinished.connect(self.startAssistantAfterLoad)
        self.browser.setUrl(local_url)

    def startAssistantAfterLoad(self, ok):
        if self.assistant_started:
            return
        self.assistant_started = True
        if not ok:
            print("index.html load failed; assistant not started.")
            return
        if self.assistant.setup(self):
            self.assistant.start()

    def eventFilter(self, obj, event):
        # 捕捉雙擊
        if event.type() == QEvent.MouseButtonDblClick:
            print(f"Native Double Click Detected on {obj}")
            if event.button() == Qt.LeftButton:
                self.cyclePose()
                return True
        return super().eventFilter(obj, event)

    def cyclePose(self):
        self.pose_index = (self.pose_index + 1) % len(self.poses)
        target_pose = self.poses[self.pose_index]
        print(f"Switching to Pose: {target_pose}")
        self.host_obj.updatePose(target_pose)

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_native_fixes()

    def closeEvent(self, event):
        self.assistant.stop()
        super().closeEvent(event)

    def apply_native_fixes(self):
        if sys.platform == "win32":
            hwnd = self.winId()
            user32 = ctypes.windll.user32
            class_style = user32.GetClassLongW(hwnd, GCL_STYLE)
            if class_style & CS_DROPSHADOW:
                user32.SetClassLongW(hwnd, GCL_STYLE, class_style & ~CS_DROPSHADOW)
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            style &= ~(WS_CAPTION | WS_THICKFRAME)
            user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)

if __name__ == "__main__":
    os.environ["QTWEBENGINE_WIDGETS_LOG_LEVEL"] = "1"
    fmt = QSurfaceFormat()
    fmt.setAlphaBufferSize(8)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    app = QApplication(sys.argv)
    icon_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    app.setWindowIcon(QIcon(str(icon_dir / 'desktopmate.ico')))
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    setup_dialog = GeminiSetupDialog()
    if setup_dialog.exec() != QDialog.Accepted:
        sys.exit(0)
    window = TransparentWindow(setup_dialog.client, setup_dialog.model)
    app.aboutToQuit.connect(window.assistant.stop)
    window.show()
    app.setQuitOnLastWindowClosed(True)
    sys.exit(app.exec())
