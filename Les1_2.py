'''
Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
'''
from ipaddress import ip_address
from Les1_1 import host_ping

def host_range_ping(begin_ip, end_ip, printed=False):
    begin_num = int(begin_ip.split('.')[3])
    end_num = int(end_ip.split('.')[3])
    addr_list = []
    for addr in range(begin_num, end_num+1):
        addr_list.append(ip_address(begin_ip[0: begin_ip.rfind('.')+1] + str(addr)))
    return host_ping(addr_list, printed=printed)



if __name__ == '__main__':
    lst = host_range_ping('192.0.2.16', '192.0.2.36', printed=True)
