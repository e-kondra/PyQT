from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit, QPushButton, qApp, QApplication


class UserNameDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.ok_pressed = False

        self.setWindowTitle('Hi!')
        self.setFixedSize(200, 160)

        self.label = QLabel('Введите имя пользователя:', self)
        self.label.move(10,10)
        self.label.setFixedSize(180,10)

        self.client_name = QLineEdit(self)
        self.client_name.setFixedSize(160, 20)
        self.client_name.move(10, 30)

        self.label = QLabel('Введите пароль:', self)
        self.label.move(10, 70)
        self.label.setFixedSize(180, 10)

        self.client_passwd = QLineEdit(self)
        self.client_passwd.setFixedSize(160, 20)
        self.client_passwd.move(10, 90)
        self.client_passwd.setEchoMode(QLineEdit.Password)

        self.btn_ok = QPushButton('Ок', self)
        self.btn_ok.setFixedSize(80, 30)
        self.btn_ok.move(10, 130)
        self.btn_ok.clicked.connect(self.ok_press)

        self.btn_cancl = QPushButton('Выход', self)
        self.btn_cancl.setFixedSize(80, 30)
        self.btn_cancl.move(100, 130)
        self.btn_cancl.clicked.connect(qApp.exit)

        self.show()


    def ok_press(self):
        if self.client_name.text() and self.client_passwd.text():
            self.ok_pressed = True
            qApp.exit()


if __name__ == '__main__':
    app = QApplication([])
    dial = UserNameDialog()
    app.exec_()
