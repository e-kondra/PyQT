import datetime
import os

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import mapper, sessionmaker


class ClientDatabase:
    class KnownUsers:
        def __init__(self, username):
            self.id = None
            self.username = username

    class MessageHistory:
        def __init__(self, contact, direction, message):
            self.id = None
            self.contact = contact
            self.direction = direction
            self.message = message
            self.date = datetime.datetime.now()

    class Contacts:
        def __init__(self, contact):
            self.id = None
            self.contact = contact

    def __init__(self, name):
        # Создаём движок базы данных, поскольку разрешено несколько клиентов одновременно, каждый должен иметь свою БД
        # Поскольку клиент мультипоточный необходимо отключить проверки на подключения с разных потоков,
        # иначе sqlite3.ProgrammingError
        path = os.path.dirname(os.path.realpath(__file__))
        filename = f'client_{name}.db3'
        self.engine = create_engine(f'sqlite:///{os.path.join(path, filename)}', echo=False, pool_recycle=7200,
                                             connect_args={'check_same_thread': False})
        self.metadata = MetaData()

        known_users = Table('KnownUsers', self.metadata,
                            Column('id', Integer, primary_key=True),
                            Column('username', String)
                            )
        message_history = Table('MessageHistory', self.metadata,
                                Column('id', Integer, primary_key=True),
                                Column('contact', String),
                                Column('direction', String),
                                Column('message', Text),
                                Column('date', DateTime)
                                )
        contacts = Table('Contacts', self.metadata,
                         Column('id', Integer, primary_key=True),
                         Column('contact', String, unique=True)
                         )
        # создали таблицы
        self.metadata.create_all(self.engine)
        # Связываем таблицы и классы. Сколько сущностей, столько и таблиц, столько связок
        mapper(self.KnownUsers, known_users)
        mapper(self.MessageHistory, message_history)
        mapper(self.Contacts, contacts)
        # сессию создаем
        SESSION = sessionmaker(bind=self.engine)
        self.session = SESSION()

        self.session.query(self.Contacts).delete()
        self.session.commit()

    # добавление известных пользователей.
    def add_users(self, users_list):
        self.session.query(self.KnownUsers).delete() # Пользователи получаются только с сервера, поэтому таблица очищается.
        for user in users_list:
            row = self.KnownUsers(user)
            self.session.add(row)
        self.session.commit()

    # добавление контакта
    def add_contact(self, contact):
        if not self.session.query(self.Contacts). filter_by(contact=contact).count():
            row = self.Contacts(contact)
            self.session.add(row)
            self.session.commit()

    def get_contacts(self):
        return [contact[0] for contact in self.session.query(self.Contacts.contact).all()]

    def get_users(self):
        return [user[0] for user in self.session.query(self.KnownUsers.username).all()]

    def check_user(self, username):
        return True if self.session.query(self.KnownUsers).filter_by(username=username).count() else False

    def check_contact(self, username):
        return True if self.session.query(self.Contacts).filter_by(contact=username).count() else False

    def del_contact(self, username):
        self.session.query(self.Contacts).filter_by(contact=username).delete()

    def save_message(self, contact, direction, message):
        row = self.MessageHistory(contact, direction, message)
        self.session.add(row)
        self.session.commit()

    def get_history(self, contact):
        query = self.session.query(self.MessageHistory).filter_by(contact=contact)
        return [(row.contact, row.direction, row.message, row.date) for row in query.all()]



if __name__ == '__main__':
    test_db = ClientDatabase('test1')
    for i in ['test3', 'test4', 'test5']:
        test_db.add_contact(i)
    test_db.add_contact('test4')
    test_db.add_users(['test1', 'test2', 'test3', 'test4', 'test5'])
    test_db.save_message('test1', 'test2', f'Привет! я тестовое сообщение от {datetime.datetime.now()}!')
    test_db.save_message('test2', 'test1', f'Привет! я другое тестовое сообщение от {datetime.datetime.now()}!')
    print(test_db.get_contacts())
    print(test_db.get_users())
    print(test_db.check_user('test1'))
    print(test_db.check_user('test10'))
    print(test_db.get_history('test2'))
    print(test_db.get_history(to_user='test2'))
    print(test_db.get_history('test3'))
    test_db.del_contact('test4')
    print(test_db.get_contacts())