import sys
import os
import platform
import threading
import subprocess
import json
import time
import re

from PyQt6.QtCore import Qt, QPoint, QProcess, QDir, QRect, QSize, QThread, pyqtSignal, QObject
from PyQt6.QtGui import (
    QFont,
    QAction,
    QKeySequence,
    QTextCursor,
    QColor,
    QPainter,
    QTextFormat,
    QFileSystemModel,
    QPixmap,
    QSyntaxHighlighter,
    QTextCharFormat,
)

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QFileDialog,
    QMenuBar,
    QSplitter,
    QPlainTextEdit,
    QTreeView,
    QGraphicsDropShadowEffect,
    QTabWidget,
    QSizePolicy,
    QInputDialog,
    QTabBar,
)

# STT and TTS imports
try:
    import sounddevice as sd
    import numpy as np
    STT_OK = True
    print("STT available")
except ImportError:
    STT_OK = False
    print("STT not available")

try:
    import pyttsx3
    TTS_OK = True
    print("TTS available")
except ImportError:
    TTS_OK = False
    print("TTS not available")

# Whisper STT import
try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
    print("Faster-Whisper available")
except ImportError:
    WHISPER_OK = False
    print("Faster-Whisper not available - install with: pip install faster-whisper")

def detect_language(file_path):
    _, ext = os.path.splitext(file_path or '')
    ext = ext.lower()
    if ext == ".py":
        return "Python"
    if ext in [".cpp", ".cc", ".cxx"]:
        return "C++"
    if ext == ".java":
        return "Java"
    return "Unknown"

# Syntax Highlighter Classes
class PythonSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None, dark_theme=True):
        super().__init__(parent)
        self.dark_theme = dark_theme
        self.highlighting_rules = []
        self.setup_highlighting_rules()

    def setup_highlighting_rules(self):
        self.highlighting_rules = []
        
        if self.dark_theme:
            # Dark theme colors
            keyword_color = QColor(86, 156, 214)      # Blue
            string_color = QColor(206, 145, 120)      # Orange
            comment_color = QColor(106, 153, 85)      # Green
            number_color = QColor(181, 206, 168)      # Light green
            function_color = QColor(220, 220, 170)    # Yellow
            class_color = QColor(78, 201, 176)        # Cyan
        else:
            # Light theme colors
            keyword_color = QColor(0, 0, 255)         # Blue
            string_color = QColor(163, 21, 21)        # Dark red
            comment_color = QColor(0, 128, 0)         # Green
            number_color = QColor(0, 0, 0)            # Black
            function_color = QColor(128, 0, 128)      # Purple
            class_color = QColor(0, 128, 128)         # Teal

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(keyword_color)
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "and", "as", "assert", "break", "class", "continue", "def",
            "del", "elif", "else", "except", "exec", "finally", "for",
            "from", "global", "if", "import", "in", "is", "lambda",
            "not", "or", "pass", "print", "raise", "return", "try",
            "while", "with", "yield", "True", "False", "None"
        ]
        for word in keywords:
            pattern = f"\\b{word}\\b"
            self.highlighting_rules.append((pattern, keyword_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(string_color)
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(comment_color)
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r"#[^\n]*", comment_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(number_color)
        self.highlighting_rules.append((r"\b\d+\.?\d*\b", number_format))

        # Function definitions
        function_format = QTextCharFormat()
        function_format.setForeground(function_color)
        function_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)", function_format))

        # Class definitions
        class_format = QTextCharFormat()
        class_format.setForeground(class_color)
        class_format.setFontWeight(QFont.Weight.Bold)
        self.highlighting_rules.append((r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)", class_format))

    def set_dark_theme(self, dark_theme):
        self.dark_theme = dark_theme
        self.setup_highlighting_rules()
        self.rehighlight()

    def highlightBlock(self, text):
        for pattern, format_obj in self.highlighting_rules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format_obj)

class CppSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None, dark_theme=True):
        super().__init__(parent)
        self.dark_theme = dark_theme
        self.highlighting_rules = []
        self.setup_highlighting_rules()

    def setup_highlighting_rules(self):
        self.highlighting_rules = []
        
        if self.dark_theme:
            keyword_color = QColor(86, 156, 214)
            string_color = QColor(206, 145, 120)
            comment_color = QColor(106, 153, 85)
            number_color = QColor(181, 206, 168)
            function_color = QColor(220, 220, 170)
            preprocessor_color = QColor(155, 155, 155)
        else:
            keyword_color = QColor(0, 0, 255)
            string_color = QColor(163, 21, 21)
            comment_color = QColor(0, 128, 0)
            number_color = QColor(0, 0, 0)
            function_color = QColor(128, 0, 128)
            preprocessor_color = QColor(128, 128, 128)

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(keyword_color)
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "auto", "break", "case", "catch", "char", "class", "const", "continue",
            "default", "delete", "do", "double", "else", "enum", "extern", "float",
            "for", "friend", "goto", "if", "inline", "int", "long", "namespace",
            "new", "operator", "private", "protected", "public", "register", "return",
            "short", "signed", "sizeof", "static", "struct", "switch", "template",
            "this", "throw", "try", "typedef", "union", "unsigned", "virtual",
            "void", "volatile", "while", "bool", "true", "false", "nullptr"
        ]
        for word in keywords:
            pattern = f"\\b{word}\\b"
            self.highlighting_rules.append((pattern, keyword_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(string_color)
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(comment_color)
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r"//[^\n]*", comment_format))
        self.highlighting_rules.append((r"/\*.*?\*/", comment_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(number_color)
        self.highlighting_rules.append((r"\b\d+\.?\d*[fFdDlL]?\b", number_format))

        # Preprocessor directives
        preprocessor_format = QTextCharFormat()
        preprocessor_format.setForeground(preprocessor_color)
        self.highlighting_rules.append((r"#[^\n]*", preprocessor_format))

    def set_dark_theme(self, dark_theme):
        self.dark_theme = dark_theme
        self.setup_highlighting_rules()
        self.rehighlight()

    def highlightBlock(self, text):
        for pattern, format_obj in self.highlighting_rules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format_obj)

class JavaSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None, dark_theme=True):
        super().__init__(parent)
        self.dark_theme = dark_theme
        self.highlighting_rules = []
        self.setup_highlighting_rules()

    def setup_highlighting_rules(self):
        self.highlighting_rules = []
        
        if self.dark_theme:
            keyword_color = QColor(86, 156, 214)
            string_color = QColor(206, 145, 120)
            comment_color = QColor(106, 153, 85)
            number_color = QColor(181, 206, 168)
            function_color = QColor(220, 220, 170)
            annotation_color = QColor(155, 155, 155)
        else:
            keyword_color = QColor(0, 0, 255)
            string_color = QColor(163, 21, 21)
            comment_color = QColor(0, 128, 0)
            number_color = QColor(0, 0, 0)
            function_color = QColor(128, 0, 128)
            annotation_color = QColor(128, 128, 128)

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(keyword_color)
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            "abstract", "assert", "boolean", "break", "byte", "case", "catch",
            "char", "class", "const", "continue", "default", "do", "double",
            "else", "enum", "extends", "final", "finally", "float", "for",
            "goto", "if", "implements", "import", "instanceof", "int", "interface",
            "long", "native", "new", "package", "private", "protected", "public",
            "return", "short", "static", "strictfp", "super", "switch", "synchronized",
            "this", "throw", "throws", "transient", "try", "void", "volatile",
            "while", "true", "false", "null"
        ]
        for word in keywords:
            pattern = f"\\b{word}\\b"
            self.highlighting_rules.append((pattern, keyword_format))

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(string_color)
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", string_format))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(comment_color)
        comment_format.setFontItalic(True)
        self.highlighting_rules.append((r"//[^\n]*", comment_format))
        self.highlighting_rules.append((r"/\*.*?\*/", comment_format))

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(number_color)
        self.highlighting_rules.append((r"\b\d+\.?\d*[fFdDlL]?\b", number_format))

        # Annotations
        annotation_format = QTextCharFormat()
        annotation_format.setForeground(annotation_color)
        self.highlighting_rules.append((r"@[A-Za-z_][A-Za-z0-9_]*", annotation_format))

    def set_dark_theme(self, dark_theme):
        self.dark_theme = dark_theme
        self.setup_highlighting_rules()
        self.rehighlight()

    def highlightBlock(self, text):
        for pattern, format_obj in self.highlighting_rules:
            expression = re.compile(pattern)
            for match in expression.finditer(text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format_obj)

# STT System with Whisper
class STTSystem(QThread):            #Speech to text
    text_recognized = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_listening = False
        self.SAMPLE_RATE = 16000
        self.FRAME_DURATION_MS = 30
        self.MAX_SILENCE_DURATION = 2.0
        self.MIN_RECORD_DURATION = 0.5
        self.DEBUG_MODE = True
        self.MODEL_PATH = "whisper-small-ct2"
        self.DEVICE = "cpu"
        self.LANGUAGE = 'en'
        self.POST_SPEECH_BUFFER = 0.3
        self.model = None
        self.silence_threshold = None
        self.init_whisper_model()

    def init_whisper_model(self):
        if WHISPER_OK:
            try:
                self.status_update.emit("Loading Whisper model...")
                print(f"Loading Whisper model: {self.MODEL_PATH} on {self.DEVICE}")
                self.model = WhisperModel(self.MODEL_PATH, device=self.DEVICE, compute_type="int8")
                self.status_update.emit("Whisper model loaded!")
                print("Whisper model loaded successfully")
            except Exception as e:
                print(f"Failed to load Whisper model: {e}")
                self.status_update.emit(f"Whisper load failed: {e}")
        else:
            print("faster-whisper not available")

    def calibrate_noise_floor(self, duration=1.5):
        if not STT_OK:
            return 0.01
        self.status_update.emit("🛠️ Calibrating ambient noise...")
        print("🛠️ Calibrating ambient noise... Please stay quiet.")
        try:
            samples = int(duration * self.SAMPLE_RATE)
            recording = sd.rec(samples, samplerate=self.SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            rms = np.sqrt(np.mean(recording**2))
            threshold = rms * 1.8
            print(f"📏 Calibrated silence threshold: {threshold:.5f}")
            self.status_update.emit(f"📏 Calibrated threshold: {threshold:.5f}")
            return threshold
        except Exception as e:
            print(f"Calibration error: {e}")
            return 0.01

    def trim_silence(self, audio, threshold):
        indices = np.where(np.abs(audio) > threshold)[0]
        if indices.size == 0:
            return np.array([], dtype='float32')
        return audio[indices[0]:indices[-1] + 1]

    def record_until_silence_energy(self, silence_threshold):
        if not STT_OK:
            return np.array([], dtype='float32')
        print("🎙️ Listening (speak now)...")
        self.status_update.emit("🎙️ Listening...")
        frame_len = int(self.SAMPLE_RATE * (self.FRAME_DURATION_MS / 1000))
        audio = []
        start_time = time.time()
        last_spoke_time = start_time
        try:
            with sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1, dtype='float32') as stream:
                while self.is_listening:
                    frame, _ = stream.read(frame_len)
                    frame = frame.flatten()
                    volume = np.sqrt(np.mean(frame**2))
                    current_time = time.time()
                    if self.DEBUG_MODE:
                        debug_msg = f"{'🗣️ Speaking' if volume > silence_threshold else '...'} - Vol: {volume:.5f}"
                        print(debug_msg, end='\r')
                    audio.extend(frame)
                    if volume > silence_threshold:
                        last_spoke_time = current_time
                    if (current_time - last_spoke_time > self.MAX_SILENCE_DURATION) and \
                       (current_time - start_time > self.MIN_RECORD_DURATION):
                        extra_frames = int(self.POST_SPEECH_BUFFER * self.SAMPLE_RATE)
                        buffer_data, _ = stream.read(extra_frames)
                        audio.extend(buffer_data.flatten())
                        break
            print("\n✅ Finished recording.")
            self.status_update.emit("✅ Finished recording")
            return np.array(audio, dtype='float32')
        except Exception as e:
            print(f"Recording error: {e}")
            return np.array([], dtype='float32')

    def transcribe_audio(self, audio_data):
        if self.model is None:
            print("Whisper model not loaded")
            return ""
        try:
            self.status_update.emit("🔄 Transcribing...")
            segments, _ = self.model.transcribe(audio_data, language=self.LANGUAGE)
            transcribed_text = " ".join([seg.text for seg in segments]).strip()
            print(f"🎯 Transcription: '{transcribed_text}'")
            return transcribed_text
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""

    def start_listening(self):
        if not STT_OK or not WHISPER_OK:
            self.status_update.emit("STT/Whisper not available")
            return
        if self.silence_threshold is None:
            self.silence_threshold = self.calibrate_noise_floor()
        self.is_listening = True
        if not self.isRunning():
            self.start()

    def stop_listening(self):
        self.is_listening = False
        self.status_update.emit("Voice stopped")

    def run(self):
        self.status_update.emit("💡 Voice assistant ready!")
        print("💡 Voice assistant ready. Speak clearly!")
        while self.is_listening:
            try:
                audio = self.record_until_silence_energy(self.silence_threshold)
                if len(audio) == 0 or np.mean(np.abs(audio)) < 1e-4:
                    print("⚠️ No speech detected.")
                    self.status_update.emit("⚠️ No speech detected")
                    time.sleep(0.5)
                    continue
                audio = self.trim_silence(audio, self.silence_threshold)
                text = self.transcribe_audio(audio)
                if text and len(text.strip()) > 0:
                    print(f"✅ Recognized: '{text}'")
                    self.text_recognized.emit(text.strip())
                    self.status_update.emit("✅ Speech recognized")
                    time.sleep(0.5)
                
                else:
                    self.status_update.emit("🎤 Ready")
                
            except Exception as e:
                print(f"❌ Voice error: {e}")
                self.status_update.emit(f"❌ Voice error: {e}")
                time.sleep(1.0)

# VelCode AI Assistant
class VelVoiceAssistant(QObject):
    response_ready = pyqtSignal(str)
    code_ready = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.chat_history = []
        self.max_history = 30
        self.personality_active = True

    def add_to_history(self, user_msg, ai_response):
        """Add conversation to history with proper ChatGPT-like formatting"""
        clean_response = re.sub(r'```.*?```', '[code provided]', ai_response, flags=re.DOTALL)
        clean_response = clean_response.strip()
        self.chat_history.append(f"User: {user_msg}")
        self.chat_history.append(f"Assistant: {clean_response}")
        if len(self.chat_history) > self.max_history * 2:
            self.chat_history = self.chat_history[-self.max_history * 2:]

    def build_conversation_context(self, current_message, code_context=""):
        """Enhanced context building for ChatGPT-like continuity"""
        context_parts = []
        if self.chat_history:
            context_parts.append("Previous conversation:")
            context_parts.extend(self.chat_history[-10:])
            context_parts.append("")
        if code_context and len(code_context.strip()) > 20:
            context_parts.append("Current code in editor:")
            if len(code_context) > 1000:
                context_parts.append(code_context[:1000] + "...")
            else:
                context_parts.append(code_context)
            context_parts.append("")
        context_parts.append(f"User: {current_message}")
        return "\n".join(context_parts)

    def process(self, text, context=""):
        def worker():
            self.try_human_conversation(text, context)
        threading.Thread(target=worker, daemon=True).start()

    def try_human_conversation(self, text, context=""):
        """Enhanced ChatGPT-style conversational AI with perfect response handling"""
        try:
            self.status_update.emit("🤖 Thinking...")
            conversation_context = self.build_conversation_context(text, context)
            result = subprocess.run(
                ["python", "ai_bridge.py", conversation_context],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout.strip())
                    if data.get("ok"):
                        full_reply = data["reply"].strip()
                        print(f"🤖 Full AI Response: {len(full_reply)} characters")
                        code = self.extract_code_carefully(full_reply)
                        chat_response = self.prepare_chat_response(full_reply, has_code=bool(code))
                        if code:
                            print(f"📝 Sending {len(code)} characters to editor")
                            self.code_ready.emit(code)
                        if chat_response:
                            self.response_ready.emit(chat_response)
                            self.speak(chat_response)
                        self.add_to_history(text, full_reply)
                        self.status_update.emit("✅ Ready")
                        return
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    self.handle_ai_error("Response processing failed")
        except subprocess.TimeoutExpired:
            print("❌ AI timeout")
            self.handle_ai_error("Response took too long - please try again")
        except Exception as e:
            print(f"❌ AI error: {e}")
            self.handle_ai_error(str(e))

    def prepare_chat_response(self, full_response, has_code=False):
        """Prepare clean response for chat panel"""
        chat_response = re.sub(r'```[\w]*.*?```', '', full_response, flags=re.DOTALL)
        chat_response = re.sub(r'\n\s*\n\s*\n', '\n\n', chat_response)
        chat_response = chat_response.strip()
        if has_code and len(chat_response.strip()) < 15:
            chat_response = "I've added the code to your editor. The code is complete and ready to run!"
        return chat_response

    def extract_code_carefully(self, text):
        """Enhanced code extraction with better reliability"""
        print(f"🔍 Extracting code from response...")
        languages = ["python", "py", "cpp", "c\\+\\+", "java", "c", "javascript", "js", "html", "css", "bash", "shell"]
        for lang in languages:
            pattern = f'```{lang}\\s*\\n(.*?)\\n```'
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                code = matches[0].strip()
                if len(code) > 10:
                    print(f"✅ Found {lang} code: {len(code)} chars")
                    return code
        generic_blocks = re.findall(r'```(?:\\w+)?\\s*\\n(.*?)\\n```', text, re.DOTALL)
        if generic_blocks:
            code = generic_blocks[0].strip()
            if len(code) > 10:
                print(f"✅ Found generic code: {len(code)} chars")
                return code
        unclosed_blocks = re.findall(r'```(?:\\w+)?\\s*\\n(.*?)$', text, re.DOTALL | re.MULTILINE)
        if unclosed_blocks:
            code = unclosed_blocks[0].strip()
            if len(code) > 10:
                print(f"✅ Found unclosed code block: {len(code)} chars")
                return code
        print("❌ No code blocks found")
        return ""

    def handle_ai_error(self, error_msg):
        """ChatGPT-like error handling"""
        fallback_responses = [
            "I apologize, but I'm experiencing a technical issue. Could you please try your question again?",
            "Sorry about that! I encountered a small problem. I'm ready to help now - what would you like to work on?",
            "I had a brief technical hiccup, but I'm back! How can I assist you with your coding project?",
            "Apologies for the interruption! I'm working properly now. What can I help you with?"
        ]
        import random
        fallback = random.choice(fallback_responses)
        self.response_ready.emit(fallback)
        self.status_update.emit("❌ Ready (after error)")
        print(f"🔧 Error handled: {error_msg}")

    def speak(self, text):
        """Enhanced TTS with better ChatGPT-like speech"""
        if not self.personality_active:
            return
        def worker():
            try:
                if TTS_OK:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 170)
                    engine.setProperty('volume', 0.85)
                    clean_text = text
                    clean_text = re.sub(r'```.*?```', '', clean_text, flags=re.DOTALL)
                    clean_text = re.sub(r'[`•]', '', clean_text)
                    clean_text = re.sub(r'Here is the code you asked for:?', '', clean_text)
                    clean_text = re.sub(r'\\[.*?\\]', '', clean_text)
                    if clean_text:
                        print(f"🔊 Speaking: {clean_text[:50]}...")
                        engine.say(clean_text)
                        engine.runAndWait()
                        engine.stop()
                        del engine
            except Exception as e:
                print(f"TTS error: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def toggle_personality(self):
        self.personality_active = not self.personality_active
        return self.personality_active

    def clear_history(self):
        self.chat_history.clear()
        print("🧹 Chat history cleared")

# Terminal Widget
class TerminalWidget(QPlainTextEdit):
    def __init__(self, shell_cmd: str, parent=None):
        super().__init__(parent)
        self.shell_cmd = shell_cmd
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.on_ready_read)
        self.process.finished.connect(self.on_process_finished)
        self.setFont(QFont("Consolas", 10))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setUndoRedoEnabled(False)
        self.setCursorWidth(10)
        self.setStyleSheet("border: none; margin: 0; padding: 0;")
        self.user_input_start = 0
        self.command_buffer = ""
        if platform.system() == "Windows":
            self.process.start("powershell.exe", ["-NoLogo"])
        else:
            self.process.start(shell_cmd, ["--noprofile", "--norc"])

    def on_ready_read(self):
        data = self.process.readAllStandardOutput().data().decode(errors="ignore")
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(data)
        self.user_input_start = self.document().characterCount() - 1
        self.moveCursor(QTextCursor.MoveOperation.End)

    def on_process_finished(self):
        self.appendPlainText("\\n[Process Exited]")

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        key = event.key()
        if cursor.position() < self.user_input_start:
            cursor.setPosition(self.document().characterCount() - 1)
            self.setTextCursor(cursor)
        if key == Qt.Key.Key_Backspace:
            if cursor.position() > self.user_input_start:
                super().keyPressEvent(event)
                self.update_command_buffer()
            return
        elif key == Qt.Key.Key_Left:
            if cursor.position() > self.user_input_start:
                super().keyPressEvent(event)
            return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.send_command()
            return
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            return
        elif key == Qt.Key.Key_Home:
            cursor.setPosition(self.user_input_start)
            self.setTextCursor(cursor)
            return
        else:
            super().keyPressEvent(event)
            self.update_command_buffer()

    def update_command_buffer(self):
        cursor = self.textCursor()
        cursor.setPosition(self.user_input_start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        self.command_buffer = cursor.selectedText()

    def send_command(self):
        if self.process.state() != QProcess.ProcessState.Running:
            self.appendPlainText("\\n[Process is not running]")
            return
        self.process.write((self.command_buffer + "\\n").encode())
        self.command_buffer = ""
        self.appendPlainText("")
        self.user_input_start = self.document().characterCount() - 1
        self.moveCursor(QTextCursor.MoveOperation.End)

# Line Number Area for Code Editor
class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

# Enhanced Code Editor with Syntax Highlighting and Auto-Indentation
class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.is_dark_theme = True
        self.current_language = "Unknown"
        self.line_number_area = LineNumberArea(self)

        # Syntax highlighter
        self.syntax_highlighter = None
        self.set_syntax_highlighter("Unknown")

        # Signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        # Setup
        self.update_line_number_area_width(0)
        self.setFont(QFont("Consolas", 13))
        self.setStyleSheet("border: none; margin: 0; padding: 0;")
        self.setTabStopDistance(40)
        self.viewport().update()

        print("🚀 CodeEditor created")

    # ---------------- Syntax Highlighting ----------------
    def set_syntax_highlighter(self, language):
        self.current_language = language

        # remove old highlighter
        if self.syntax_highlighter:
            self.syntax_highlighter.setDocument(None)
            self.syntax_highlighter = None

        if language == "Python":
            self.syntax_highlighter = PythonSyntaxHighlighter(self.document(), self.is_dark_theme)
        elif language == "C++":
            self.syntax_highlighter = CppSyntaxHighlighter(self.document(), self.is_dark_theme)
        elif language == "Java":
            self.syntax_highlighter = JavaSyntaxHighlighter(self.document(), self.is_dark_theme)
        else:
            self.syntax_highlighter = None
        

    # ---------------- Indentation Helpers ----------------
    def get_line_indentation(self, line_text):
        indent_count = 0
        for char in line_text:
            if char == ' ':
                indent_count += 1
            elif char == '\t':
                indent_count += 4
            else:
                break
        return indent_count

    def should_increase_indent(self, line_text):
        line_text = line_text.strip()
        if self.current_language == "Python":
            return (line_text.endswith(':') or
                    line_text.startswith(('if ', 'elif ', 'else:', 'for ', 'while ',
                                          'def ', 'class ', 'try:', 'except', 'finally:', 'with ')))
        elif self.current_language in ["C++", "Java"]:
            return (line_text.endswith('{') or
                    line_text.startswith(('if ', 'else', 'for ', 'while ', 'do ', 'switch ',
                                          'case ', 'default:', 'try ', 'catch ', 'finally ')))
        return False

    def should_decrease_indent(self, line_text):
        line_text = line_text.strip()
        if self.current_language == "Python":
            return line_text.startswith(('except', 'elif ', 'else:', 'finally:'))
        elif self.current_language in ["C++", "Java"]:
            return line_text.startswith(('}', 'case ', 'default:', 'else'))
        return False

    # ---------------- Key Handling ----------------
    def keyPressEvent(self, event):
        cursor = self.textCursor()
        key = event.key()

        # Enter: split line at cursor, indent new line
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current_line = cursor.block().text()
            current_indent = self.get_line_indentation(current_line)
            new_indent = current_indent + 4 if self.should_increase_indent(current_line) else current_indent
            cursor.insertText('\n' + ' ' * new_indent)
            return

        # Tab: indent or insert spaces
        elif key == Qt.Key.Key_Tab:
            if cursor.hasSelection():
                self.indent_selection()
            else:
                cursor.insertText('    ')
            return

        # Shift+Tab: dedent
        elif key == Qt.Key.Key_Backtab:
            self.dedent_selection()
            return

        # Delete: remove one "tab" (4 spaces) if cursor is before spaces
        elif key == Qt.Key.Key_Delete:
            cursor.movePosition(QTextCursor.MoveOperation.Right,
                                QTextCursor.MoveMode.KeepAnchor, 4)
            if cursor.selectedText() == '    ':
                cursor.removeSelectedText()
            else:
                super().keyPressEvent(event)
            return

        # Bracket completion
        elif key in [Qt.Key.Key_ParenLeft, Qt.Key.Key_BracketLeft, Qt.Key.Key_BraceLeft]:
            super().keyPressEvent(event)
            cursor = self.textCursor()
            closing = {
                Qt.Key.Key_ParenLeft: ')',
                Qt.Key.Key_BracketLeft: ']',
                Qt.Key.Key_BraceLeft: '}'
            }
            cursor.insertText(closing[key])
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return

        # Quote completion
        elif event.text() in ['"', "'"]:
            super().keyPressEvent(event)
            cursor = self.textCursor()
            cursor.insertText(event.text())
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return

        # Dedent triggers (Python/C++/Java)
        elif event.text().isalpha():
            super().keyPressEvent(event)
            cursor = self.textCursor()
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            current_line = cursor.selectedText()
            if self.should_decrease_indent(current_line):
                cursor.clearSelection()
                cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
                line_start = cursor.position()
                cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
                line_text = cursor.selectedText()
                if line_text.startswith('    '):
                    cursor.setPosition(line_start)
                    cursor.movePosition(QTextCursor.MoveOperation.Right,
                                        QTextCursor.MoveMode.KeepAnchor, 4)
                    cursor.removeSelectedText()
            return

        # Default behavior
        super().keyPressEvent(event)

    # ---------------- Indent/Dedent ----------------
    def indent_selection(self):
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        while cursor.position() <= end:
            cursor.insertText('    ')
            if not cursor.movePosition(QTextCursor.MoveOperation.Down):
                break
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            end += 4

    def dedent_selection(self):
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        while cursor.position() <= end:
            line_start = cursor.position()
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 4)
            if cursor.selectedText() == '    ':
                cursor.removeSelectedText()
                end -= 4
            else:
                cursor.setPosition(line_start)
            if not cursor.movePosition(QTextCursor.MoveOperation.Down):
                break
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)

    # ---------------- AI Insertion ----------------
    def insert_ai_code(self, code):
        print(f"📝 INSERTING COMPLETE CODE: {len(code)} characters")
        code = code.replace('\\n', '\n').replace('\\t', '\t')
        cursor = self.textCursor()
        current_text = self.toPlainText()
        if current_text and not current_text.endswith('\n'):
            code = '\n\n' + code
        elif current_text:
            code = '\n' + code
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(code)
        self.setTextCursor(cursor)
        print("✅ COMPLETE CODE INSERTED - NO TRIMMING!")

    # ---------------- Theme ----------------
    def set_dark_theme(self, is_dark: bool):
        self.is_dark_theme = is_dark
        if self.syntax_highlighter:
            self.syntax_highlighter.set_dark_theme(is_dark)
        self.line_number_area.update()
        self.update()

    # ---------------- Line Numbers ----------------
    def line_number_area_width(self):
        min_digits, line_count = 5, max(1, self.blockCount())
        digits, temp = 0, line_count
        while temp > 0:
            temp //= 10
            digits += 1
        digits = max(digits, min_digits)
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
                                                self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        if self.is_dark_theme:
            bg_color, text_color, border_color = QColor(45, 45, 45), QColor(255, 255, 255), QColor(100, 100, 100)
        else:
            bg_color, text_color, border_color = QColor(240, 240, 240), QColor(0, 0, 0), QColor(180, 180, 180)

        painter.fillRect(event.rect(), bg_color)
        pen = painter.pen()
        pen.setColor(border_color)
        painter.setPen(pen)
        right_x = self.line_number_area.width() - 1
        painter.drawLine(right_x, event.rect().top(), right_x, event.rect().bottom())

        block = self.firstVisibleBlock()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        font_height = self.fontMetrics().height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block.blockNumber() + 1)
                painter.setPen(text_color)
                painter.drawText(0, int(top), self.line_number_area.width(), font_height,
                                 Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, number)
            block = block.next()
            top, bottom = bottom, bottom + self.blockBoundingRect(block).height()

    def highlight_current_line(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()

            # Aqua with transparency (alpha = 60)
            line_color = QColor(0, 255, 255, 60)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)

            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)


    # ---------------- Painting ----------------
    # def paintEvent(self, event):
    #     # only default painting now, no line highlight
    #     super().paintEvent(event)

# Custom Tab Bar
class CustomTabBar(QTabBar):
    def __init__(self, parent=None): 
        super().__init__(parent)
        self.setTabsClosable(True)

    def tabInserted(self, index):
        close_btn = QPushButton("⛌")
        close_btn.setFixedSize(18, 18)
        close_btn.setStyleSheet(
            "QPushButton { border: none; color: #e53935; background: transparent; }"
            "QPushButton:hover { background: #ffebee; }"
        )
        close_btn.clicked.connect(
            lambda _: self.tabCloseRequested.emit(index)
        )
        self.setTabButton(index, QTabBar.ButtonPosition.RightSide, close_btn)

# Main VelCode IDE
class CustomIDE(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(1200, 700)
        self.old_pos = QPoint()
        self.is_maximized = False
        self.is_dark_theme = True
        self.folder_visible = True
        self.assistant_visible = False
        self.terminal_visible = True
        self.editor_file_paths = {}
        self.dirty_flags = {}   # track unsaved changes per tab
        self.normal_size = self.size()

        # Voice and AI state
        self.voice_active = False
        self.ai_active = True

        # Initialize systems
        print("Initializing Whisper STT System...")
        self.stt_system = STTSystem()
        self.stt_system.text_recognized.connect(self.on_voice_recognized)
        self.stt_system.status_update.connect(self.update_voice_status)

        print("Initializing VelCode Assistant...")
        self.ai_model = VelVoiceAssistant()
        self.ai_model.response_ready.connect(self.on_ai_response)
        self.ai_model.code_ready.connect(self.on_ai_code)
        self.ai_model.status_update.connect(self.update_ai_status)

        print("✅ All systems initialized!")
        self.init_ui()
        self.apply_theme()

    def init_ui(self):
        # Initialize language_label FIRST to prevent AttributeError
        self.language_label = QLabel("Language: Unknown")
        self.language_label.setFont(QFont("Segoe UI", 11))
        self.language_label.setFixedHeight(28)
        self.language_label.setStyleSheet(
            "background: #222; color: #0f0; padding-left:10px;"
            if self.is_dark_theme
            else "background: #f0f0f0; color: #333; padding-left:10px;"
        )

        # Title bar with logo
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(45)

        # Logo
        self.logo_label = QLabel()
        self.load_logo()

        self.title_label = QLabel("VelCode")
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet("padding-left: 8px; background: transparent; border: none;")

        self.btn_min = QPushButton("—")
        self.btn_max_restore = QPushButton("☐")
        self.btn_close = QPushButton("⛌")

        for btn in [self.btn_min, self.btn_max_restore, self.btn_close]:
            btn.setFixedSize(40, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFlat(True)

        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max_restore.clicked.connect(self.toggle_max_restore)
        self.btn_close.clicked.connect(self.close)

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_layout.setSpacing(8)
        title_layout.addWidget(self.logo_label)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.btn_min)
        title_layout.addWidget(self.btn_max_restore)
        title_layout.addWidget(self.btn_close)

        # Menu bar
        self.menu_bar = QMenuBar()
        self.menu_bar.setContentsMargins(0, 0, 0, 0)

        file_menu = self.menu_bar.addMenu("File")
        view_menu = self.menu_bar.addMenu("View")
        run_menu = self.menu_bar.addMenu("Run")
        ai_menu = self.menu_bar.addMenu("AI")

        # File menu actions
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        open_action = QAction("Open File", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        open_folder_action = QAction("Open Folder", self)
        open_folder_action.setShortcut(QKeySequence("Ctrl+Shift+O"))

        file_menu.addActions([new_action, open_action, save_action, save_as_action, close_tab_action, open_folder_action])
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # View menu actions
        toggle_folder_action = QAction("Toggle Folder View", self, checkable=True)
        toggle_folder_action.setChecked(True)
        toggle_folder_action.setShortcut(QKeySequence("Ctrl+F"))
        toggle_assistant_action = QAction("Toggle Assistant Panel", self, checkable=True)
        toggle_assistant_action.setChecked(False)
        toggle_assistant_action.setShortcut(QKeySequence("Ctrl+T"))
        toggle_terminal_action = QAction("Toggle Terminal", self, checkable=True)
        toggle_terminal_action.setChecked(True)
        toggle_terminal_action.setShortcut(QKeySequence("Ctrl+Shift+T"))

        view_menu.addActions([toggle_folder_action, toggle_assistant_action, toggle_terminal_action])

        # Run menu actions
        run_code_action = QAction("Run Code", self)
        run_code_action.setShortcut(QKeySequence("Ctrl+R"))
        run_code_action_f5 = QAction("Run Code (F5)", self)
        run_code_action_f5.setShortcut(QKeySequence(Qt.Key.Key_F5))
        run_menu.addActions([run_code_action, run_code_action_f5])

        # AI menu actions
        toggle_personality_action = QAction("Toggle AI Voice", self, checkable=True)
        toggle_personality_action.setChecked(True)
        clear_history_action = QAction("Clear Chat History", self)
        ai_menu.addActions([toggle_personality_action, clear_history_action])

        # Theme toggle
        theme_toggle_action = QAction("Toggle Dark/Light Theme", self)
        theme_toggle_action.setShortcut(QKeySequence("Ctrl+D"))
        view_menu.addAction(theme_toggle_action)

        # Connect actions
        new_action.triggered.connect(self.new_file)
        open_action.triggered.connect(self.open_file)
        save_action.triggered.connect(self.save_file)
        save_as_action.triggered.connect(self.save_file_as)
        close_tab_action.triggered.connect(self.close_current_tab)
        exit_action.triggered.connect(self.close)
        toggle_folder_action.triggered.connect(self.toggle_folder_panel)
        toggle_assistant_action.triggered.connect(self.toggle_assistant_panel)
        toggle_terminal_action.triggered.connect(self.toggle_terminal_panel)
        run_code_action.triggered.connect(self.run_code)
        run_code_action_f5.triggered.connect(self.run_code)
        theme_toggle_action.triggered.connect(self.toggle_theme)
        open_folder_action.triggered.connect(self.open_folder)
        toggle_personality_action.triggered.connect(self.toggle_ai_personality)
        clear_history_action.triggered.connect(self.clear_ai_history)

        # Toolbar buttons
        self.btn_theme = QPushButton("🌙")
        self.btn_theme.setFixedSize(40, 25)
        font = QFont()
        font.setPointSize(13)
        self.btn_theme.setFont(font)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setFlat(True)
        self.btn_theme.clicked.connect(self.toggle_theme)

        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(8)
        shadow_effect.setOffset(1, 1)
        shadow_effect.setColor(QColor(0, 0, 0, 160))
        self.btn_theme.setGraphicsEffect(shadow_effect)

        self.btn_run = QPushButton("▷")
        self.btn_run.setFixedSize(40, 25)
        font_run = QFont()
        font_run.setPointSize(20)
        self.btn_run.setFont(font_run)
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.setFlat(True)
        self.btn_run.clicked.connect(self.run_code)

        # Voice control button
        self.btn_voice = QPushButton("🎤")
        self.btn_voice.setFixedSize(40, 25)
        font_voice = QFont()
        font_voice.setPointSize(16)
        self.btn_voice.setFont(font_voice)
        self.btn_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_voice.setFlat(True)
        self.btn_voice.clicked.connect(self.toggle_voice)
        self.btn_voice.setStyleSheet("border: none; background: transparent; color: #666;")

        # Menu wrapper
        menu_wrapper = QWidget()
        menu_wrapper.setObjectName("menuWrapper")
        self.menu_wrapper = menu_wrapper

        menu_layout = QHBoxLayout(menu_wrapper)
        menu_layout.setContentsMargins(5, 0, 5, 0)
        menu_layout.setSpacing(0)
        menu_layout.addWidget(self.menu_bar)
        menu_layout.addStretch()
        menu_layout.addWidget(self.btn_voice)
        menu_layout.addWidget(self.btn_theme)
        menu_layout.addWidget(self.btn_run)

        # File system tree
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(QDir.rootPath())
        self.fs_model.setNameFilters(["*.py", "*.cpp", "*.cc", "*.cxx", "*.java"])
        self.fs_model.setNameFilterDisables(False)

        self.tree = QTreeView()
        self.tree.setModel(self.fs_model)
        self.tree.setRootIndex(self.fs_model.index(QDir.homePath()))
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree.setAlternatingRowColors(False)
        self.tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self.tree.setMinimumWidth(200)
        self.tree.clicked.connect(self.tree_item_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.setColumnHidden(1, True)
        self.tree.setColumnHidden(2, True)
        self.tree.setColumnHidden(3, True)
        self.tree.setStyleSheet("border: none; padding: 0; margin: 0;")

        # Tab widget for code editors
        self.tab_widget = QTabWidget()
        # Tab widget styling with bottom border under tabs
        

        self.custom_tab_bar = CustomTabBar()
        self.tab_widget.setTabBar(self.custom_tab_bar)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.tabBarDoubleClicked.connect(self.rename_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Create initial tab
        self.add_new_tab()

        # Assistant panel
        assistant_container = QWidget()
        assistant_layout = QVBoxLayout(assistant_container)
        assistant_layout.setContentsMargins(5, 5, 5, 5)
        assistant_layout.setSpacing(5)

        # Status indicators
        status_layout = QHBoxLayout()
        self.ai_status_label = QLabel("🤖 VelCode: Ready to help!")
        self.ai_status_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.ai_status_label.setStyleSheet("color: #4CAF50; padding: 2px;")

        self.voice_status_label = QLabel("🔇 Voice: Off")
        self.voice_status_label.setFont(QFont("Segoe UI", 9))
        self.voice_status_label.setStyleSheet("color: #666; padding: 2px;")

        status_layout.addWidget(self.ai_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.voice_status_label)

        # Chat area
        self.assistant_chat = QTextEdit()
        self.assistant_chat.setReadOnly(True)
        self.assistant_chat.setFont(QFont("Segoe UI", 11))
        self.assistant_chat.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.assistant_chat.setPlaceholderText("Hi! I'm VelCode Enhanced with syntax highlighting and auto-indentation! What would you like to work on today?")

        # Input area
        self.assistant_input = QTextEdit()
        self.assistant_input.setFont(QFont("Segoe UI", 11))
        self.assistant_input.setFixedHeight(50)
        self.assistant_input.setPlaceholderText("Ask me anything about coding! I give complete, helpful responses with working code!")

        self.assistant_send = QPushButton("Send")
        self.assistant_send.setFixedHeight(30)
        self.assistant_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.assistant_send.clicked.connect(self.assistant_send_message)

        assistant_layout.addLayout(status_layout)
        assistant_layout.addWidget(self.assistant_chat)

        send_layout = QHBoxLayout()
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.setSpacing(0)
        send_layout.addWidget(self.assistant_input)
        send_layout.addWidget(self.assistant_send)

        assistant_layout.addLayout(send_layout)
        assistant_container.setMinimumWidth(250)
        assistant_container.setStyleSheet("border: none;")

        self.assistant_panel = assistant_container
        self.assistant_panel.setVisible(self.assistant_visible)

        # Terminal
        shell = "powershell.exe" if platform.system() == "Windows" else "/bin/bash"
        self.terminal = TerminalWidget(shell)
        self.terminal.setMinimumHeight(160)
        self.terminal.setStyleSheet("border: none; margin: 0; padding: 0;")

        # Splitter setup
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setChildrenCollapsible(False)
        self.h_splitter.setHandleWidth(2)
        self.h_splitter.addWidget(self.tree)
        self.h_splitter.addWidget(self.tab_widget)
        self.h_splitter.addWidget(self.assistant_panel)
        self.h_splitter.setSizes([self.tree.minimumWidth(), 1000, 250])
        self.h_splitter.setContentsMargins(0, 0, 0, 0)
        self.h_splitter.setStyleSheet("QSplitter { padding: 0; margin: 0; border: none; }")
        self.h_splitter.setStretchFactor(0, 0)
        self.h_splitter.setStretchFactor(1, 4)
        self.h_splitter.setStretchFactor(2, 1)

        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setChildrenCollapsible(False)
        self.v_splitter.setHandleWidth(3)
        self.v_splitter.addWidget(self.h_splitter)
        self.v_splitter.addWidget(self.terminal)
        self.v_splitter.setStretchFactor(0, 5)
        self.v_splitter.setStretchFactor(1, 1)
        self.v_splitter.setContentsMargins(0, 0, 0, 0)
        self.v_splitter.setStyleSheet("QSplitter { padding: 0; margin: 0; border: none; }")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(menu_wrapper)
        main_layout.addWidget(self.v_splitter)

        # Add language bar
        language_bar_layout = QHBoxLayout()
        language_bar_layout.setContentsMargins(0, 0, 0, 0)
        language_bar_layout.addWidget(self.language_label)
        main_layout.addLayout(language_bar_layout)

    def load_logo(self):
        """Load VelCode logo with high quality"""
        try:
            logo_paths = [
                r"C:\Users\JAY ABI ADHI\Desktop\Final Year Project\AI Studio\IDE_Logo.png"
            ]
            logo_loaded = False
            for logo_path in logo_paths:
                if os.path.exists(logo_path):
                    print(f"🔍 Found logo: {logo_path}")
                    pixmap = QPixmap(logo_path)
                    if pixmap.isNull():
                        continue
                    target_size = 45
                    device_pixel_ratio = self.devicePixelRatio()
                    if device_pixel_ratio > 1.0:
                        target_size = int(target_size * device_pixel_ratio)
                    scaled_pixmap = pixmap.scaled(
                        target_size, target_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    scaled_pixmap.setDevicePixelRatio(device_pixel_ratio)
                    self.logo_label.setPixmap(scaled_pixmap)
                    self.logo_label.setStyleSheet("""
                        QLabel {
                            border: 0px; background-color: rgba(0,0,0,0); background: transparent;
                            padding: 0px; margin: 0px; outline: none;
                        }
                    """)
                    self.logo_label.setFixedSize(64, 64)
                    self.logo_label.setScaledContents(False)
                    self.logo_label.setContentsMargins(0, -18, 0, 0)
                    self.logo_label.setAutoFillBackground(False)
                    self.logo_label.setFrameStyle(0)
                    print(f"✅ VelCode logo loaded from {logo_path}")
                    logo_loaded = True
                    break

            if not logo_loaded:
                self.logo_label.setText("💧")
                self.logo_label.setFont(QFont("Segoe UI", 32))
                self.logo_label.setStyleSheet("""
                    QLabel {
                        color: #00BCD4; font-weight: bold; border: 0px;
                        background-color: rgba(0,0,0,0); background: transparent;
                        padding: 0px; margin: 0px; outline: none;
                    }
                """)
                self.logo_label.setFixedSize(64, 64)
                self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.logo_label.setAutoFillBackground(False)
                print("⚠️ Logo file not found, using droplet symbol")

        except Exception as e:
            print(f"❌ Error loading logo: {e}")
            self.logo_label.setText("💧")
            self.logo_label.setFont(QFont("Segoe UI", 32))
            self.logo_label.setStyleSheet("""
                QLabel {
                    color: #00BCD4; font-weight: bold; border: 0px;
                    background-color: rgba(0,0,0,0); background: transparent;
                    padding: 0px; margin: 0px; outline: none;
                }
            """)
            self.logo_label.setFixedSize(64, 64)
            self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.logo_label.setAutoFillBackground(False)

    # Voice control methods
    def toggle_voice(self):
        if self.voice_active:
            self.stt_system.stop_listening()
            self.voice_active = False
            self.btn_voice.setStyleSheet("border: none; background: transparent; color: #666;")
            self.update_voice_status("🔇 Voice: Off")
        else:
            self.stt_system.start_listening()
            self.voice_active = True
            self.btn_voice.setStyleSheet("border: none; background: transparent; color: #4CAF50;")
            self.update_voice_status("🎤 Voice: Starting...")

    def on_voice_recognized(self, text):
        print(f"🎤 Voice input: {text}")
        self.assistant_input.setPlainText(text)
        if self.ai_active:
            self.assistant_send_message()

    def update_voice_status(self, status):
        self.voice_status_label.setText(status)
        if "listening" in status.lower() or "🎤" in status:
            self.voice_status_label.setStyleSheet("color: #4CAF50; padding: 2px;")
        elif "error" in status.lower() or "❌" in status:
            self.voice_status_label.setStyleSheet("color: #f44336; padding: 2px;")
        else:
            self.voice_status_label.setStyleSheet("color: #666; padding: 2px;")

    # AI integration methods
    def update_ai_status(self, status):
        self.ai_status_label.setText(f"🤖 VelCode: {status}")
        if "ready" in status.lower() or "✅" in status:
            self.ai_status_label.setStyleSheet("color: #4CAF50; padding: 2px;")
        elif "thinking" in status.lower() or "🤖" in status:
            self.ai_status_label.setStyleSheet("color: #2196F3; padding: 2px;")
        else:
            self.ai_status_label.setStyleSheet("color: #666; padding: 2px;")

    def on_ai_response(self, response):
        print(f"💬 FULL VelCode response: {len(response)} characters - NO TRIMMING")
        self.assistant_chat.append(f"VelCode: {response}")
        cursor = self.assistant_chat.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.assistant_chat.setTextCursor(cursor)

    def on_ai_code(self, code):
        print(f"📝 CODE RECEIVED: {len(code)} characters - NO TRIMMING")
        editor = self.current_editor()
        if editor:
            print("✅ Inserting complete code into editor...")
            editor.insert_ai_code(code)
            self.terminal.appendPlainText("[📝 Complete code inserted by VelCode Enhanced]")
            print("✅ COMPLETE CODE INSERTION FINISHED!")
        else:
            print("❌ NO EDITOR FOUND")

    def is_file_command(self, text):
        """Check for IDE file commands"""
        text_lower = text.lower().strip()
        ide_commands = [
            "open file", "open folder", "save file", "save",
            "run code", "run", "execute", "new file", "close file"
        ]
        for cmd in ide_commands:
            if cmd in text_lower:
                print(f"🔧 IDE command detected: {cmd}")
                return True
        return False

    def handle_file_command(self, text):
        """Handle IDE file commands with perfect ChatGPT-style responses"""
        text_lower = text.lower().strip()
        print(f"🔧 Executing IDE command: {text}")

        if "open folder" in text_lower:
            self.open_folder()
            response = "Perfect! I've opened the folder dialog for you. Select the folder you'd like to work with and we'll get started!"
        elif "open file" in text_lower:
            self.open_file()
            response = "Great! I've opened the file dialog. Choose the file you want to edit and I'll help you with any coding questions!"
        elif "save" in text_lower:
            self.save_file()
            response = "Excellent! I've saved your file. Your work is safe now. What would you like to work on next?"
        elif "run" in text_lower or "execute" in text_lower:
            self.run_code()
            response = "Awesome! I'm running your code now. Let's see what happens! I'm here if you need any debugging help."
        elif "new file" in text_lower:
            self.new_file()
            response = "Perfect! I've created a new file for you. What kind of program would you like to create? I can help with Python, C++, or Java!"
        else:
            response = "Got it! I understand what you're asking for. I'm here to help with whatever you need!"

        self.assistant_chat.append(f"VelCode: {response}")

    def assistant_send_message(self):
        """Process assistant messages - PRESERVE FULL RESPONSES"""
        user_message = self.assistant_input.toPlainText().strip()
        if not user_message:
            return

        print(f"📤 User message: {user_message}")
        self.assistant_chat.append(f"You: {user_message}")
        self.assistant_input.clear()

        if self.is_file_command(user_message):
            print("🔧 IDE command detected - handling directly")
            self.handle_file_command(user_message)
            return

        print("🤖 Sending to VelCode AI - FULL RESPONSE PRESERVED")
        context = ""
        editor = self.current_editor()
        if editor:
            context = editor.toPlainText()

        if self.ai_active:
            self.ai_model.process(user_message, context)

    # AI menu methods
    def toggle_ai_personality(self):
        active = self.ai_model.toggle_personality()
        status = "Voice enabled!" if active else "Voice disabled"
        self.update_ai_status(status)

    def clear_ai_history(self):
        self.ai_model.clear_history()
        self.assistant_chat.clear()
        self.assistant_chat.append("Chat history cleared! Hi there! I'm excited to help you with your next coding project with enhanced syntax highlighting and auto-indentation!")

    # File operations
    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open Folder", QDir.homePath())
        if folder:
            self.fs_model.setRootPath(folder)
            self.tree.setRootIndex(self.fs_model.index(folder))
            print(f"📁 Opened folder: {folder}")

    def set_language_label(self, language):
        if not hasattr(self, 'language_label'):
            return
        color = "#0f0" if self.is_dark_theme else "#333"
        bg = "#222" if self.is_dark_theme else "#f0f0f0"
        self.language_label.setText(f"Language: {language}")
        self.language_label.setStyleSheet(f"background:{bg}; color:{color}; padding-left:10px;")

    def add_new_tab(self, file_path=None, content=""):
        editor = CodeEditor()

        editor.cursorPositionChanged.emit()  # force refresh once

        editor.set_dark_theme(self.is_dark_theme)

        # Detect language (Unknown for untitled)
        language = detect_language(file_path) if file_path else "Unknown"
        editor.set_syntax_highlighter(language)

        # Load file content if provided
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                pass

        editor.setPlainText(content)

        # Force highlight immediately
        if editor.syntax_highlighter:
            editor.syntax_highlighter.rehighlight()

        # Styling
        if self.is_dark_theme:
            editor.setStyleSheet("background-color: #2d2d2d; color: white; border: none; margin: 0; padding: 0;")
        else:
            editor.setStyleSheet("background-color: white; color: black; border: none; margin: 0; padding: 0;")
        
        # Force immediate cursor rect update
        editor.viewport().update()
        # Add tab
        title = os.path.basename(file_path) if file_path else "Untitled"
        index = self.tab_widget.addTab(editor, title)
        self.tab_widget.setCurrentIndex(index)
        self.editor_file_paths[index] = file_path
        self.dirty_flags[index] = False   # initially clean

        # connect textChanged to mark tab dirty
        editor.textChanged.connect(lambda idx=index: self._on_editor_text_changed(idx))

        self.set_language_label(language)

    def rename_tab(self, index):
        if index == -1:
            return
        new_name, ok = QInputDialog.getText(self, "Rename Tab", "New tab name:")
        if ok and new_name:
            self.tab_widget.setTabText(index, new_name)

    def close_tab(self, index):
        if index < 0:
            return
        self.tab_widget.removeTab(index)
        self.editor_file_paths.pop(index, None)
        self.dirty_flags.pop(index, None)

        # reindex maps
        self.editor_file_paths = {
            new_idx: self.editor_file_paths.get(old_idx, None)
            for new_idx, old_idx in enumerate(sorted(self.editor_file_paths.keys()))
        }
        self.dirty_flags = {
            new_idx: self.dirty_flags.get(old_idx, False)
            for new_idx, old_idx in enumerate(sorted(self.dirty_flags.keys()))
        }

        curr_idx = self.tab_widget.currentIndex()
        file_path = self.editor_file_paths.get(curr_idx, None)
        language = detect_language(file_path) if file_path else "Unknown"
        self.set_language_label(language)

    def current_editor(self):
        widget = self.tab_widget.currentWidget()
        if isinstance(widget, CodeEditor):
            return widget
        return None

    def current_file_path(self):
        idx = self.tab_widget.currentIndex()
        return self.editor_file_paths.get(idx, None)

    def save_file(self):
        idx = self.tab_widget.currentIndex()
        if idx == -1:
            return
        path = self.editor_file_paths.get(idx)
        if path is None:
            self.save_file_as()
            return
        editor = self.current_editor()
        if not editor:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            self.terminal.appendPlainText(f"[Saved {path}]")
            print(f"💾 Saved: {path}")

            language = detect_language(path)
            editor.set_syntax_highlighter(language)
            if editor.syntax_highlighter:
                editor.syntax_highlighter.rehighlight()
            self.set_language_label(language)

            # clear dirty flag
            self.dirty_flags[idx] = False
            self._set_tab_title(idx, os.path.basename(path), dirty=False)

        except Exception as e:
            self.terminal.appendPlainText(f"[Failed saving file: {e}]")

    def save_file_as(self):
        idx = self.tab_widget.currentIndex()
        if idx == -1:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save File As", "",
            "Python Files (*.py);;C++ Files (*.cpp *.cc *.cxx);;Java Files (*.java)",
        )
        if not path:
            return
        editor = self.current_editor()
        if not editor:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(editor.toPlainText())
            self.editor_file_paths[idx] = path
            self.terminal.appendPlainText(f"[Saved As {path}]")

            language = detect_language(path)
            editor.set_syntax_highlighter(language)
            editor.cursorPositionChanged.emit()

            if editor.syntax_highlighter:
                editor.syntax_highlighter.rehighlight()
            self.set_language_label(language)

            # clear dirty flag
            self.dirty_flags[idx] = False
            self._set_tab_title(idx, os.path.basename(path), dirty=False)

            print(f"💾 Saved as: {path}")
        except Exception as e:
            self.terminal.appendPlainText(f"[Failed saving file: {e}]")


    def new_file(self):
        self.add_new_tab()
        print("📄 New file created")

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "",
            "Python, C++ and Java Files (*.py *.cpp *.cc *.cxx *.java)",
        )
        if not file_path:
            return
        for idx, path in self.editor_file_paths.items():
            if path == file_path:
                self.tab_widget.setCurrentIndex(idx)
                self.set_language_label(detect_language(file_path))
                return
        self.add_new_tab(file_path)
        print(f"📂 Opened: {file_path}")

    def tree_item_clicked(self, index):
        if not index.isValid():
            return
        file_path = self.fs_model.filePath(index)
        if os.path.isfile(file_path) and file_path.endswith((".py", ".cpp", ".cc", ".cxx", ".java")):
            for idx, path in self.editor_file_paths.items():
                if path == file_path:
                    self.tab_widget.setCurrentIndex(idx)
                    self.set_language_label(detect_language(file_path))
                    return
            self.add_new_tab(file_path)

    def run_code(self):
        editor = self.current_editor()
        if not editor:
            self.terminal.appendPlainText("[No file to run]")
            return
        code_text = editor.toPlainText()
        idx = self.tab_widget.currentIndex()
        file_path = self.editor_file_paths.get(idx)
        if not file_path:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File Before Running",
                "",
                "Python Files (*.py);;C++ Files (*.cpp *.cc *.cxx);;Java Files (*.java)",
            )
            if not path:
                self.terminal.appendPlainText("[Run canceled: file not saved]")
                return
            self.editor_file_paths[idx] = path
            self.tab_widget.setTabText(idx, os.path.basename(path))
            file_path = path
            self.set_language_label(detect_language(file_path))
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code_text)
        except Exception as e:
            self.terminal.appendPlainText(f"[Failed saving file: {e}]")
            return
        language = detect_language(file_path)
        self.set_language_label(language)

        if language == "Python":
            command = f'python "{file_path}"\n'
        elif language == "C++":
            exe_name = os.path.splitext(file_path)[0]
            exe_file = exe_name + (".exe" if platform.system() == "Windows" else "")
            dir_name = os.path.dirname(file_path)
            if platform.system() == "Windows":
                drive = dir_name[0]
                command = (
                    f'{drive}:\n'
                    f'cd "{dir_name}" ; '
                    f'g++ "{file_path}" -o "{exe_file}" ; '
                    f'if ($?) {{ .\\{os.path.basename(exe_file)} }}\n'
                )
            else:
                command = (
                    f'cd "{dir_name}" && '
                    f'g++ "{file_path}" -o "{exe_file}" && '
                    f'./{os.path.basename(exe_file)}\n'
                )
        elif language == "Java":
            dir_name = os.path.dirname(file_path)
            class_name = os.path.splitext(os.path.basename(file_path))[0]
            if platform.system() == "Windows":
                command = (
                    f'cd "{dir_name}" ; '
                    f'javac "{file_path}" ; '
                    f'if ($?) {{ java {class_name} }}\n'
                )
            else:
                command = f'cd "{dir_name}" && javac "{file_path}" && java {class_name}\n'
        else:
            self.terminal.appendPlainText("[Unsupported file type]")
            return

        if self.terminal.process.state() == QProcess.ProcessState.Running:
            self.terminal.process.write(command.encode())
            print(f"▷ Running {language} code")
        else:
            self.terminal.appendPlainText("[Shell process is not running. Please restart IDE.]")

    def close_current_tab(self):
        idx = self.tab_widget.currentIndex()
        if idx != -1:
            self.close_tab(idx)

    def toggle_folder_panel(self):
        self.folder_visible = not self.folder_visible
        self.tree.setVisible(self.folder_visible)

    def toggle_assistant_panel(self):
        self.assistant_visible = not self.assistant_visible
        self.assistant_panel.setVisible(self.assistant_visible)

    def toggle_terminal_panel(self):
        self.terminal_visible = not self.terminal_visible
        self.terminal.setVisible(self.terminal_visible)

    def on_tab_changed(self, index):
        editor = self.current_editor()
        if editor:
            editor.set_dark_theme(self.is_dark_theme)
            file_path = self.editor_file_paths.get(index, None)
            language = detect_language(file_path) if file_path else "Unknown"
            editor.set_syntax_highlighter(language)
            self.set_language_label(language)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_maximized:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def toggle_max_restore(self):
        if self.is_maximized:
            self.showNormal()
            self.resize(self.normal_size)
            self.is_maximized = False
            self.btn_max_restore.setText("☐")
        else:
            self.normal_size = self.size()
            self.showMaximized()
            self.is_maximized = True
            self.btn_max_restore.setText("⮺")

    def toggle_theme(self):
        self.is_dark_theme = not self.is_dark_theme
        self.apply_theme()

    def apply_theme(self):
        if self.is_dark_theme:
            self.setStyleSheet("background-color: #1e1e1e; color: white;")
            self.title_bar.setStyleSheet("background-color: #1a1a1a; border: 1px solid #555555;")
            self.title_label.setStyleSheet("color: white; background: transparent; border: none;")
            self.menu_wrapper.setStyleSheet("background-color: #1f1f1f; border: None")
            self.menu_bar.setStyleSheet(
                "QMenuBar { background-color: transparent; color: white; }"
                "QMenuBar::item:selected { background: #444; }"
                "QMenu { background-color: #2d2d2d; color: white; }"
                "QMenu::item:selected { background: #444; }"
            )
            self.btn_theme.setStyleSheet("border: none; background: transparent; color: white;")
            self.btn_theme.setText("🔆")
            self.btn_run.setStyleSheet("border: none; background: transparent; color: white;")

            if self.voice_active:
                self.btn_voice.setStyleSheet("border: none; background: transparent; color: #4CAF50;")
            else:
                self.btn_voice.setStyleSheet("border: none; background: transparent; color: #666;")

            for i in range(self.tab_widget.count()):
                editor = self.tab_widget.widget(i)
                if isinstance(editor, CodeEditor):
                    editor.set_dark_theme(self.is_dark_theme)
                    editor.setStyleSheet("background-color: #2d2d2d; color: white; border: none; margin: 0; padding: 0;")
            self.tab_widget.setStyleSheet("""
        QTabBar::tab {
            background: #2d2d2d;
            color: white;
            padding: 6px 12px;
        }
        QTabBar::tab:selected {
            background: #3d3d3d;
            border-bottom: 2px solid #00BCD4; /* aqua highlight */
        }
        QTabWidget::pane {
            border-top: 1px solid #444; /* thin line under tab bar */
            top: -1px;
        }
    """)
            self.tree.setStyleSheet(
                "QTreeView { background-color: #1f1f1f; color: white; border: none; padding: 0; margin: 0; }"
                "QTreeView::item:selected { background: #1a1a1a; }"
            )
            self.assistant_panel.setStyleSheet("background-color: #1e1e1e; color: white; border: none;")
            self.assistant_input.setStyleSheet("background-color: #121212; color: white; border: none;")
            self.assistant_chat.setStyleSheet("background-color: #2d2d2d; color: white; border: none;")
            self.terminal.setStyleSheet("background-color: #1f1f1f; color: #00FF00; border: none; margin: 0; padding: 0;")

            for btn in [self.btn_min, self.btn_max_restore, self.btn_close]:
                btn.setStyleSheet("border: none; background: transparent; color: white;")

            self.language_label.setStyleSheet("background: #222; color: #0f0; padding-left:10px;")

        else:
            self.setStyleSheet("background-color: white; color: black; border: none;")
            self.title_bar.setStyleSheet("background-color: #f0f0f0; border: 1px solid #555555;")
            self.title_label.setStyleSheet("color: black; background: transparent; border: none;")
            self.menu_wrapper.setStyleSheet("background-color: #f0f0f0; border: none;")
            self.menu_bar.setStyleSheet(
                "QMenuBar { background-color: transparent; color: black; }"
                "QMenuBar::item:selected { background: #888; color: white; }"
                "QMenu { background-color: white; color: black; }"
                "QMenu::item:selected { background: #888; color: white; }"
            )
            self.btn_theme.setStyleSheet("border: none; background: transparent; color: black;")
            self.btn_theme.setText("🌙")
            self.btn_run.setStyleSheet("border: none; background: transparent; color: black;")

            if self.voice_active:
                self.btn_voice.setStyleSheet("border: none; background: transparent; color: #4CAF50;")
            else:
                self.btn_voice.setStyleSheet("border: none; background: transparent; color: #666;")
            self.tab_widget.setStyleSheet("""
        QTabBar::tab {
            background: #f9f9f9;
            color: black;
            padding: 6px 12px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            border-bottom: 2px solid #00BCD4; /* aqua highlight */
        }
        QTabWidget::pane {
            border-top: 1px solid #ccc; /* light gray line under tab bar */
            top: -1px;
        }
    """)
            for i in range(self.tab_widget.count()):
                editor = self.tab_widget.widget(i)
                if isinstance(editor, CodeEditor):
                    editor.set_dark_theme(self.is_dark_theme)
                    editor.setStyleSheet("background-color: white; color: black; border: none; margin: 0; padding: 0;")

            self.tree.setStyleSheet(
                "QTreeView { background-color: #f0f0f0; color: black; border: none; padding: 0; margin: 0; }"
                "QTreeView::item:selected { background: #ccc; }"
            )
            self.assistant_panel.setStyleSheet("background-color: #f9f9f9; color: black; border: none;")
            self.assistant_input.setStyleSheet("background-color: white; color: black; border: none;")
            self.assistant_chat.setStyleSheet("background-color: white; color: black; border: none;")
            self.terminal.setStyleSheet("background-color: #eee; color: black; border: none; margin: 0; padding: 0;")

            for btn in [self.btn_min, self.btn_max_restore, self.btn_close]:
                btn.setStyleSheet("border: none; background: transparent; color: black;")

            self.language_label.setStyleSheet("background: #f0f0f0; color: #333; padding-left:10px;")

        idx = self.tab_widget.currentIndex()
        file_path = self.editor_file_paths.get(idx, None)
        language = detect_language(file_path) if file_path else "Unknown"
        self.set_language_label(language)

    def closeEvent(self, event):
        print("Shutting down systems...")
        if hasattr(self, 'stt_system'):
            self.stt_system.stop_listening()
            self.stt_system.wait(2000)
        if self.terminal.process.state() == QProcess.ProcessState.Running:
            self.terminal.process.terminate()
            if not self.terminal.process.waitForFinished(300):
                self.terminal.process.kill()
        event.accept()
    def on_tab_changed(self, index):
        if index < 0:
            self.set_language_label("Unknown")
            return
        file_path = self.editor_file_paths.get(index)
        language = detect_language(file_path) if file_path else "Unknown"
        self.set_language_label(language)

        editor = self.current_editor()
        if editor and editor.syntax_highlighter:
            editor.syntax_highlighter.rehighlight()

    def _on_editor_text_changed(self, idx):
        if idx not in range(self.tab_widget.count()):
            return
        if self.dirty_flags.get(idx, False):
            return
        self.dirty_flags[idx] = True
        current_title = self.tab_widget.tabText(idx)
        if not current_title.endswith("*"):
            self.tab_widget.setTabText(idx, current_title + "*")

    def _set_tab_title(self, idx, base_title, dirty=False):
        title = base_title + ("*" if dirty else "")
        if 0 <= idx < self.tab_widget.count():
            self.tab_widget.setTabText(idx, title)



if __name__ == "__main__":
    print("Starting VelCode IDE Enhanced with Syntax Highlighting & Auto-Indentation...")
    app = QApplication(sys.argv)
    window = CustomIDE()
    window.setWindowTitle("VelCode Enhanced - AI-Powered IDE with Syntax Highlighting")
    window.show()
    
    print("🎉 VELCODE IDE ENHANCED READY!")
    print("\n✅ NEW FEATURES:")
    print(" 🌈 Full syntax highlighting for Python, C++, and Java")
    print(" 📝 Smart auto-indentation with language-specific rules")
    print(" 🔧 Automatic bracket and quote completion")
    print(" ⚡ Tab/Shift+Tab for indentation/dedentation")
    print(" 🎨 Theme-aware syntax colors (dark/light mode)")
    print(" 🤖 Perfect ChatGPT-style conversational AI")
    print(" 🎤 Whisper-small-ct2 STT integration")
    print(" 🖼️ High-quality logo support")
    print(" 🔧 Multi-language support with smart detection")
    
    print("\n🎨 SYNTAX HIGHLIGHTING:")
    print(" - Keywords in blue (bold)")
    print(" - Strings in orange/red")
    print(" - Comments in green (italic)")
    print(" - Numbers highlighted")
    print(" - Function/class names emphasized")
    
    print("\n📝 AUTO-INDENTATION:")
    print(" - Smart indentation after colons (:) in Python")
    print(" - Automatic indentation after braces ({) in C++/Java")
    print(" - Dedentation for else/elif/except/finally")
    print(" - Tab key inserts 4 spaces")
    print(" - Shift+Tab removes indentation")
    
    print("\n🚀 USAGE:")
    print(" - Files are auto-detected and highlighted appropriately")
    print(" - Press Enter for smart auto-indentation")
    print(" - Use Tab/Shift+Tab for manual indentation control")
    print(" - Bracket completion works automatically")
    print(" - Switch themes to see different color schemes")
    
    print("\n🎊 Your enhanced coding companion is ready!")
    
    sys.exit(app.exec())