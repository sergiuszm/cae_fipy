from src.mqtt import MQTTClient
from src.globals import CK_MQTT_SERVER, CK_MQTT_PORT, CK_TCP_SERVER, CK_TCP_PORT, CK_TCP_BUFF_SIZE
from src.timeutil import TimedStep
from src.setup import hardware_id
import src.logging as logging
import socket
from src.fileutil import file_size, isfile

BUFF_SIZE = 1024
_logger = logging.getLogger("netutil")

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

    def send_file(self, path):
        if isfile(path) is False:
            _logger.warning('Can\'t send file:{}. It doesn\'t exist')
            return

        _logger.info('Attempt to send file: %s', path)
        s = socket.socket(socket.AF_INET)
        with TimedStep('Connecting to {}:{}'.format(CK_TCP_SERVER, CK_TCP_PORT), logger=_logger):
            s.connect(socket.getaddrinfo(CK_TCP_SERVER, CK_TCP_PORT)[0][-1])

        with TimedStep('Sending file name', logger=_logger):
            path_parts = path.split('/')
            file_name = "{}_{}###".format(self.client_id, path_parts.pop())
            s.send(file_name)

        with TimedStep('Sending file of size {} bytes'.format(file_size(path)), logger=_logger):
            f = open(path, 'rb')
            data = f.read(CK_TCP_BUFF_SIZE)
            while len(data) > 0:
                s.send(data)
                data = f.read(CK_TCP_BUFF_SIZE)
            
            f.close()
            s.close()
