'''Модуль История пользователей'''

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QTableView, QPushButton, QLabel, QDialog


class StatWindow(QDialog):
    '''Класс - окно история пользователей '''
    def __init__(self, database):
        super().__init__()

        self.database = database
        self.init_ui()

    def init_ui(self):
        '''Инициализация графического интерфейса'''
        self.setWindowTitle('Users History')
        self.setFixedSize(600, 550)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.label = QLabel('ClientsHistory:', self)
        self.label.setFixedSize(240, 25)
        self.label.move(10, 10)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(207, 227, 255))
        self.setPalette(palette)

        self.close_button = QPushButton('Закрыть', self)
        self.close_button.move(450, 450)
        self.close_button.clicked.connect(self.close)

        self.history_table = QTableView(self)
        self.history_table.move(10, 35)
        self.history_table.setFixedSize(580, 380)

        self.create_stat_model()

    def create_stat_model(self):
        '''Создание и отображение таблицы истории'''
        hist_list = self.database.message_history()
        list_ = QStandardItemModel()
        list_.setHorizontalHeaderLabels(
            ['Clients name', 'Last login time', 'Sent messages', 'Reсeived messages'])

        for row in hist_list:
            user, time, sent, rcv = row
            user = QStandardItem(user)  # создаем элемент
            user.setEditable(False)  # редактирование
            time = QStandardItem(str(time.replace(microsecond=0)))
            time.setEditable(False)
            sent = QStandardItem(str(sent))
            sent.setEditable(False)
            rcv = QStandardItem(str(rcv))
            rcv.setEditable(False)
            list_.appendRow([user, time, sent, rcv])  # добавляем строку
        self.history_table.setModel(list_)
        self.history_table.resizeColumnsToContents()
        self.history_table.resizeRowsToContents()
