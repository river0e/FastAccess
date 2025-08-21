import json
import os
import sys

def get_commands_path():
    """Devuelve la ruta del commands.json, ya sea en desarrollo o en exe."""
    if getattr(sys, 'frozen', False):
        # Cuando corre como .exe
        base_path = os.path.dirname(sys.executable)
    else:
        # Cuando corre en Python normal
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, "commands.json")

def load_commands():
    path = get_commands_path()
    if not os.path.exists(path):
        # Si no existe, lo crea vacío
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_commands(commands):
    path = get_commands_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(commands, f, indent=4, ensure_ascii=False)