Common package
=================================================

Пакет общих утилит, использующихся в разных модулях проекта.

Скрипт decors.py
------------------

.. automodule:: common.decors
	:members:

Скрипт descriptors.py
----------------------

.. autoclass:: common.descriptors.Port
	:members:

.. autoclass:: common.descriptors.Host
	:members:

Скрипт errors.py
------------------

.. autoclass:: common.errors.ServerError
	:members:

Скрипт utils.py
------------------

common.utils. **get_message** (client)


	Функция приёма сообщений от удалённых компьютеров. Принимает сообщения JSON,
	декодирует полученное сообщение и проверяет что получен словарь.

common.utils. **send_message** (sock, message)


	Функция отправки словарей через сокет. Кодирует словарь в формат JSON и отправляет через сокет.


Скрипт variables.py
---------------------

Содержит разные глобальные переменные проекта.