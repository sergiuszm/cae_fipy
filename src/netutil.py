from src.mqtt import MQTTClient
from src.hw_id import hardware_id
from src.globals import *

class DataSender:
    def __init__(self):
        self.client_id = hardware_id()
        self.client = MQTTClient(self.client_id, CK_MQTT_SERVER, CK_MQTT_PORT)
        self.client.connect()

    def deinit(self):
        self.client.disconnect()

    def send_msg(self, topic, message):
        self.client.publish('/cae/{}/{}'.format(self.client_id, topic), message.encode())