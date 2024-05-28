import os
import json
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QMessageBox, QHBoxLayout
from PyQt5.QtCore import QTimer, QDateTime
from typing import Dict, List
from WE import WE, Quota

CONFIG_FILE = os.path.expanduser("~/config.json")

def loadIcon(filename):
    return os.path.join(os.path.abspath(os.getcwd()), os.path.join('assets', filename))

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login In")
        self.setFixedSize(300, 100)

        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)

        self.show_icon = QIcon(loadIcon("vis.png"))
        self.hide_icon = QIcon(loadIcon("visoff.png"))
        self.show_hide_password_button = QPushButton()
        self.show_hide_password_button.setIcon(self.show_icon)
        self.show_hide_password_button.setCheckable(True)
        self.show_hide_password_button.clicked.connect(self.toggle_password_visibility)

        layout = QFormLayout()
        layout.addRow("Service Number:", self.username_input)
        password_layout = QHBoxLayout()
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.show_hide_password_button)
        layout.addRow("Password:", password_layout)

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def toggle_password_visibility(self):
        if self.show_hide_password_button.isChecked():
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.show_hide_password_button.setIcon(self.hide_icon)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.show_hide_password_button.setIcon(self.show_icon)

    def get_credentials(self):
        return self.username_input.text(), self.password_input.text()

class QuotaTrayApp:
    def __init__(self):
        self.app = QApplication([])
        self.app.setQuitOnLastWindowClosed(False)

        self.icon = QIcon(loadIcon("icon.png"))

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.icon)
        self.tray.setVisible(True)

        self.menu = QMenu()

        self.last_update_time = QDateTime.currentDateTime().toString("hh:mm:ss AP")
        self.we = None

        self.initialize()

    def initialize(self):
        config = self.load_config()
        if config:
            self.initialize_we(config["username"], config["password"])
        self.update_quota_info()

        self.tray.setContextMenu(self.menu)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_action)
        self.timer.start(1000)

        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.update_quota_info)
        self.refresh_timer.start(600000)  # 600,000 milliseconds = 10 minutes

        self.update_time_action()
        self.app.exec_()

    def save_config(self, username, password):
        with open(CONFIG_FILE, 'w') as file:
            json.dump({"username": username, "password": password}, file)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as file:
                return json.load(file)
        return None

    def sign_in(self):
        dialog = LoginDialog()
        if dialog.exec_() == QDialog.Accepted:
            username, password = dialog.get_credentials()
            try:
                self.initialize_we(username, password)
            except Exception as brr:
                QMessageBox.critical(None, "Sign In Error", repr(brr))
                self.sign_in()

            self.save_config(username, password)
            self.update_quota_info()

    def initialize_we(self, username, password):
        self.we = WE(username, password)

    def update_quota_info(self):
        self.menu.clear()
        self.menu.addSeparator()
        if self.we is None:
            sign_in_action = QAction("Sign In", self.menu)
            sign_in_action.triggered.connect(self.sign_in)
            self.menu.addAction(sign_in_action)
        else:
            quotas = self.we.FullQuotaInfo()

            total_quotas = QAction(f"Total of Quotas: {quotas.total}", self.menu)
            total_remain = QAction(f"Total remaining: {quotas.remain}", self.menu)
            self.menu.addAction(total_quotas)
            self.menu.addAction(total_remain)

            for quota in quotas.freeUnitBeanDetailList:
                self.menu.addSeparator()
                quota_title = QAction(f"Current Quota: {quota.offeringName}", self.menu)
                total = QAction(f"Total: {quota.initialAmount} GB", self.menu)
                remain = QAction(f"Remaining: {quota.currentAmount} GB", self.menu)
                sub_date = QAction(f"Subscription date: {quota.effectiveTime_dt}", self.menu)
                expire_date = QAction(f"Expire date: {quota.expireTime_dt}", self.menu)
                num_days = QAction(f"Number of Days until renewal: {quota.remainingDaysForRenewal}", self.menu)
                self.menu.addAction(quota_title)
                self.menu.addAction(total)
                self.menu.addAction(remain)
                self.menu.addAction(sub_date)
                self.menu.addAction(expire_date)
                self.menu.addAction(num_days)

            self.menu.addSeparator()
            refresh_action = QAction("Refresh", self.menu)
            refresh_action.triggered.connect(self.update_quota_info)
            self.menu.addAction(refresh_action)
            
            logout_action = QAction("Logout", self.menu)
            logout_action.triggered.connect(self.logout)
            self.menu.addAction(logout_action)

        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)
        self.last_update_time = QDateTime.currentDateTime().toString("hh:mm:ss AP")

    def logout(self):
        self.we = None
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
        self.update_quota_info()

    def update_time_action(self):
        current_time = QDateTime.currentDateTime().toString("hh:mm:ss AP")
        self.tray.setToolTip(f"Last Update Time: {self.last_update_time} | Current Time: {current_time}")

if __name__ == "__main__":
    QuotaTrayApp()
