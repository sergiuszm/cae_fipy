from src.mqtt import MQTTClient
from src.globals import CK_MQTT_SERVER, CK_MQTT_PORT, CK_TCP_SERVER, CK_TCP_PORT, CK_TCP_BUFF_SIZE
from src.timeutil import TimedStep
from src.setup import hardware_id
import src.logging as logging
import socket
from src.fileutil import file_size, isfile
import time

BUFF_SIZE = 1024
_logger = logging.getLogger("netutil")

def connect_any(radios):
    connected = False
    selected_radio = None
    for radio in radios:
        try:
            radio.connect()
            connected = True
            selected_radio = radio
            break
        except Exception as e:
            _logger.error('Connecting failed. Cause: %s. Repeating with next radio...', e)
            radio.deinit()
            continue

    if connected:
        return selected_radio

    return None

class DataSender:
    def __init__(self):
        self.client_id = hardware_id()
        self.mqtt_client = MQTTClient(self.client_id, CK_MQTT_SERVER, CK_MQTT_PORT)
        self.mqtt_connected = False

    def deinit(self):
        if self.mqtt_connected:
            self.mqtt_client.disconnect()
            self.mqtt_connected = False

    def send_msg(self, topic, message):
        if self.mqtt_connected is False:
            self.mqtt_client.connect()
            self.mqtt_connected = True

        self.mqtt_client.publish('/cae/{}/{}'.format(self.client_id, topic), message.encode())

    def send_file(self, path, live_file=False):
        if isfile(path) is False:
            _logger.warning('Can\'t send file:{}. It doesn\'t exist'.format(path))
            return

        _logger.info('Attempt to send file: %s', path)
        s = socket.socket(socket.AF_INET)
        with TimedStep('Connecting to {}:{}'.format(CK_TCP_SERVER, CK_TCP_PORT), logger=_logger):
            s.connect(socket.getaddrinfo(CK_TCP_SERVER, CK_TCP_PORT)[0][-1])

        f_size = file_size(path)
        info = 'Sending file of size {} bytes'.format(f_size)
        if live_file:
            f_size += len(info)
            f_size += len(' ...')
            f_size += len('INFO:netutil:\n')
        path_parts = path.split('/')
        f_meta = "{}_{}_{}###".format(self.client_id, path_parts.pop(), f_size)
        s.send(f_meta)

        with TimedStep(info, logger=_logger):
            f = None
            try:
                f = open(path, 'rb')
                data = f.read(CK_TCP_BUFF_SIZE)
                while len(data) > 0:
                    s.send(data)
                    data = f.read(CK_TCP_BUFF_SIZE)
                
                f.close()
                s.close()
            except Exception as e:
                if f is not None:
                    f.close()
                s.close()
                _logger.traceback(e)
