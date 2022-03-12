import json

from .variables import MAX_PACKAGE_LENGTH, ENCODING
from logs.configs.server_log_config import LOG

def get_message(client):
    '''
    Get bytes, decode to json, from json loads to dictionary
    and return object dict or raise error
    client.py 192.168.1.33 8888
    '''
    try:
        encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    except Exception as err:
        LOG.debug(f'get_message err: {err}')
    # if isinstance(encoded_response, bytes):
    json_response = encoded_response.decode(ENCODING)
    response = json.loads(json_response)

    if isinstance(response, dict):
        return response
    else:
        raise TypeError

def send_message(sock, msg):
    '''
    from str to bytes and sending message in byte-format
    '''
    js_message = json.dumps(msg)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)