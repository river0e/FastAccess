# voice.py
import re
import speech_recognition as sr
import pyttsx3
import time

engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()

def voice_listener(apps, groups, run_action_fn, run_group_fn):
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        speak("Asistente de voz activado. Puedes hablar.")
        time.sleep(1)
        while True:
            try:
                print("🎤 Escuchando...")
                audio = recognizer.listen(source)
                command = recognizer.recognize_google(audio, language="es-ES").lower()
                print("🗣️ Comando detectado:", command)

                clean_command = re.sub(
                    r"\b(abrir|abre|abrirme|ir a|quiero|pon|ejecuta|lanza)\b", 
                    "", 
                    command
                ).strip()

                ejecutado = False

                # Apps
                for app_name, app in apps.items():
                    if app_name.lower() in clean_command:
                        run_action_fn(app)
                        speak(f"Ejecutando {app_name}")
                        ejecutado = True
                        break

                # Grupos
                for group_name, group in groups.items():
                    if group_name.lower() in clean_command:
                        run_group_fn(group)
                        speak(f"Ejecutando grupo {group_name}")
                        ejecutado = True
                        break

                if not ejecutado:
                    speak("No encontré ese comando")

            except Exception as e:
                print("Error de voz:", e)
                speak("No entendí lo que dijiste")
