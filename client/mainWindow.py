import sys
sys.path.append('../')
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QColor, QStandardItem, QStandardItemModel, QBrush
from PyQt5.QtWidgets import QMainWindow, QApplication, qApp, QMessageBox

from client.AddContactDialog import AddContact
from client.delete_contact import RemoveContact
from common.errors import ServerError
from logs.configs.client_log_config import LOG


class Ui_ClientWindow(object):
    def setupUi(self, MainClientWindow):
        MainClientWindow.setObjectName("MainClientWindow")
        MainClientWindow.resize(756, 534)
        MainClientWindow.setMinimumSize(QtCore.QSize(756, 534))

        self.centralwidget = QtWidgets.QWidget(MainClientWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.label_contacts = QtWidgets.QLabel(self.centralwidget)
        self.label_contacts.setGeometry(QtCore.QRect(10, 0, 130, 16))
        self.label_contacts.setObjectName("label_contacts")

        self.btn_add_contact = QtWidgets.QPushButton(self.centralwidget)
        self.btn_add_contact.setGeometry(QtCore.QRect(10, 450, 121, 31))
        self.btn_add_contact.setObjectName("btn_add_contact")

        self.btn_remove_contact = QtWidgets.QPushButton(self.centralwidget)
        self.btn_remove_contact.setGeometry(QtCore.QRect(140, 450, 121, 31))
        self.btn_remove_contact.setObjectName("btn_remove_contact")

        self.label_history = QtWidgets.QLabel(self.centralwidget)
        self.label_history.setGeometry(QtCore.QRect(300, 0, 391, 21))
        self.label_history.setObjectName("label_history")

        self.text_message = QtWidgets.QTextEdit(self.centralwidget)
        self.text_message.setGeometry(QtCore.QRect(300, 360, 441, 71))
        self.text_message.setObjectName("text_message")

        self.label_new_message = QtWidgets.QLabel(self.centralwidget)
        self.label_new_message.setGeometry(QtCore.QRect(300, 330, 450, 16))  # Правка тут
        self.label_new_message.setObjectName("label_new_message")

        self.list_contacts = QtWidgets.QListView(self.centralwidget)
        self.list_contacts.setGeometry(QtCore.QRect(10, 20, 251, 411))
        self.list_contacts.setObjectName("list_contacts")

        self.list_messages = QtWidgets.QListView(self.centralwidget)
        self.list_messages.setGeometry(QtCore.QRect(300, 20, 441, 301))
        self.list_messages.setObjectName("list_messages")

        self.btn_send = QtWidgets.QPushButton(self.centralwidget)
        self.btn_send.setGeometry(QtCore.QRect(600, 450, 145, 31))
        self.btn_send.setObjectName("btn_send")

        self.btn_clear = QtWidgets.QPushButton(self.centralwidget)
        self.btn_clear.setGeometry(QtCore.QRect(460, 450, 131, 31))
        self.btn_clear.setObjectName("btn_clear")

        MainClientWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainClientWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 756, 21))
        self.menubar.setObjectName("menubar")

        self.menu = QtWidgets.QMenu(self.menubar)
        self.menu.setObjectName("menu")
        self.menu_2 = QtWidgets.QMenu(self.menubar)
        self.menu_2.setObjectName("menu_2")
        MainClientWindow.setMenuBar(self.menubar)

        self.statusBar = QtWidgets.QStatusBar(MainClientWindow)
        self.statusBar.setObjectName("statusBar")
        MainClientWindow.setStatusBar(self.statusBar)

        self.menu_exit = QtWidgets.QAction(MainClientWindow)
        self.menu_exit.setObjectName("menu_exit")

        self.menu_add_contact = QtWidgets.QAction(MainClientWindow)
        self.menu_add_contact.setObjectName("menu_add_contact")

        self.menu_del_contact = QtWidgets.QAction(MainClientWindow)
        self.menu_del_contact.setObjectName("menu_del_contact")

        self.menu.addAction(self.menu_exit)

        self.menu_2.addAction(self.menu_add_contact)
        self.menu_2.addAction(self.menu_del_contact)
        self.menu_2.addSeparator()

        self.menubar.addAction(self.menu.menuAction())
        self.menubar.addAction(self.menu_2.menuAction())

        self.retranslateUi(MainClientWindow)
        self.btn_clear.clicked.connect(self.text_message.clear)
        QtCore.QMetaObject.connectSlotsByName(MainClientWindow)

    def retranslateUi(self, MainClientWindow):
        _translate = QtCore.QCoreApplication.translate
        MainClientWindow.setWindowTitle(_translate("MainClientWindow", "Чат Клиентская часть"))
        self.label_contacts.setText(_translate("MainClientWindow", "Список контактов:"))
        self.btn_add_contact.setText(_translate("MainClientWindow", "Добавить контакт"))
        self.btn_remove_contact.setText(_translate("MainClientWindow", "Удалить контакт"))
        self.label_history.setText(_translate("MainClientWindow", "История сообщений:"))
        self.label_new_message.setText(_translate("MainClientWindow", "Введите новое сообщение:"))
        self.btn_send.setText(_translate("MainClientWindow", "Отправить сообщение"))
        self.btn_clear.setText(_translate("MainClientWindow", "Очистить поле"))
        self.menu.setTitle(_translate("MainClientWindow", "Файл"))
        self.menu_2.setTitle(_translate("MainClientWindow", "Контакты"))
        self.menu_exit.setText(_translate("MainClientWindow", "Выход"))
        self.menu_add_contact.setText(_translate("MainClientWindow", "Добавить контакт"))
        self.menu_del_contact.setText(_translate("MainClientWindow", "Удалить контакт"))


class MainWindow(QMainWindow):
    def __init__(self, database, transport):

        super().__init__()
        self.database = database
        self.transport = transport

        self.ui = Ui_ClientWindow()
        self.ui.setupUi(self)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(255, 255, 204))
        self.setPalette(palette)

        self.ui.menu_exit.triggered.connect(qApp.exit)

        self.ui.btn_send.clicked.connect(self.send_message)

        self.ui.menu_add_contact.triggered.connect(self.window_add_contact)
        self.ui.btn_add_contact.clicked.connect(self.window_add_contact)

        self.ui.menu_del_contact.triggered.connect(self.window_del_contact)
        self.ui.btn_remove_contact.clicked.connect(self.window_del_contact)

        self.contacts_model = None
        self.history_model = None
        self.messages = QMessageBox()
        self.current_chat = None
        self.ui.list_messages.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.list_messages.setWordWrap(True)

        self.ui.list_contacts.doubleClicked.connect(self.select_active_user)

        self.contacts_list_update()
        self.set_disabled_input()

        self.show()

    def set_disabled_input(self):
        # Надпись  - получатель.
        self.ui.label_new_message.setText('Для выбора получателя дважды кликните на нем в окне контактов.')
        self.ui.text_message.clear()
        if self.history_model:
            self.history_model.clear()

        # Поле ввода и кнопка отправки неактивны до выбора получателя.
        self.ui.btn_clear.setDisabled(True)
        self.ui.btn_send.setDisabled(True)
        self.ui.text_message.setDisabled(True)

    def send_message(self):
        print('send_message')
        # Текст в поле, проверяем что поле не пустое затем забирается сообщение и поле очищается
        message_text = self.ui.text_message.toPlainText()
        print(f'message_text = {message_text}')
        self.ui.text_message.clear()
        if not message_text:
            print('not message_text')
            return
        try:
            self.transport.send_message_(self.current_chat, message_text)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', f'Таймаут соединения!{err}')
        except (ConnectionResetError, ConnectionAbortedError):
            self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
            self.close()
        except Exception as err:
            print(f'Exception send_message: {err}')
        else:
            self.database.save_message(self.current_chat, 'out', message_text)
            LOG.debug(f'Отправлено сообщение для {self.current_chat}: {message_text}')
            self.history_list_update()

    def window_add_contact(self):
        global selected_dialog
        selected_dialog = AddContact(self.transport, self.database)
        selected_dialog.btn_ok.clicked.connect(lambda: self.add_contact_action(selected_dialog))
        selected_dialog.show()

        # Функция обработчик даблклика по контакту
    def select_active_user(self):
        # Выбранный пользователем (даблклик) находится в выделеном элементе в QListView
        self.current_chat = self.ui.list_contacts.currentIndex().data()
        # вызываем основную функцию
        self.set_active_user()

    def add_contact_action(self, item):
        contact = item.selector.currentText()
        self.add_contact(contact)
        item.close()

    def add_contact(self, contact):
        print('add_contact')
        try:
            self.transport.add_contact(contact)
        except ServerError as err:
            self.messages.critical(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.add_contact(contact)
            contact = QStandardItem(contact)
            contact.setEditable(False)
            self.contacts_model.appendRow(contact)
            LOG.info(f'Добавлен контакт {contact}')
            self.messages.information(self,'Успешно', 'Добавлен контакт')


    def window_del_contact(self):
        global remove_dialog
        remove_dialog = RemoveContact(self.database)
        remove_dialog.btn_ok.clicked.connect(lambda: self.del_contact(remove_dialog))
        remove_dialog.show()

    def del_contact(self, item):
        selected_contact = item.selector.currentText()
        try:
            self.transport.remove_contact(selected_contact)
        except ServerError as err:
            self.messages.сritical(self, 'Ошибка сервера', err.text)
            # self.messages.warning(self, 'Ошибка сервера', err.text)
        except OSError as err:
            if err.errno:
                self.messages.critical(self, 'Ошибка', 'Потеряно соединение с сервером!')
                self.close()
            self.messages.critical(self, 'Ошибка', 'Таймаут соединения!')
        else:
            self.database.del_contact(selected_contact)
            self.contacts_list_update()
            LOG.info(f'Успешно удалён контакт {selected_contact}')
            self.messages.information(self, 'Успех', 'Контакт успешно удалён.')
            item.close()
            # Если удалён активный пользователь, то деактивируем поля ввода.
            if selected_contact == self.current_chat:
                self.current_chat = None
                self.set_disabled_input()

    def contacts_list_update(self):
        contacts_list = self.database.get_contacts()
        self.contacts_model = QStandardItemModel()
        for i in sorted(contacts_list):
            item = QStandardItem(i)
            item.setEditable(False)
            self.contacts_model.appendRow(item)
        self.ui.list_contacts.setModel(self.contacts_model)

    def history_list_update(self):
        hist_list = sorted(self.database.get_history(self.current_chat), key=lambda i: i[3]) # сортируем по дате историю сообщений
        if not self.history_model:
            self.history_model = QStandardItemModel() # универсальная модель для хранения пользовательских данных
            self.ui.list_messages.setModel(self.history_model)
        self.history_model.clear()
        hist_length = len(hist_list)
        start = hist_length - 20 if hist_length > 20 else 0 # последние 20 записей
        # Заполнение модели записями: разделим входящие и исходящие выравниванием и разным фоном.
        # Записи в обратном порядке, поэтому выбираем их с конца и не более 20
        for i in range(start, hist_length):
            item = hist_list[i]
            if item[1] == 'in':
                mess = QStandardItem(f'Входящее: {item[3].replace(microsecond=0)}\n{item[2]}')
                mess.setEditable(False)
                mess.setBackground(QBrush(QColor(215,213,213)))
                mess.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(mess)
            else:
                mess = QStandardItem(f'Исходящее: {item[3].replace(microsecond=0)}\n{item[2]}')
                mess.setEditable(False)
                mess.setBackground(QBrush(QColor(204, 255, 204)))
                mess.setTextAlignment(Qt.AlignLeft)
                self.history_model.appendRow(mess)
        self.ui.list_messages.scrollToBottom()

    @pyqtSlot(str)
    def message(self, sender):
        if sender == self.current_chat:
            self.history_list_update()
        else:
            if self.database.check_contact(sender):
                if self.messages.question(self, 'Новое сообщение',
                                          f'Получено новое сообщение от {sender}. Открыть чат с ним?', QMessageBox.Yes,
                                          QMessageBox.No) == QMessageBox.Yes:
                    self.current_chat = sender
                    self.set_active_user()
            else:
                if self.messages.question(self, 'Новое сообщение',
                                          f'Получено новое сообщение от {sender}.\nЭтого контакта нет в Вашем контакт-листе \nДобавить в контакты и открыть чат с ним?',
                                          QMessageBox.Yes, QMessageBox.No) == QMessageBox.Yes:
                    self.add_contact(sender)
                    self.current_chat = sender
                    self.set_active_user()

    def make_connection(self, trans_obj):
        trans_obj.new_message.connect(self.message)
        trans_obj.connection_lost.connect(self.connection_lost)

    @pyqtSlot()
    def connection_lost(self):
        self.messages.warning(self, 'Сбой соединения', 'Потеряно соединение с сервером')
        self.close()

    # установка активного собеседника
    def set_active_user(self):
        self.ui.label_new_message.setText(f'ВВедите сообщение для {self.current_chat}')
        self.ui.btn_clear.setDisabled(False)
        self.ui.btn_send.setDisabled(False)
        self.ui.text_message.setDisabled(False)
        self.history_list_update()


if __name__ == '__main__':
    APP = QApplication(sys.argv)  # точка входа, создание приложения
    WINDOW_OBJ = MainWindow()  # базовый класс для графич.элементов
    APP.exec_()
