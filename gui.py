# gui.py
import os
import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QMessageBox, QScrollArea, QInputDialog, QStyle
)
from PyQt6.QtCore import Qt
from commands import load_commands, save_commands


class FastAccessGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FastAccess")
        self.setGeometry(200, 200, 640, 640)  # más ancho para 2 columnas

        # Aplicar estilo desde CSS externo
        css_path = os.path.join(os.path.dirname(__file__), "style.css")
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        layout = QVBoxLayout(self)

        # Título
        titulo = QLabel("FastAccess")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        # Layout en grid para los botones de acciones generales
        actions_layout = QGridLayout()
        self.add_btn = QPushButton("Añadir comando")
        self.add_btn.setObjectName("add-button")
        self.add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.add_btn.clicked.connect(self.add_command)

        self.delete_btn = QPushButton("Eliminar comando")
        self.delete_btn.setObjectName("delete-button")
        self.delete_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.delete_btn.clicked.connect(self.delete_command)

        self.add_group_btn = QPushButton("Añadir grupo")
        self.add_group_btn.setObjectName("add-button")
        self.add_group_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        self.add_group_btn.clicked.connect(self.add_group)

        self.delete_group_btn = QPushButton("Eliminar grupo")
        self.delete_group_btn.setObjectName("delete-button")
        self.delete_group_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        self.delete_group_btn.clicked.connect(self.delete_group)

        # Añadir al grid (2 columnas)
        actions_layout.addWidget(self.add_btn, 0, 0)
        actions_layout.addWidget(self.delete_btn, 0, 1)
        actions_layout.addWidget(self.add_group_btn, 1, 0)
        actions_layout.addWidget(self.delete_group_btn, 1, 1)
        layout.addLayout(actions_layout)

        # Scroll para comandos
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QGridLayout(self.container)  # grid para apps y grupos
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Render inicial
        self.load_and_render_commands()

    # ---------- Carga y render ----------
    def load_and_render_commands(self):
        """Cargar comandos y grupos desde JSON y renderizarlos."""
        # Limpiar layout del contenedor
        while self.container_layout.count():
            w = self.container_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        data = load_commands()
        self.apps = {app["name"]: app for app in data.get("apps", [])}
        self.groups = {group["name"]: group for group in data.get("groups", [])}

        row, col = 0, 0

        # Render apps/web (botones individuales)
        for app in self.apps.values():
            btn = QPushButton(app["name"])
            btn.setObjectName("app-button")
            btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            btn.clicked.connect(lambda checked, a=app: self.run_action(a))
            self.container_layout.addWidget(btn, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        # Render grupos
        for group in self.groups.values():
            btn = QPushButton(f"{group['name']} (grupo)")
            btn.setObjectName("group-button")
            btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
            btn.clicked.connect(lambda checked, g=group: self.run_group(g))
            self.container_layout.addWidget(btn, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

    # ---------- Resolución y ejecución ----------
    def execute_target(self, target: str):
        """Abre una URL o ruta local."""
        try:
            if isinstance(target, str) and target.lower().startswith(("http://", "https://")):
                webbrowser.open(target)
            else:
                os.startfile(target)  # ruta local
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{target}\n\n{e}")

    def resolve_item_to_targets(self, item):
        """
        Convierte un item de grupo en una o varias 'targets' abribles.
        """
        targets = []

        # Caso 1: string
        if isinstance(item, str):
            if item in self.apps:
                targets.append(self.apps[item]["action"])
            elif item.lower().startswith(("http://", "https://")):
                targets.append(item)
            elif os.path.exists(item):
                targets.append(item)
            else:
                print(f"[Grupo] Item no válido o desconocido: '{item}'")

        # Caso 2: diccionario {"action": "..."}
        elif isinstance(item, dict):
            action = item.get("action")
            if action:
                if item.get("type") in ("web", "app"):
                    targets.append(action)
                else:
                    if action.lower().startswith(("http://", "https://")) or os.path.exists(action):
                        targets.append(action)
                    else:
                        print(f"[Grupo] Acción no válida en dict: {item}")
            else:
                print(f"[Grupo] Dict sin 'action': {item}")

        return targets

    # ---------- Acciones de botones ----------
    def run_action(self, app):
        """Ejecutar un comando de tipo app o web."""
        self.execute_target(app["action"])

    def run_group(self, group):
        """Ejecutar todos los elementos del grupo."""
        items = group.get("items", [])
        executed = False

        for item in items:
            targets = self.resolve_item_to_targets(item)
            for t in targets:
                self.execute_target(t)
                executed = True

        if not executed:
            QMessageBox.warning(
                self,
                "Grupo vacío",
                f"El grupo '{group.get('name','(sin nombre)')}' no contiene elementos válidos."
            )

    # ---------- Alta/Baja de apps ----------
    def add_command(self):
        """Alta rápida de app/web."""
        name, ok = QInputDialog.getText(self, "Añadir comando", "Nombre: ")
        if not ok or not name.strip():
            return

        type_, ok = QInputDialog.getItem(self, "Tipo", "Tipo:", ["web", "app"], 0, False)
        if not ok:
            return

        action, ok = QInputDialog.getText(
            self, "Acción", "URL (https://...) o ruta local (C:/.../App.exe):"
        )
        if not ok or not action.strip():
            return

        new_app = {"name": name.strip(), "type": type_.strip(), "action": action.strip()}

        # Actualiza memoria y JSON
        self.apps[name.strip()] = new_app
        data = load_commands()
        data.setdefault("apps", [])
        data["apps"].append(new_app)
        save_commands(data)

        self.load_and_render_commands()

    def delete_command(self):
        if not self.apps:
            QMessageBox.information(self, "Eliminar comando", "No hay comandos que eliminar.")
            return
        name, ok = QInputDialog.getText(self, "Eliminar comando", "Nombre exacto de la app/web a eliminar:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name not in self.apps:
            QMessageBox.warning(self, "Eliminar comando", f"No existe una app/web llamada '{name}'.")
            return

        del self.apps[name]
        data = load_commands()
        data["apps"] = [a for a in data.get("apps", []) if a.get("name") != name]
        save_commands(data)

        self.load_and_render_commands()

    # ---------- Alta/Baja de grupos ----------
    def add_group(self):
        name, ok = QInputDialog.getText(self, "Añadir grupo", "Nombre del grupo:")
        if not ok or not name.strip():
            return
        items_text, ok = QInputDialog.getText(
            self,
            "Items del grupo",
            "Introduce elementos separados por comas.\n"
            "- Nombres de apps ya creadas\n"
            "- URLs (https://...)\n"
            "- Rutas locales (C:/.../algo.exe)\n"
        )
        if not ok:
            return

        items = [s.strip() for s in items_text.split(",") if s.strip()]
        new_group = {"name": name.strip(), "items": items}

        self.groups[name.strip()] = new_group
        data = load_commands()
        data.setdefault("groups", [])
        data["groups"].append(new_group)
        save_commands(data)

        btn = QPushButton(f"{new_group['name']} (grupo)")
        btn.setObjectName("group-button")
        btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
        btn.clicked.connect(lambda checked, g=new_group: self.run_group(g))
        count = self.container_layout.count()
        self.container_layout.addWidget(btn, count // 2, count % 2)

    def delete_group(self):
        if not self.groups:
            QMessageBox.information(self, "Eliminar grupo", "No hay grupos que eliminar.")
            return
        name, ok = QInputDialog.getText(self, "Eliminar grupo", "Nombre exacto del grupo a eliminar:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name not in self.groups:
            QMessageBox.warning(self, "Eliminar grupo", f"No existe un grupo llamado '{name}'.")
            return

        del self.groups[name]
        data = load_commands()
        data["groups"] = [g for g in data.get("groups", []) if g.get("name") != name]
        save_commands(data)

        self.load_and_render_commands()
