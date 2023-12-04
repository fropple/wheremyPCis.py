import sys
import psutil
import ctypes
from pypresence import Presence
from PyQt5 import QtWidgets, QtCore, QtGui
import os
from datetime import datetime
import json

logs_dir = "logs"
os.makedirs(logs_dir, exist_ok=True)

log_filename = f"{logs_dir}/logs-{datetime.now().strftime('%d-%m-%y')}.txt"

sys.stdout = open(log_filename, "a")
sys.stderr = open(log_filename, "a")

try:
    with open("config.json", "r") as config_file:
        config = json.load(config_file)
except Exception as e:
    config = {"show_process_name": True}

ver = "v2.0"

try:
    client_id = '1112662282615394335'
    RPC = Presence(client_id, pipe=0)
    RPC.connect()
    print("successfully started the handshake loop, check your status")
except Exception as e:
    print(f"error: unable to connect to Discord RPC - {e}")

class ErrorDialog(QtWidgets.QMessageBox):
    def __init__(self, message):
        super().__init__()
        self.setIcon(QtWidgets.QMessageBox.Critical)
        self.setText("An error occurred during startup.")
        self.setInformativeText(message)
        self.setWindowTitle("Error")
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.show_process_name = config.get("show_process_name", True)

        self.initUI()

        self.rpc_thread = QtCore.QThread()
        self.rpc_worker = RPCTask(self)  
        self.rpc_worker.moveToThread(self.rpc_thread)
        self.rpc_thread.started.connect(self.rpc_worker.run)
        self.rpc_thread.start()

        self.setup_system_tray()

    def initUI(self):
        self.setWindowTitle(f"wheremyPCis.py {ver}")
        self.setFixedSize(400, 200)
        self.setWindowIcon(QtGui.QIcon('assets/icon.ico'))

        self.about_tab = QtWidgets.QWidget()
        self.options_tab = QtWidgets.QWidget()

        self.notebook = QtWidgets.QTabWidget(self)
        self.notebook.setGeometry(10, 10, 380, 150)

        self.notebook.addTab(self.about_tab, "about")
        self.notebook.addTab(self.options_tab, "options")

        self.about_label = QtWidgets.QLabel("froppledojem's useless software, proudly made in python!\n\nthis software is designed to display your PC's current status as your Discord RPC.", self.about_tab)
        self.about_label.setGeometry(10, 10, 300, 100)
        self.about_label.setWordWrap(True)

        self.show_process_name_checkbox = QtWidgets.QCheckBox("show active process name?", self.options_tab)
        self.show_process_name_checkbox.setChecked(self.show_process_name)
        self.show_process_name_checkbox.stateChanged.connect(self.toggle_show_process_name)
        self.show_process_name_checkbox.setGeometry(10, 10, 200, 30)

        self.hide_to_system_tray_button = QtWidgets.QPushButton("hide to system tray", self)
        self.hide_to_system_tray_button.setGeometry(10, 165, 150, 30)
        self.hide_to_system_tray_button.clicked.connect(self.hide_to_system_tray)

    def toggle_show_process_name(self, state):
        self.show_process_name = state == QtCore.Qt.Checked
        config["show_process_name"] = bool(self.show_process_name)
        with open("config.json", "w") as config_file:
            json.dump(config, config_file)

    def hide_to_system_tray(self):
        self.hide()
        self.tray_icon.show()

    def show_normal(self):
        self.show()
        self.tray_icon.hide()

    def setup_system_tray(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(QtGui.QIcon('assets/icon.ico'))
        
        menu = QtWidgets.QMenu(self)
        
        show_action = QtWidgets.QAction('show window', self)
        show_action.triggered.connect(self.show_normal)
        menu.addAction(show_action)
        
        exit_action = QtWidgets.QAction('exit / quit', self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(menu)
        
        self.tray_icon.activated.connect(self.tray_activated)

    def tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.show_normal()

class RPCTask(QtCore.QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.show_process_name = config.get("show_process_name", True)

    def run(self):
        while True:
            cpu_usage = round(psutil.cpu_percent(), 1)
            mem = psutil.virtual_memory()
            active_process_name = self.get_active_process_name() if self.window.show_process_name else ""
            mem_total = psutil.virtual_memory().total
            mem_total_gb = round(mem_total / (1024 ** 3), 1)
            mem_usage = round(mem.percent, 1)
            disk_usage = psutil.disk_usage('/')
            total_storage = round(disk_usage.total / (1024 ** 3), 1)

            large_image = "icon"
            details = f"CPU usage: {cpu_usage}% - RAM usage: {mem_usage}%"

            if active_process_name and self.window.show_process_name:
                state = f"{total_storage}/{mem_total_gb}GB | {active_process_name}"
            else:
                state = f"{total_storage}/{mem_total_gb}GB"

            RPC.update(details=details, state=state, large_image=large_image)
            QtCore.QThread.msleep(1000)

    def get_active_process_name(self):
        active_window = ctypes.windll.user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        ctypes.windll.user32.GetWindowThreadProcessId(active_window, ctypes.byref(pid))
        process = psutil.Process(pid.value)
        name = process.name()
        return (name[:15] + '...') if len(name) > 12 else name

if __name__ == "__main__":
    try:
        app = QtWidgets.QApplication(sys.argv)
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        error_message = str(e)
        with open(log_filename, "r") as log_file:
            error_message += f"\n\nLast log entries:\n{log_file.read()}"
        error_dialog = ErrorDialog(error_message)
        error_dialog.exec_()
