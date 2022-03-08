from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, qApp


class UserNameDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.ok_pressed = False

        self.setWindowTitle('Введите имя пользователя')
        self.setFixedSize(200, 100)

        self.label = QLabel('Введите имя пользователя')
        self.label.move(10,10)
        self.label.setFixedSize(180,10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(160, 20)
        self.client_name.move(10, 30)

        self.btn_ok = QPushButton('Ок', self)
        self.btn_ok.move(10, 60)
        self.btn_ok.clicked.connect(self.ok_press)

        self.btn_cancl = QPushButton('Выход', self)
        self.btn_cancl.move(100, 60)
        self.btn_cancl.clicked.connect(qApp.exit)

        self.show()


    def ok_press(self):
        if self.client_name.text():
            self.ok_pressed = True
            qApp.exit()


