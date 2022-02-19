import logging
LOG = logging.getLogger('server')


class Port:
    def __set__(self, instance, value):
        if value < 1024 or value > 65535:
            LOG.critical('В качастве порта может быть указано только число в диапазоне от 1024 до 65535.')
            exit(1)
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class Host:
    def __set__(self, instance, value):
        LOG.debug(f'{value}')
        if value:
            if int(value.split('.')[3]) > 254:
                LOG.critical('Не верный адрес')
                exit(1)
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name