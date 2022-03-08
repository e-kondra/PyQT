from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QDialog, QLabel, QComboBox, QPushButton

from logs.configs.client_log_config import LOG


class AddContact(QDialog):
    def __init__(self, transport, database):

        super().__init__()
        self.transport = transport
        self.database = database

        self.setFixedSize(300, 100)
        self.setWindowTitle('Выбор контактов для добавления:')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(153, 204, 153))
        self.setPalette(palette)

        self.selector_label = QLabel('Выберите контакт для добавления:', self)
        self.selector_label.setFixedSize(230, 30)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(280, 20)
        self.selector.move(10, 30)

        self.btn_ok= QtWidgets.QPushButton('Добавить', self)
        self.btn_ok.setFixedSize(80, 30)
        self.btn_ok.move(125, 60)

        self.btn_cancl = QPushButton('Отменить', self)
        self.btn_cancl.setFixedSize(80, 30)
        self.btn_cancl.move(210, 60)
        self.btn_cancl.clicked.connect(self.close)

        self.btn_refresh = QPushButton('Обновить список', self)
        self.btn_refresh.setFixedSize(110, 30)
        self.btn_refresh.move(10, 60)

        self.contacts_update()
        self.btn_refresh.clicked.connect(self.update_possible_contacts)

    def contacts_update(self):
        self.selector.clear()
        contacts = set(self.database.get_contacts())
        users = set(self.database.get_users())
        users.remove(self.transport.username)
        self.selector.addItems(users - contacts)

    def update_possible_contacts(self):
        try:
            self.transport.user_list_request()
        except OSError:
            pass
        else:
            LOG.debug('Обновлен список пользователей с сервера')
            self.contacts_update()
