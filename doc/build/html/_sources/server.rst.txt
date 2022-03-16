Servers module documentation
=================================================

server.py
~~~~~~~~~

Запускаемый модуль,содержит парсер аргументов командной строки и функционал инициализации приложения.

server. **arg_parser** ()
    Парсер аргументов командной строки, возвращает кортеж из 4 элементов:

	* адрес с которого принимать соединения
	* порт
	* флаг запуска GUI

server. **config_load** ()
    Функция загрузки параметров конфигурации из ini файла.
    В случае отсутствия файла задаются параметры по умолчанию.

core.py
~~~~~~~~~~~

.. autoclass:: server.core.MessageProcessor
	:members:


server_database.py
~~~~~~~~~~~~~~~~~~

.. autoclass:: server.server_database.ServerStorage
	:members:

main_window.py
~~~~~~~~~~~~~~

.. autoclass:: server.main_window.MainWindow
	:members:

registr_window.py
~~~~~~~~~~~~~~~~~

.. autoclass:: server.registr_window.RegistrUser
	:members:

remove_window.py
~~~~~~~~~~~~~~~~~

.. autoclass:: server.remove_window.DeleteUser
	:members:

config_window.py
~~~~~~~~~~~~~~~~~

.. autoclass:: server.config_window.ConfigWindow
	:members:

stat_window.py
~~~~~~~~~~~~~~~~~

.. autoclass:: server.stat_window.StatWindow
	:members: