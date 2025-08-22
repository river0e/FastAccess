import os
import sys
import webbrowser
from urllib.parse import urlparse

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QPushButton, QLabel, QMessageBox,
    QScrollArea, QInputDialog, QStyle, QMenu, QSystemTrayIcon, QApplication
)
from PyQt6.QtCore import Qt, QPoint, QEvent
from PyQt6.QtGui import QIcon

from commands import load_commands, save_commands
from voice import toggle_listening, signals  # Función para pausar/reactivar voz y señales en label

# --------------- NUEVO: Función para rutas empaquetadas ---------------
def resource_path(relative_path):
    """Devuelve la ruta correcta a recursos dentro del exe o en desarrollo."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class FastAccessGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fast Access")
        self.setGeometry(250, 250, 670, 657)

        # Conectar señales de voice.py al label de mensajes
        signals.status.connect(lambda msg: self.show_message(msg, "info"))
        signals.error.connect(lambda msg: self.show_message(msg, "error"))
        signals.command_detected.connect(lambda msg: self.show_message(f"Comando detectado: {msg}", "success"))

        # --------------------- Íconos ---------------------
        self.setWindowIcon(QIcon(resource_path("icon/Titulo.ico")))

        # Configurar icono de bandeja
        tray_icon_path = resource_path("icon/minimizado.ico")
        self.tray_icon = QSystemTrayIcon(QIcon(tray_icon_path), parent=self)
        self.tray_icon.setToolTip("FastAccess - Asistente en segundo plano")

        # Menú de bandeja
        tray_menu = QMenu()
        restore_action = tray_menu.addAction("Restaurar")
        restore_action.triggered.connect(self.restore_from_tray)
        exit_action = tray_menu.addAction("Salir")
        exit_action.triggered.connect(self.exit_app)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

        # Aceptar arrastrar/soltar
        self.setAcceptDrops(True)

        # CSS externo opcional
        css_path = resource_path("style.css")
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        # --------------------- Layout principal ---------------------
        layout = QVBoxLayout(self)

        titulo = QLabel("FAST ACCESS")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(titulo)

        # Botones de acciones
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

        self.toggle_voice_btn = QPushButton("Voz (Activa)")
        self.toggle_voice_btn.setObjectName("add-button")
        self.toggle_voice_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.toggle_voice_btn.clicked.connect(self.handle_toggle_voice)

        # Añadir botones al grid
        actions_layout.addWidget(self.add_btn, 0, 0)
        actions_layout.addWidget(self.delete_btn, 0, 1)
        actions_layout.addWidget(self.add_group_btn, 1, 0)
        actions_layout.addWidget(self.delete_group_btn, 1, 1)
        actions_layout.addWidget(self.toggle_voice_btn, 2, 0, 1, 2)
        layout.addLayout(actions_layout)

        # Scroll para apps y grupos
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.container_layout = QGridLayout(self.container)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

        # Label de mensajes
        self.info_label = QLabel("")
        self.info_label.setFixedHeight(25)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("border: 2px solid yellow; padding: 2px; font-weight: bold;")
        layout.addWidget(self.info_label)

        # Tooltip general
        self.setToolTip("Arrastra un acceso directo de una app, ruta o URL aquí.\nSe crearán automáticamente botones y comandos de voz para facilitar su uso.")

        # Carga inicial
        self.load_and_render_commands()

    # ---------- Restaurar ventana ----------
    def restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ---------- Click en bandeja ----------
    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.restore_from_tray()

    # ---------- Salir de la app de forma completa ----------
    def exit_app(self):
        """Cierra la app y el icono de la bandeja."""
        self.tray_icon.hide()  # Oculta y elimina el icono de la bandeja
        QApplication.quit()    # Cierra toda la aplicación

    # ---------- Sobrescribir closeEvent ----------
    def closeEvent(self, event):
        """
        Cuando se pulsa la X de la ventana, ocultamos la ventana y mostramos
        un mensaje de confirmación para salir realmente si quieres.
        """
        reply = QMessageBox.warning(
            self,
            "Salir",
            "¿Deseas cerrar FastAccess completamente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
    )
        if  reply == QMessageBox.StandardButton.Yes:
            self.exit_app()  # Llama al cierre completo
            event.accept()
        else:
            event.ignore()  # Solo oculta la ventana, la app sigue en la bandeja        

    # ---------- Cambios de estado ----------
    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                self.hide()  # Oculta la ventana pero mantiene tray
        super().changeEvent(event)

    # ---------- Drag & Drop ----------
    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls() or md.hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        handled_any = False
        md = event.mimeData()

        if md.hasUrls():
            for url in md.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path:
                        self.add_dropped_command(action=path, type_="app")
                        handled_any = True
                else:
                    s = url.toString()
                    if s.startswith(("http://", "https://")):
                        self.add_dropped_command(action=s, type_="web")
                        handled_any = True
        elif md.hasText():
            text = md.text().strip()
            if text.startswith(("http://", "https://")):
                self.add_dropped_command(action=text, type_="web")
                handled_any = True
            elif os.path.exists(text):
                self.add_dropped_command(action=text, type_="app")
                handled_any = True

        if handled_any:
            self.show_message("Elemento añadido por arrastrar/soltar", "success")
        else:
            self.show_message("No se pudo interpretar lo arrastrado", "error")

        event.acceptProposedAction()

    def add_dropped_command(self, action, type_):
        base_name = os.path.basename(action) if type_ == "app" else urlparse(action).netloc or action
        name = self._unique_name(base_name)

        new_app = {"name": name, "type": type_, "action": action}
        self.apps[name] = new_app
        data = load_commands()
        data.setdefault("apps", []).append(new_app)
        save_commands(data)
        self.load_and_render_commands()

    def _unique_name(self, base):
        name = base
        i = 1
        while name in getattr(self, "apps", {}):
            name = f"{base} ({i})"
            i += 1
        return name

    # ---------- Mensajes ----------
    def show_message(self, text, tipo="info"):
        color = {"info": "yellow", "error": "red", "success": "green"}.get(tipo, "yellow")
        self.info_label.setStyleSheet(f"border: 2px solid {color}; padding: 2px; font-weight: bold;")
        self.info_label.setText(text)

    # ---------- Toggle voz ----------
    def handle_toggle_voice(self):
        state = toggle_listening()
        if state:
            self.toggle_voice_btn.setText("Voz (Activa)")
            self.toggle_voice_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
            self.show_message("Asistente de voz activado", "info")
        else:
            self.toggle_voice_btn.setText("Voz (Pausada)")
            self.toggle_voice_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.show_message("Asistente de voz pausado", "info")

    # ---------- Carga y render ----------
    def load_and_render_commands(self):
        # Limpiar layout
        while self.container_layout.count():
            w = self.container_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        data = load_commands()
        self.apps = {app["name"]: app for app in data.get("apps", [])}
        self.groups = {group["name"]: group for group in data.get("groups", [])}

        row, col = 0, 0
        # Render apps
        for app in self.apps.values():
            btn = QPushButton(app["name"])
            btn.setObjectName("app-button")
            btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            btn.clicked.connect(lambda checked, a=app: self.run_action(a))
            btn.setToolTip(f"Tipo: {app.get('type','?')}\nAcción: {app['action']}")
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, name=app["name"]: self.show_app_context_menu(b, name)
            )
            self.container_layout.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

        # Render grupos
        for group in self.groups.values():
            btn = QPushButton(f"{group['name']} (grupo)")
            btn.setObjectName("group-button")
            btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
            btn.clicked.connect(lambda checked, g=group: self.run_group(g))
            btn.setToolTip(self._build_group_tooltip(group))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, name=group["name"]: self.show_group_context_menu(b, name)
            )
            self.container_layout.addWidget(btn, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def _build_group_tooltip(self, group):
        items = group.get("items", []) or []
        if not items:
            return "Grupo vacío"
        lines = []
        for item in items:
            if item in self.apps:
                a = self.apps[item]
                lines.append(f"• {item} → {a.get('action','')}")
            else:
                lines.append(f"• {item}")
        return "Incluye:\n" + "\n".join(lines)

    # ---------- Menú contextual: APP ----------
    def show_app_context_menu(self, button: QPushButton, app_name: str):
        if app_name not in self.apps:
            return
        menu = QMenu(self)
        act_edit = menu.addAction("✏️ Editar")
        act_move = menu.addAction("📂 Mover a grupo…")
        act_newgrp = menu.addAction("➕ Crear grupo con esta app…")
        menu.addSeparator()
        act_delete = menu.addAction("🗑️ Eliminar")

        chosen = menu.exec(button.mapToGlobal(QPoint(0, button.height())))
        if not chosen:
            return

        if chosen == act_edit:
            self._edit_app_dialog(app_name)
        elif chosen == act_move:
            self._move_app_to_group(app_name)
        elif chosen == act_newgrp:
            self._create_group_with_app(app_name)
        elif chosen == act_delete:
            self._delete_command_by_name(app_name)

    def _edit_app_dialog(self, app_name: str):
        app = self.apps.get(app_name)
        if not app:
            return

        new_name, ok = QInputDialog.getText(self, "Editar comando", "Nombre:", text=app["name"])
        if not ok or not new_name.strip():
            return
        new_type, ok = QInputDialog.getItem(self, "Tipo", "Tipo:", ["web", "app"],
                                            0 if app.get("type") == "web" else 1, False)
        if not ok:
            return
        new_action, ok = QInputDialog.getText(self, "Acción", "URL o ruta:", text=app["action"])
        if not ok or not new_action.strip():
            return

        new_name = new_name.strip()
        new_type = new_type.strip()
        new_action = new_action.strip()

        data = load_commands()

        # Actualizar app en datos
        for a in data.get("apps", []):
            if a["name"] == app_name:
                a["name"] = new_name
                a["type"] = new_type
                a["action"] = new_action
                break

        # Si cambió el nombre, actualizar referencias en grupos
        if new_name != app_name:
            for g in data.get("groups", []):
                if "items" in g and g["items"]:
                    g["items"] = [new_name if x == app_name else x for x in g["items"]]

        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"Comando '{new_name}' editado", "success")

    def _move_app_to_group(self, app_name: str):
        if not self.groups:
            QMessageBox.information(self, "Grupos", "No hay grupos disponibles.")
            return
        group_name, ok = QInputDialog.getItem(
            self, "Mover a grupo", "Selecciona grupo:", list(self.groups.keys()), 0, False
        )
        if not ok:
            return

        data = load_commands()
        for g in data.get("groups", []):
            if g["name"] == group_name:
                g.setdefault("items", [])
                if app_name not in g["items"]:
                    g["items"].append(app_name)
                break
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"'{app_name}' movido a grupo '{group_name}'", "success")

    def _create_group_with_app(self, app_name: str):
        group_name, ok = QInputDialog.getText(self, "Crear grupo", "Nombre del nuevo grupo:")
        if not ok or not group_name.strip():
            return
        group_name = group_name.strip()

        data = load_commands()

        # Evitar duplicado
        existing = {g["name"] for g in data.get("groups", [])}
        if group_name in existing:
            QMessageBox.warning(self, "Ya existe", f"El grupo '{group_name}' ya existe.")
            return

        new_group = {"name": group_name, "items": [app_name]}
        data.setdefault("groups", []).append(new_group)
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"Grupo '{group_name}' creado con '{app_name}'", "success")

    def _delete_command_by_name(self, name: str):
        data = load_commands()
        data["apps"] = [a for a in data.get("apps", []) if a.get("name") != name]
        # (Opcional) limpiar referencias en grupos
        for g in data.get("groups", []):
            if "items" in g and g["items"]:
                g["items"] = [x for x in g["items"] if x != name]
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"Comando '{name}' eliminado", "success")

    # ---------- Menú contextual: GRUPO ----------
    def show_group_context_menu(self, button: QPushButton, group_name: str):
        group = self.groups.get(group_name)
        if not group:
            return
        menu = QMenu(self)
        act_edit = menu.addAction("✏️ Editar")
        act_add = menu.addAction("➕ Añadir app existente…")
        act_remove = menu.addAction("➖ Quitar app…")
        menu.addSeparator()
        act_delete = menu.addAction("🗑️ Eliminar")

        chosen = menu.exec(button.mapToGlobal(QPoint(0, button.height())))
        if not chosen:
            return

        if chosen == act_edit:
            self._edit_group_dialog(group_name)
        elif chosen == act_add:
            self._add_app_to_group(group_name)
        elif chosen == act_remove:
            self._remove_app_from_group(group_name)
        elif chosen == act_delete:
            self._delete_group_by_name(group_name)

    def _edit_group_dialog(self, group_name: str):
        group = self.groups.get(group_name)
        if not group:
            return

        new_name, ok = QInputDialog.getText(self, "Editar grupo", "Nombre:", text=group["name"])
        if not ok or not new_name.strip():
            return

        # Editar items como texto separado por comas
        current_items_text = ", ".join(group.get("items", []))
        items_text, ok = QInputDialog.getText(
            self, "Editar elementos del grupo",
            "Introduce elementos separados por comas.\n"
            "- Nombres de apps ya creadas\n"
            "- URLs (https://...)\n"
            "- Rutas locales (C:/.../algo.exe)\n",
            text=current_items_text
        )
        if not ok:
            return

        new_items = [s.strip() for s in items_text.split(",") if s.strip()]
        new_name = new_name.strip()

        data = load_commands()
        for g in data.get("groups", []):
            if g["name"] == group_name:
                g["name"] = new_name
                g["items"] = new_items
                break
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"Grupo '{new_name}' editado", "success")

    def _add_app_to_group(self, group_name: str):
        if not self.apps:
            QMessageBox.information(self, "Apps", "No hay apps disponibles.")
            return
        app_name, ok = QInputDialog.getItem(
            self, "Añadir app al grupo", "Selecciona app:", list(self.apps.keys()), 0, False
        )
        if not ok:
            return
        data = load_commands()
        for g in data.get("groups", []):
            if g["name"] == group_name:
                g.setdefault("items", [])
                if app_name not in g["items"]:
                    g["items"].append(app_name)
                break
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"'{app_name}' añadido a '{group_name}'", "success")

    def _remove_app_from_group(self, group_name: str):
        group = self.groups.get(group_name, {})
        items = group.get("items", [])
        if not items:
            QMessageBox.information(self, "Grupo", "Este grupo no tiene elementos.")
            return
        # Solo mostrar apps por nombre (no URLs sueltas)
        selectable = [i for i in items if i in self.apps]
        if not selectable:
            QMessageBox.information(self, "Grupo", "No hay apps por nombre que quitar (solo URLs/rutas).")
            return

        app_name, ok = QInputDialog.getItem(
            self, "Quitar app del grupo", "Selecciona app:", selectable, 0, False
        )
        if not ok:
            return

        data = load_commands()
        for g in data.get("groups", []):
            if g["name"] == group_name:
                g["items"] = [x for x in g.get("items", []) if x != app_name]
                break
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"'{app_name}' quitado de '{group_name}'", "success")

    def _delete_group_by_name(self, name: str):
        data = load_commands()
        data["groups"] = [g for g in data.get("groups", []) if g.get("name") != name]
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"Grupo '{name}' eliminado", "success")

    # ---------- Ejecuciones ----------
    def execute_target(self, target: str):
        try:
            if isinstance(target, str) and target.lower().startswith(("http://", "https://")):
                webbrowser.open(target)
            else:
                os.startfile(target)
        except Exception as e:
            self.show_message(f"No se pudo abrir: {target}", "error")
            QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{target}\n\n{e}")

    def resolve_item_to_targets(self, item):
        targets = []
        if isinstance(item, str):
            if item in self.apps:
                targets.append(self.apps[item]["action"])
            elif item.lower().startswith(("http://", "https://")):
                targets.append(item)
            elif os.path.exists(item):
                targets.append(item)
        elif isinstance(item, dict):
            action = item.get("action")
            if action:
                targets.append(action)
        return targets

    def run_action(self, app):
        self.execute_target(app["action"])
        self.show_message(f"Ejecutando {app['name']}", "success")

    def run_group(self, group):
        items = group.get("items", [])
        executed = False
        for item in items:
            targets = self.resolve_item_to_targets(item)
            for t in targets:
                self.execute_target(t)
                executed = True
        if executed:
            self.show_message(f"Ejecutando grupo {group.get('name','(sin nombre)')}", "success")
        else:
            self.show_message(f"Grupo '{group.get('name','(sin nombre)')}' vacío", "error")
            QMessageBox.warning(
                self,
                "Grupo vacío",
                f"El grupo '{group.get('name','(sin nombre)')}' no contiene elementos válidos."
            )

    # ---------- Alta/Baja ----------
    def add_command(self):
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

        name = self._unique_name(name.strip())
        new_app = {"name": name, "type": type_.strip(), "action": action.strip()}
        self.apps[name] = new_app
        data = load_commands()
        data.setdefault("apps", [])
        data["apps"].append(new_app)
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"Comando '{name}' añadido", "success")

    def delete_command(self):
        if not self.apps:
            self.show_message("No hay comandos que eliminar", "info")
            return
        name, ok = QInputDialog.getText(self, "Eliminar comando", "Nombre exacto de la app/web a eliminar:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name not in self.apps:
            self.show_message(f"No existe la app/web '{name}'", "error")
            return
        self._delete_command_by_name(name)

    def add_group(self):
        name, ok = QInputDialog.getText(self, "Añadir grupo", "Nombre del grupo:")
        if not ok or not name.strip():
            return
        group_name = name.strip()
        if group_name in self.groups:
            self.show_message(f"El grupo '{group_name}' ya existe", "error")
            return
        new_group = {"name": group_name, "items": []}
        self.groups[group_name] = new_group
        data = load_commands()
        data.setdefault("groups", [])
        data["groups"].append(new_group)
        save_commands(data)
        self.load_and_render_commands()
        self.show_message(f"Grupo '{group_name}' añadido", "success")

    def delete_group(self):
        if not self.groups:
            self.show_message("No hay grupos que eliminar", "info")
            return
        name, ok = QInputDialog.getText(self, "Eliminar grupo", "Nombre exacto del grupo a eliminar:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name not in self.groups:
            self.show_message(f"No existe el grupo '{name}'", "error")
            return
        self._delete_group_by_name(name)

