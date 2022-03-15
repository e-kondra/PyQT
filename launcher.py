"""Программа-лаунчер"""
import subprocess

process = []

while True:
    action = input('Выберите действие: q - выход , s - запустить сервер,'
                   ' k - запустить клиенты x - закрыть все окна:')
    if action == 'q':
        break
    elif action == 's':
        # Запускаем сервер!
        try:
            process.append(subprocess.Popen('python server.py',
                                            creationflags=subprocess.CREATE_NEW_CONSOLE))
        except Exception as err:
            print(err)
    elif action == 'k':
        print('Убедитесь, что на сервере зарегистрировано'
              ' необходимое количество клиентов с паролем 123456.')
        print('Первый запуск может быть достаточно долгим'
              ' из-за генерации ключей!')
        clients_count = int(
            input('Введите количество тестовых клиентов для запуска: '))
        # Запускаем клиентов:
        for i in range(clients_count):
            process.append(
                subprocess.Popen(
                    f'python client.py -n test{i + 1} -p 123456',
                    creationflags=subprocess.CREATE_NEW_CONSOLE))
    elif action == 'x':
        while process:
            process.pop().kill()
