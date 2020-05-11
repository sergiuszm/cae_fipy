from src.mqtt import MQTTClient
from src.globals import CK_MQTT_SERVER, CK_MQTT_PORT, CK_TCP_SERVER, CK_TCP_PORT, CK_TCP_BUFF_SIZE, TRACEBACK, CK_NBIOT_PART_SIZE, F_SENDING
from src.globals import CK_UDP_SERVER, CK_UDP_PORT, RADIO_NBT
from src.timeutil import TimedStep
from src.setup import hardware_id
import src.logging as logging
import socket
from src.fileutil import file_size, isfile
import time
from src.storage import AggregatedMetric
import binascii
from src.comm import NBT
from uhashlib import sha256


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
    def __init__(self, comm):
        self.client_id = hardware_id()
        self.mqtt_client = None
        self.mqtt_connected = False
        self.comm = comm

    def deinit(self):
        if self.mqtt_connected:
            self.mqtt_client.disconnect()
            self.mqtt_connected = False

        self.comm.deinit()

    def send_msg_mqtt(self, topic, message):
        if self.mqtt_client is None:
            self.mqtt_client = MQTTClient(self.client_id, CK_MQTT_SERVER, CK_MQTT_PORT)

        if self.mqtt_connected is False:
            self.mqtt_client.connect()
            self.mqtt_connected = True

        self.mqtt_client.publish('/cae/{}/{}'.format(self.client_id, topic), message.encode())

    def send_file_tcp(self, path, live_file=False):
        if isfile(path) is False:
            _logger.warning('Can\'t send file:{}. It doesn\'t exist'.format(path))
            return

        if not self.comm.connected:
            self.comm.connect() 

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
                AggregatedMetric.write(TRACEBACK, 1)

    def send_file_udp(self, path):
        if isfile(path) is False:
            _logger.warning('Can\'t send file:{}. It doesn\'t exist'.format(path))
            return

        if not self.comm.connected:
            self.comm.connect()

        s = None
        if self.comm.type == RADIO_NBT:
            from src.nbiotpy import FakeUDPSocket
            s = FakeUDPSocket(self.comm)

        if s is None:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        _logger.info('Attempt to send file: %s', path)

        addr = (CK_UDP_SERVER, CK_UDP_PORT)
        path_parts = path.split('/')
        file_name = path_parts.pop()
        start_msg = "0#{}#{}#{}#{}"
        f_size = file_size(path)
        info = 'Sending file of size {} bytes'.format(f_size)
        with TimedStep(info, code=F_SENDING, logger=_logger):
            with open(path, 'rb') as f:
                data = f.read()
                hexified_data = binascii.hexlify(data).decode()
                sha = sha256(data)
                checksum = binascii.hexlify(sha.digest()).decode()
                data_len = len(hexified_data)

                if data_len > CK_NBIOT_PART_SIZE:
                    parts = [data[i:i + CK_NBIOT_PART_SIZE] for i in range(0, len(data), CK_NBIOT_PART_SIZE)]
                    _logger.info('Parts to send: {}'.format(len(parts)))
                    start_msg = start_msg.format(self.client_id, file_name, len(parts), checksum)
                    s.sendto(start_msg, addr)
                    counter = 1
                    for part in parts:
                        msg = "{}#{}#{}".format(counter, self.client_id, binascii.hexlify(part).decode())
                        s.sendto(msg, addr)
                        counter += 1
                else:
                    start_msg = START_MSG.format(self.client_id, file_name, 1, checksum)
                    s.sendto(start_msg, addr)

        s.close()

