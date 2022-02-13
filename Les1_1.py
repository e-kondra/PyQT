"""
Написать функцию host_ping(), в которой с помощью утилиты ping
будет проверяться доступность сетевых узлов. Аргументом функции является список,
в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять их доступность с выводом
соответствующего сообщения («Узел доступен», «Узел недоступен»).
При этом ip-адрес сетевого узла должен создаваться с помощью функции ip_address()
"""
from socket import gethostbyname
from ipaddress import ip_address
from subprocess import PIPE,Popen


def host_ping(list_addr, count=1, printed=False):
    result_dict = {'Reachable': [], 'Unreachable': []}
    for addr in list_addr:
        try:
            addr = ip_address(addr)
        except:
            try:
                addr = ip_address(gethostbyname(addr))
            except Exception as err:
                print(f'{addr} ошибка {err}')
                continue
        res = Popen(f'ping /n {count} {addr} ', stdout= PIPE, shell=False)
        res.wait()
        if res.returncode == 0 :
            if printed:
                print(f'узел {addr} доступен')
            result_dict['Reachable'].append(str(addr))
        else:
            if printed:
                print(f'узел {addr} недоступен')
            result_dict['Unreachable'].append(str(addr))
    return result_dict


if __name__ == '__main__':
    list_ip = ['3.1.1.2', '192.168.1.1', 'google.com', '127.0.0.1', '142.250.68.46', '192.0.2.0', '192.0.2.1', '192.0.2.2', 'mail.ru']
    print(host_ping(list_ip, printed=True))