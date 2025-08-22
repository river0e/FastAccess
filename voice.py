import re
import speech_recognition as sr
import pyttsx3
import time
from difflib import get_close_matches
import unicodedata
import threading
from PyQt6.QtCore import QObject, pyqtSignal

# Señales para comunicar la GUI
class VoiceSignals(QObject):
    command_detected = pyqtSignal(str)  # mensaje de comando detectado
    status = pyqtSignal(str)            # mensajes de estado (pausa/activado)
    error = pyqtSignal(str)             # errores de voz

signals = VoiceSignals()

# Inicializar motor de voz
engine = pyttsx3.init()
voice_active = True  # estado global

# Función speak en hilo para no bloquear
def speak(text):
    def run():
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            signals.error.emit(f"Error TTS: {e}")
    threading.Thread(target=run, daemon=True).start()

# Alterna la escucha
def toggle_listening():
    global voice_active
    voice_active = not voice_active
    status_msg = "Asistente de voz activado" if voice_active else "Asistente de voz pausado"
    signals.status.emit(status_msg)
    speak(status_msg)
    return voice_active

# Normaliza texto (minúsculas + sin acentos + sin espacios)
def normalize_text(text):
    text = text.lower()
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = text.replace(" ", "")
    return text

# Fuzzy match multiword
def fuzzy_match_multiword(transcription, commands_list):
    transcription_norm = normalize_text(transcription)
    matches = []
    for cmd in commands_list:
        cmd_norm = normalize_text(cmd)
        if cmd_norm in transcription_norm or transcription_norm in cmd_norm:
            matches.append(cmd)
        else:
            close = get_close_matches(transcription_norm, [cmd_norm], n=1, cutoff=0.6)
            if close:
                matches.append(cmd)
    return matches[0] if matches else None

# Listener principal (usa gui siempre actualizado)
def voice_listener(gui):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        signals.status.emit("🎤 Asistente de voz activado. Puedes hablar.")
        speak("Asistente de voz activado. Puedes hablar.")
        time.sleep(1)

        listening_shown = False  # 🔹 control para no repetir "escuchando..."

        while True:
            try:
                if not voice_active:
                    listening_shown = False  # reset para cuando se reactive
                    time.sleep(0.5)
                    continue

                # Mostrar "Escuchando..." solo una vez
                if not listening_shown:
                    signals.status.emit("🎧 Escuchando...")
                    listening_shown = True

                # ⚡ comprobar justo antes de escuchar
                if not voice_active:
                    continue

                audio = recognizer.listen(source)

                # ⚡ volver a comprobar tras capturar audio (por si pausaron en medio)
                if not voice_active:
                    continue

                command = recognizer.recognize_google(audio, language="es-ES").lower()
                signals.command_detected.emit(command)

                # Limpiar palabras irrelevantes
                clean_command = re.sub(
                    r"\b(abrir|abre|abrirme|ir a|quiero|pon|ejecuta|lanza)\b",
                    "",
                    command
                ).strip()

                ejecutado = False
                app_names = list(gui.apps.keys())
                group_names = list(gui.groups.keys())

                # Apps
                matched_app = fuzzy_match_multiword(clean_command, app_names)
                if matched_app:
                    gui.run_action(gui.apps[matched_app])
                    msg = f"✅ Ejecutando {matched_app}"
                    signals.status.emit(msg)
                    speak(msg)
                    ejecutado = True

                # Grupos
                if not ejecutado:
                    matched_group = fuzzy_match_multiword(clean_command, group_names)
                    if matched_group:
                        gui.run_group(gui.groups[matched_group])
                        msg = f"✅ Ejecutando grupo {matched_group}"
                        signals.status.emit(msg)
                        speak(msg)
                        ejecutado = True

                if not ejecutado:
                    msg = "⚠️ No encontré ese comando"
                    signals.status.emit(msg)
                    speak(msg)

            except sr.UnknownValueError:
                msg = "❌ No entendí lo que dijiste"
                signals.error.emit(msg)  # mejor como error
                speak(msg)

            except Exception as e:
                msg = f"⚠️ Error de reconocimiento: {e}"
                signals.error.emit(msg)
                speak("Ocurrió un error en el reconocimiento de voz")