Clients module documentation
=================================================

Клиентское приложение для обмена сообщениями. Поддерживает
отправку сообщений пользователям которые находятся в сети, сообщения шифруются
с помощью алгоритма RSA с длинной ключа 2048 bit.


client.py
~~~~~~~~~

Запускаемый модуль,содержит парсер аргументов командной строки и функционал инициализации приложения.

client. **arg_parser** ()
    Парсер аргументов командной строки, возвращает кортеж из 4 элементов:

	* адрес сервера
	* порт
	* имя пользователя
	* пароль

    Выполняет проверку на корректность номера порта.

database.py
~~~~~~~~~~~

.. autoclass:: client.database.ClientDatabase
	:members:

transport.py
~~~~~~~~~~~~

.. autoclass:: client.transport.ClientTransport
	:members:

main_window.py
~~~~~~~~~~~~~~
.. autoclass:: client.main_window.ClientMainWindow
	:members:

user_name_dialog.py
~~~~~~~~~~~~~~~~~~~

.. autoclass:: client.user_name_dialog.UserNameDialog
	:members:

main_window_conv.py
~~~~~~~~~~~~~~~~~~~

.. autoclass:: client.main_window_conv.Ui_MainClientWindow
	:members:

add_contact_dialog.py
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: client.add_contact_dialog.AddContact
	:members:

delete_contact.py
~~~~~~~~~~~~~~~~~

.. autoclass:: client.delete_contact.RemoveContact
	:members: