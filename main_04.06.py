import os
import sys
import json
import openai
import pyperclip
import pyttsx3
import pyaudio
import vosk
import threading
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit, QFileDialog, QWidget
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from config import load_encrypted_key, decrypt_key
import qtawesome as qta

# Инициализация движка для озвучивания текста
tts_engine = pyttsx3.init()

def speak_text(text, stop_event):
    """Озвучивает заданный текст."""
    tts_engine.setProperty('rate', 200)
    for word in text.split("."):
        if stop_event.is_set():
            break
        tts_engine.say(word)
        tts_engine.runAndWait()

def stop_speaking(stop_event):
    """Останавливает воспроизведение аудио."""
    stop_event.set()

def recognize_speech():
    """Записывает и распознает речь с микрофона, возвращает распознанный текст."""
    model = "vosk-model-small"

    if not os.path.exists(model):
        print("Vosk model не найдена. Убедитесь, что модель существует и доступна.")
        sys.exit(1)

    vosk_model = vosk.Model(model)
    rec = vosk.KaldiRecognizer(vosk_model, 16000)
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
    stream.start_stream()
    text = ""
    print("Говорите что-нибудь...")
    while True:
        data = stream.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text")
            print("Вы сказали: " + text)
            break
    stream.stop_stream()
    stream.close()
    p.terminate()
    return text

class MainWindow(QMainWindow):
    update_text_signal = pyqtSignal(str)

    def __init__(self):
        super(MainWindow, self).__init__()

        # Настройка интерфейса
        self.setWindowTitle("Генератор кода")
        self.setWindowIcon(QIcon("test1.jpg"))
        self.setGeometry(100, 100, 800, 600)

        self.conversation_history = []
        self.stop_audio_flag = threading.Event()

        layout = QVBoxLayout()

        self.button_generate = QPushButton(qta.icon('fa5s.cogs'), "Генерировать код")
        self.button_generate.clicked.connect(lambda: threading.Thread(target=self.generate_code).start())
        layout.addWidget(self.button_generate)

        self.button_answer = QPushButton(qta.icon('fa5s.question-circle'), "Ответить на вопрос")
        self.button_answer.clicked.connect(lambda: threading.Thread(target=self.answer_question).start())
        layout.addWidget(self.button_answer)

        self.button_play = QPushButton(qta.icon('fa5s.play-circle'), "Прослушать")
        self.button_play.clicked.connect(self.play_generated_code)
        layout.addWidget(self.button_play)

        self.button_stop = QPushButton(qta.icon('fa5s.stop-circle'), "Остановить воспроизведение")
        self.button_stop.clicked.connect(self.stop_audio)
        layout.addWidget(self.button_stop)

        self.button_history = QPushButton(qta.icon('fa5s.history'), "Показать историю")
        self.button_history.clicked.connect(self.show_history)
        layout.addWidget(self.button_history)

        self.button_save_history = QPushButton(qta.icon('fa5s.save'), "Сохранить историю")
        self.button_save_history.clicked.connect(self.save_history_to_file)
        layout.addWidget(self.button_save_history)

        self.button_process_file = QPushButton(qta.icon('fa5s.file-alt'), "Выбрать файл")
        self.button_process_file.clicked.connect(self.process_text_file)
        layout.addWidget(self.button_process_file)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.update_text_signal.connect(self.update_text)

    @pyqtSlot(str)
    def update_text(self, text):
        self.output_text.clear()
        self.output_text.append(text)

    def chat_with_gpt(self, user_message, conversation_history):
        encrypted_api_key, key = load_encrypted_key()
        api_key = decrypt_key(encrypted_api_key, key)
        openai.api_key = api_key
        messages = [{'role': role, 'content': content} for content, role in conversation_history]
        messages.append({'role': 'user', 'content': user_message})
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
            top_p=1,
            stop=None
        )

        response = completion.choices[0].message['content']
        return response

    def generate_code_with_gpt(self, user_message, conversation_history):
        encrypted_api_key, key = load_encrypted_key()
        api_key = decrypt_key(encrypted_api_key, key)
        openai.api_key = api_key
        messages = [{'role': role, 'content': content} for content, role in conversation_history]
        messages.append({'role': 'user', 'content': "Напиши программный код по следующему запросу: " + user_message})
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1024,
            temperature=0.7,
            top_p=1,
            stop=None
        )

        response = completion.choices[0].message['content']
        return response

    def answer_question(self):
        text = recognize_speech()
        answer = self.chat_with_gpt(text, self.conversation_history)
        print("Ответ: ", answer)
        self.update_text_signal.emit(answer)
        pyperclip.copy(answer)
        self.conversation_history.append((text, "user"))
        self.conversation_history.append((answer, "assistant"))

        self.stop_audio_flag.set()
        self.stop_audio_flag = threading.Event()
        threading.Thread(target=speak_text, args=(answer, self.stop_audio_flag)).start()

    def show_history(self):
        """Отображает историю запросов в текстовом поле."""
        self.output_text.clear()
        for idx, entry in enumerate(self.conversation_history, start=1):
            question, role = entry
            self.output_text.append(f"{role} {idx}: \"{question}\"\n\n")

    def process_text_file(self):
        print("Выберите ваш текстовый файл для запроса")
        text = self.read_text_file()
        if text is None:
            print("Файл не выбран")
            return
        threading.Thread(target=self.process_and_display_file_content, args=(text,)).start()

    def process_and_display_file_content(self, text):
        response = self.chat_with_gpt(text, self.conversation_history)
        print("Ответ: ", response)
        self.update_text_signal.emit(response)
        pyperclip.copy(response)
        self.conversation_history.append((text, "user"))
        self.conversation_history.append((response, "assistant"))



    def generate_code(self):
        text = recognize_speech()
        generated_code = self.generate_code_with_gpt(text, self.conversation_history)
        print("Сгенерированный код: ", generated_code)
        self.update_text_signal.emit(generated_code)
        pyperclip.copy(generated_code)
        self.conversation_history.append((text, "user"))
        self.conversation_history.append((generated_code, "assistant"))

        self.stop_audio_flag.set()
        self.stop_audio_flag = threading.Event()
        threading.Thread(target=speak_text, args=(generated_code, self.stop_audio_flag)).start()

    def read_text_file(self):
        """Открывает диалог выбора файла и считывает выбранный текстовый файл."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Текстовые файлы (*.txt)")

        if not file_path:
            return None

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content

    def save_to_file(self, message):
        """Сохраняет сгенерированный код в файл."""
        with open("generated_code.txt", "w") as file:
            file.write(message)

    def save_history_to_file(self):
        """Сохраняет историю запросов в файл."""
        with open("history.txt", "w") as file:
            for idx, entry in enumerate(self.conversation_history, start=1):
                question, role = entry
                file.write(f"{role} {idx}: \"{question}\"\n\n")
        print("История запросов сохранена в файл 'history.txt'")

    def play_generated_code(self):
        if not self.conversation_history:
            print("Нет кода для воспроизведения")
            return

        self.stop_audio_flag.set()
        self.stop_audio_flag = threading.Event()
        threading.Thread(target=speak_text, args=(self.conversation_history[-1][0], self.stop_audio_flag)).start()


    def stop_audio(self):
        """Останавливает воспроизведение аудио."""
        if not self.stop_audio_flag.is_set():
            self.stop_audio_flag.set()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Установка стиля Fusion
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec())





