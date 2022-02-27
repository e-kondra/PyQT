import datetime
import logging

from tabulate import tabulate
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import mapper, sessionmaker, join


class ServerStorage:
    class Users:
        def __init__(self, username):
            self.id = None
            self.username = username
            self.last_login = datetime.datetime.now()

    class UsersHistory:
        def __init__(self, ip, port, user, date):
            self.id = None
            self.ip = ip
            self.port = port
            self.user = user
            self.date = date

    class ActiveUsers:
        def __init__(self, user, login_time, ip, port):
            self.id = None
            self.user = user
            self.login_time = login_time
            self.ip = ip
            self.port = port

    # Класс отображение таблицы истории действий
    class UsersActionHistory:  # add_new
        def __init__(self, user):
            self.id = None
            self.user = user
            self.sent = 0
            self.accepted = 0

    class UsersContacts:
        def __init__(self, user, contact):
            self.id = None
            self.user = user
            self.contact = contact

    def __init__(self, path):
        self.engine = create_engine(f'sqlite:///{path}', echo=False, pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        users_table = Table('Users', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('username', String, unique=True),
                            Column('last_login', DateTime)
                            )
        users_history_table = Table('UsersHistory', self.metadata,
                                    Column('id', Integer, primary_key=True),
                                    Column('ip', String),
                                    Column('port', Integer),
                                    Column('user', ForeignKey('Users.id')),
                                    Column('date', DateTime)
                                    )
        active_users_table = Table('ActiveUsers', self.metadata,
                                   Column('id', Integer, primary_key=True),
                                   Column('user', ForeignKey('Users.id'), unique=True),
                                   Column('login_time', DateTime),
                                   Column('ip', String),
                                   Column('port', Integer)
                                   )
        users_action_history_table = Table('UsersActionHistory', self.metadata,
                                           Column('id', Integer, primary_key=True),
                                           Column('user', ForeignKey('Users.id'), unique=True),
                                           Column('sent', Integer),
                                           Column('accepted', Integer)
                                           )
        users_contacts_table = Table('UsersContacts', self.metadata,
                                     Column('id', Integer, primary_key=True),
                                     Column('user', ForeignKey('Users.id')),
                                     Column('contact', ForeignKey('Users.id'))
                                     )
        # создали таблицы
        self.metadata.create_all(self.engine)
        # Связываем таблицы и классы. Сколько сущностей, столько и таблиц, столько связок
        mapper(self.Users, users_table)
        mapper(self.UsersHistory, users_history_table)
        mapper(self.ActiveUsers, active_users_table)
        mapper(self.UsersActionHistory, users_action_history_table)
        mapper(self.UsersContacts, users_contacts_table)
        # сессию создаем
        SESSION = sessionmaker(bind=self.engine)
        self.session = SESSION()
        # удаляем все из таблицы активных пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def login(self, username, ip, port):
        try:
            res = self.session.query(self.Users).filter_by(username=username)
        except Exception as err:
            logging.warning(err)
        if res.count():
            # print('result.count')
            user = res.first()
            user.last_login = datetime.datetime.now()
        else:
            # print('new')
            # создаем нового пользователя
            user = self.Users(username)
            # print(f'user={user.id}')
            self.session.add(user)
            self.session.commit()
            users_action = self.UsersActionHistory(user.id)
            self.session.add(users_action)
        # записываем пользователя в таблицу активных пользователей
        active_user = self.ActiveUsers(user.id, datetime.datetime.now(), ip, port)
        self.session.add(active_user)
        # и добавляем в историю запись о входе пользователя
        users_visit = self.UsersHistory(ip, port, user.id, datetime.datetime.now())
        self.session.add(users_visit)
        # сохраняем данные в БД
        self.session.commit()

    def logout(self, username):
        # нашли пользователя
        user = self.session.query(self.Users).filter_by(username=username).first()
        # нашли и удалили активного пользователя
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    # фиксация передачи сообщения и отметки в БД
    def process_message(self, sender, recipient):
        sender = self.session.query(self.Users).filter_by(username=sender).first().id
        recipient = self.session.query(self.Users).filter_by(username=recipient).first().id
        send_row = self.session.query(self.UsersActionHistory).filter_by(user=sender).first()
        send_row.sent += 1
        rec_row = self.session.query(self.UsersActionHistory).filter_by(user=recipient).first()
        rec_row.accepted += 1
        self.session.commit()


    def users_list(self):
        query = self.session.query(
            self.Users.username,
            self.Users.last_login
        )
        return query.all()
        # return tabulate(query.all(), headers=['user', 'last_connect'], tablefmt='grid')

    def active_users_list(self):
        query = self.session.query(
            self.Users.username,
            self.ActiveUsers.login_time,
            self.ActiveUsers.ip,
            self.ActiveUsers.port).join(self.Users)
        # return tabulate(query.all(), headers=['user', 'login_time', 'ip', 'port'], tablefmt='grid')
        return query.all()

    def users_history(self, username=None):
        query = self.session.query(
            self.Users.username,
            self.UsersHistory.date,
            self.UsersHistory.ip,
            self.UsersHistory.port
        ).join(self.Users)
        if username:
            query = query.filter(self.Users.username == username)
        # return tabulate(query.all(), headers=['user', 'login_time', 'ip', 'port'], tablefmt='grid')
        return query.all()

    def message_history(self):
        query = self.session.query(
            self.Users.username,
            self.Users.last_login,
            self.UsersActionHistory.sent,
            self.UsersActionHistory.accepted
        ).join(self.Users)
        # Возвращаем список кортежей
        return query.all()

    def get_contacts(self, username):
        user = self.session.query(self.Users).filter_by(username=username).one()
        query = self.session.query(self.UsersContacts, self.Users.username).\
            filter_by(user=user.id).join(self.Users,self.UsersContacts.contact == self.Users.id)
        return [contact[1] for contact in query.all()]

# Отладка
if __name__ == '__main__':
    test_db = ServerStorage()
    # выполняем 'подключение' пользователя
    test_db.login('client_1', '192.168.1.4', 8888)
    test_db.login('client_2', '192.168.1.5', 7777)
    # выводим список кортежей - активных пользователей
    print(test_db.active_users_list())
    # выполянем 'отключение' пользователя
    test_db.logout('client_1')
    # выводим список активных пользователей
    print(test_db.active_users_list())
    # запрашиваем историю входов по пользователю
    test_db.users_history('client_1')
    # выводим список известных пользователей
    print(test_db.users_list())
