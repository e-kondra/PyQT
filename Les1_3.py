'''
Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2.
Но в данном случае результат должен быть итоговым по всем ip-адресам,
представленным в табличном формате (использовать модуль tabulate).
'''
from tabulate import tabulate

from Les1_2 import host_range_ping


def host_range_ping_tab(start_ip, end_ip):
    print(tabulate(host_range_ping(start_ip, end_ip), headers='keys', tablefmt='grid'))



if __name__ == '__main__':
    host_range_ping_tab('142.250.68.46', '142.250.68.69')