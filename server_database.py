import datetime
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

    def __init__(self):
        self.engine = create_engine('sqlite:///server_base.db3', echo=False, pool_recycle=7200)
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
        # создали таблицы
        self.metadata.create_all(self.engine)
        # Связываем таблицы и классы. Сколько сущностей, столько и таблиц, столько связок
        mapper(self.Users, users_table)
        mapper(self.UsersHistory, users_history_table)
        mapper(self.ActiveUsers, active_users_table)
        # сессию создаем
        SESSION = sessionmaker(bind=self.engine)
        self.session = SESSION()
        # удаляем все из таблицы активных пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    def login(self, username, ip, port):
        print(f'username = {username}')
        result = self.session.query(self.Users).filter_by(username=username)
        if result.count():
            print('result.count')
            user = result.first()
            user.last_login = datetime.datetime.now()
        else:
            print('new')
            # создаем нового пользователя
            user = self.Users(username)
            print(f'user={user.id}')
            self.session.add(user)
            self.session.commit()
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


    def users_list(self):
        query = self.session.query(
           self.Users.username,
           self.Users.last_login
        )
        # return query.all()
        return tabulate(query.all(), headers=['user', 'last_connect'], tablefmt='grid')

    def active_users_list(self):
        query = self.session.query(
            self.Users.username,
            self.ActiveUsers.login_time,
            self.ActiveUsers.ip,
            self.ActiveUsers.port).join(self.Users)
        return tabulate(query.all(), headers=['user', 'login_time', 'ip', 'port'], tablefmt='grid')
        # return query.all()

    def users_history(self, username=None):
        query = self.session.query(
            self.Users.username,
            self.UsersHistory.date,
            self.UsersHistory.ip,
            self.UsersHistory.port
        ).join(self.Users)
        if username:
            query = query.filter(self.Users.username==username)
        return tabulate(query.all(), headers=['user', 'login_time', 'ip', 'port'], tablefmt='grid')
        # return query.all()

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