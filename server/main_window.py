'''Основное окно серверного приложения'''

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QColor, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QLabel, QTableView

from server.config_window import ConfigWindow
from server.registr_window import RegistrUser
from server.remove_window import DeleteUser
from server.stat_window import StatWindow


class MainWindow(QMainWindow):
    '''Класс - основное окно сервера.'''

    def __init__(self, database, server, config):
        super().__init__()

        self.database = database

        self.server_thread = server
        self.config = config

        # Настройки геометрии основного окна
        # размер окна фиксирован.
        self.setFixedSize(600, 550)
        self.setWindowTitle('Messaging Server')
        # фон
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(207, 227, 255))
        self.setPalette(palette)
        # кнопка выход
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(qApp.quit)

        self.refresh_button = QAction('Обновить список', self)  # обновить список клиентов

        self.config_button = QAction('Настройки сервера', self)

        self.registration_btn = QAction('Регистрация пользователя', self)

        self.remove_button = QAction('Удаление пользователя', self)

        self.show_history_btn = QAction('История клиентов', self)

        # Статусбар
        self.statusBar()

        # Тулбар
        self.toolbar = self.addToolBar('MainBar')

        self.toolbar.addAction(self.refresh_button)
        self.toolbar.addAction(self.show_history_btn)
        self.toolbar.addAction(self.config_button)
        self.toolbar.addAction(self.registration_btn)
        self.toolbar.addAction(self.remove_button)
        self.toolbar.addAction(exit_action)

        # Надпись о том, что ниже список подключённых клиентов
        self.label = QLabel('Active Users List:', self)
        self.label.setFixedSize(240, 25)
        self.label.move(10, 30)

        # Окно со списком подключённых клиентов.( по умолчанию без шапки)
        self.active_clients_table = QTableView(self)
        self.active_clients_table.move(10, 55)
        self.active_clients_table.setFixedSize(580, 400)

        # Таймер, обновляющий список клиентов 1 раз в секунду
        self.timer = QTimer()
        self.timer.timeout.connect(self.create_users_model)
        self.timer.start(1000)

        self.refresh_button.triggered.connect(self.create_users_model)
        self.show_history_btn.triggered.connect(self.show_statistics)
        self.config_button.triggered.connect(self.server_config)
        self.registration_btn.triggered.connect(self.registr_user)
        self.remove_button.triggered.connect(self.remove_user)

        self.show()

    def create_users_model(self):
        '''Заполнение таблицы активных пользователей'''
        active_users = self.database.active_users_list()
        list_ = QStandardItemModel()
        list_.setHorizontalHeaderLabels(['Clients name', 'last login', 'IP address', 'Port', ])
        for row in active_users:
            user, ipaddress, port, time = row
            user = QStandardItem(user)  # создаем элемент
            user.setEditable(False)  # редактирование
            ipaddress = QStandardItem(str(ipaddress))
            ipaddress.setEditable(False)
            port = QStandardItem(str(port))
            port.setEditable(False)
            time = QStandardItem(str(time.replace(microsecond=0)))
            time.setEditable(False)
            list_.appendRow([user, ipaddress, port, time])  # добавляем строку
        self.active_clients_table.setModel(list_)
        self.active_clients_table.resizeColumnsToContents()
        self.active_clients_table.resizeRowsToContents()

    def show_statistics(self):
        '''Создание окна со статистикой клиентов'''
        global stat_window
        stat_window = StatWindow(self.database)
        stat_window.show()

    def server_config(self):
        '''Создание окна с настройками сервера'''
        global config_window
        config_window = ConfigWindow(self.config)

    def registr_user(self):
        '''Создание окна регистрации пользователя'''
        global registr_window
        registr_window = RegistrUser(self.database, self.server_thread)
        registr_window.show()

    def remove_user(self):
        '''Создание окна удаления пользователя'''
        global remove_window
        remove_window = DeleteUser(self.database, self.server_thread)
        remove_window.show()
