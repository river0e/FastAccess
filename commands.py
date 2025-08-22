import json
import os
import sys
import shutil

def get_commands_path():
    """Devuelve la ruta donde se creará/leerá commands.json en disco."""
    if getattr(sys, 'frozen', False):
        # Cuando corre como .exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Python normal
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "commands.json")

def load_commands():
    """Carga commands.json desde disco. Si no existe, copia el incluido en el exe o crea vacío."""
    path = get_commands_path()
    if not os.path.exists(path):
        try:
            # Intentar copiar el commands.json incluido en el exe
            if getattr(sys, 'frozen', False):
                bundle_path = sys._MEIPASS
                example_path = os.path.join(bundle_path, "commands.json")
            else:
                example_path = os.path.join(os.path.dirname(__file__), "commands.json")
            if os.path.exists(example_path):
                shutil.copy(example_path, path)
            else:
                # Crear vacío si no existe
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"apps": [], "groups": []}, f, indent=4, ensure_ascii=False)
        except Exception:
            # Fallback: crear vacío
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"apps": [], "groups": []}, f, indent=4, ensure_ascii=False)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Normalizar para evitar claves faltantes
    if "apps" not in data:
        data["apps"] = []
    if "groups" not in data:
        data["groups"] = []

    return data

def save_commands(commands):
    """Guarda los comandos en disco."""
    path = get_commands_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(commands, f, indent=4, ensure_ascii=False)
