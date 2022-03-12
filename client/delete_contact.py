from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QDialog, QLabel, QComboBox, QApplication


class RemoveContact(QDialog):

    def __init__(self, database):
        super().__init__()
        self.database = database

        self.setFixedSize(300, 100)
        self.setWindowTitle('Выберите контакт для удаления:')
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setModal(True)

        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(103, 135, 111))
        self.setPalette(palette)

        self.selector_label = QLabel('Выберите контакт для удаления:', self)
        self.selector_label.setFixedSize(230, 30)
        self.selector_label.move(10, 0)

        self.selector = QComboBox(self)
        self.selector.setFixedSize(280, 20)
        self.selector.move(10, 30)

        self.btn_ok = QtWidgets.QPushButton('Удалить', self)
        self.btn_ok.setFixedSize(80, 30)
        self.btn_ok.move(125, 60)

        self.btn_cancl = QtWidgets.QPushButton('Отменить', self)
        self.btn_cancl.setFixedSize(80, 30)
        self.btn_cancl.move(210, 60)
        self.btn_cancl.clicked.connect(self.close)

        self.selector.addItems(sorted(self.database.get_contacts()))


if __name__ == '__main__':
    app = QApplication([])
    window = RemoveContact(None)
    window.show()
    app.exec_()
