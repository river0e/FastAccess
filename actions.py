# actions.py
import os
import webbrowser

def execute_command(targets):
    for target in targets:
        if target.startswith("http"):
            webbrowser.open(target)
        elif os.path.exists(target):
            os.startfile(target)
        else:
            print(f"No se pudo abrir: {target}")