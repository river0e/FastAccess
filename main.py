import sys 
from PyQt6.QtWidgets import QApplication
from gui import FastAccessGUI
from voice import voice_listener
import threading

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = FastAccessGUI()
    gui.show()

    # Iniciar escucha de voz en hilo separado (pasamos gui entero)
    t = threading.Thread(target=voice_listener, args=(gui,), daemon=True)
    t.start()

    sys.exit(app.exec())