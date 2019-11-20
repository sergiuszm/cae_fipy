from machine import UART as serial
from machine import Timer
import time
import re
import binascii
from .atcommands import *


class NbIoT:

    def __init__(self, pins=('P3', 'P4'), apn='telenor.iot', mccmnc=24201, socket_port=9000, debug=False):

        self.serial = serial(1, baudrate=9600, pins=pins)
        # Serial(serial_port, 9600, 5.0)

        self.socket = -1
        self.imei = None
        self.imsi = None
        self.ccid = None
        # Mobile Country Code and Mobile Network Code
        self.mccmnc = mccmnc
        self.apn = apn
        self.port = socket_port
        self.is_attached = False

        self._cmd = None
        self._complex_cmd = None
        self._debug = debug

    def __log(self, msg):
        if self._debug:
            print(msg)

    def connect(self):
        self.is_attached = False
        self.reboot()
        self.__radio_on()
        self.__set_apn()
        self.__select_operator()
        if not self.__check_if_attached():
            return False

        self.is_attached = True
        self.__activate_pdp_context()
        self.__create_socket()

        return True

    def disconnect(self):
        self.is_attached = False
        self.__radio_off()
        self.__close_socket()

    def reboot(self):
        self.__log("### REBOOT ###")
        status, _ = self.__execute_cmd(REBOOT)
        self.__log("##############")

        return status

    def ping(self, addr):
        self.__log("### PING ###")
        status = False
        self.set_urc(1)
        self._complex_cmd = NPING.format(addr)
        status, _ = self.__execute_cmd(NPING)
        urc = self.read_urc(15)
        self.set_urc(0)

        pattern = re.compile("\+NPING:\s+.*,(\d+),(\d+)")
        for x in urc:
            search = pattern.match(x)
            try:
                if int(search.group(1)) > 0 and int(search.group(2)) > 0:
                    status = True
                    self.__log(search)
            except IndexError:
                status = False

        self.__log("##############")
        return status

    def send_to(self, data, addr):
        self.__log("### SEND_TO ###")
        cmd = SOST.format(self.socket)
        msg_len = len(data)

        # AT+NSOST=<socket>,<remote_ip_address>,<remote_port>,<length>,<data>
        # AT+NSOST=1,"192.158.5.1",1024,2,"07FF"
        self._complex_cmd = "{},\"{}\",{},{},\"{}\"".format(
            cmd,
            addr[0],
            addr[1],
            msg_len,
            binascii.hexlify(data.encode()).decode('utf-8')
        )

        status, _ = self.__execute_cmd(SOST)
        self.__log("##############")

    def read_urc(self, timeout):
        chrono = Timer.Chrono()
        chrono.start()
        urc = []
        while True:
            x = self.serial.readline()
            if x is None:
                continue

            x = x.decode()
            x = x.replace('\r', '').replace('\n', '')

            if len(x) > 0:
                urc.append(x)
                self.__log("<-- %s" % x)

            elapsed = chrono.read()
            if elapsed >= float(timeout):
                return urc

            time.sleep(0.1)

    def get_signal_strength(self):
        self.__log("### SIGNAL STRENGTH ###")
        status, csq = self.__execute_cmd(CSQ)
        csq = -113 + (int(csq) * 2)
        self.__log("CSQ: {} dBm".format(csq))
        self.__log("##############")

        return csq

    def set_urc(self, n):
        self.__log("### SET URC ###")
        self._complex_cmd = SCONN.format(n)
        status, _ = self.__execute_cmd(SCONN)

    def get_connection_status(self):
        self.__log("### CONNECTION STATUS ###")
        status, _ = self.__execute_cmd(CONS)
        self.__log("##############")

    def get_imei(self):
        self.__log("### IMEI ###")
        if self.imei is None:
            status, self.imei = self.__execute_cmd(IMEI)
        self.__log("##############")

    def get_imsi(self):
        self.__log("### IMSI ###")
        if self.imsi is None:
            status, self.imsi = self.__execute_cmd(IMSI)
        self.__log("##############")

        return self.imsi

    def get_ccid(self):
        self.__log("### IMSI ###")
        if self.ccid is None:
            status, self.ccid = self.__execute_cmd(CCID)
        self.__log("##############")

        return self.ccid

    def get_pdp_context(self):
        self.__log("### PDP CONTEXT")
        status, _ = self.__execute_cmd(CGDCR)
        self.__log("##############")

    def get_pdp_address(self):
        self.__log("### PDP CONTEXT")
        self._complex_cmd = CGPR.format("1")
        status, _ = self.__execute_cmd(CGPR)
        self.__log("##############")

    def __radio_on(self):
        self.__log("### RADIO ON ###")
        status, _ = self.__execute_cmd(RADIO_ON)
        self.__log("##############")

        return status

    def __radio_off(self):
        self.__log("### RADIO OFF ###")
        status, _ = self.__execute_cmd(RADIO_OFF)
        self.__log("##############")

        return status

    # SARA-N2_ATCommands manual, point 9.3 "Response time up to 3 min"
    def __check_if_attached(self, timeout=180.0):
        self.__log("### CHECK IF ATTACHED (up to 180s) ###")
        online = False

        chrono = Timer.Chrono()
        chrono.start()
        while not online:
            elapsed = chrono.read()

            # timeout
            if elapsed >= float(timeout):
                break

            status, cgatt = self.__execute_cmd(GPRS)

            if status:
                online = bool(int(cgatt))

            if online:
                break

            if not online:
                time.sleep(5)
                continue

        self.__log("##############")

        return online

    def __create_socket(self):
        self.__log("### CREATE_SOCKET ###")

        if self.socket < 0:
            self._complex_cmd = SOCR.format(self.port)
            status, self.socket = self.__execute_cmd(SOCR)
            self.socket = int(self.socket)

        self.__log("##############")

    def __close_socket(self):
        self.__log("### CLOSE_SOCKET ###")

        if self.socket >= 0:
            self._complex_cmd = SOCL.format(self.socket)
            status, _ = self.__execute_cmd(SOCL)

        self.socket = -1
        self.__log("##############")

    # def receive_from(self):
    #     self.__log("### RECEIVE ###")
    #     self._complex_cmd = SORF.format(self.socket, 200)
    #
    #     status, _ = self.__execute_cmd(SORF)
    #     self.__log("##############")

    def __set_apn(self):
        self.__log("### SET APN ###")
        self._complex_cmd = CGDCS.format("1,\"IP\",\"{}\"".format(self.apn))
        status, _ = self.__execute_cmd(CGDCS)
        self.__log("##############")

    def __activate_pdp_context(self):
        self.__log("### ACTIVATE PDP CONTEXT")
        self._complex_cmd = CGAC.format("{},{}".format(1, 1))
        status, _ = self.__execute_cmd(CGAC)
        self.__log("##############")

    def __select_operator(self):
        self.__log("### SELECT OPERATOR ###")
        self._complex_cmd = COPS.format("1,2,\"{}\"".format(self.mccmnc))
        status, _ = self.__execute_cmd(COPS)
        self.__log("##############")

    def set_coap_server(self, addr):
        self.__log("### SET COAP SERVER ###")
        self._complex_cmd = COAP.format("0,\"{}\",\"{}\"".format(addr[0], addr[1]))
        status, _ = self.__execute_cmd(COAP)
        self.__log("##############")

    def set_coap_uri(self, addr):
        self.__log("### SET COAP URI ###")
        self._complex_cmd = COAP.format("1,\"/time\"")
        status, _ = self.__execute_cmd(COAP)
        self.__log("##############")

    def set_coap_pdu(self):
        self.__log("### SET COAP PDU ###")
        self._complex_cmd = COAP.format("2,\"4\",\"1\"")
        status, _ = self.__execute_cmd(COAP)
        self._complex_cmd = COAP.format("2,\"0\",\"1\"")
        status, _ = self.__execute_cmd(COAP)
        self._complex_cmd = COAP.format("2,\"1\",\"1\"")
        status, _ = self.__execute_cmd(COAP)
        self._complex_cmd = COAP.format("2,\"2\",\"1\"")
        status, _ = self.__execute_cmd(COAP)
        self.__log("##############")

    def set_current_coap_profile(self):
        self.__log("### SET COAP PROFILE NUMBER ###")
        self._complex_cmd = COAP.format("3,\"0\"")
        status, _ = self.__execute_cmd(COAP)
        self.__log("##############")

    def set_coap_profile_valid_flag(self):
        self.__log("### SET COAP PROFILE VALID FLAG ###")
        self._complex_cmd = COAP.format("4,\"1\"")
        status, _ = self.__execute_cmd(COAP)
        self.__log("##############")

    def save_coap_profile(self):
        self.__log("### SAVE COAP PROFILE ###")
        self._complex_cmd = COAP.format("6,\"0\"")
        status, _ = self.__execute_cmd(COAP)
        self.__log("##############")

    def restore_and_user_coap_profile(self):
        self.__log("### RESTORE AND USE COAP PROFILE ###")
        self._complex_cmd = COAP.format("7,\"0\"")
        status, _ = self.__execute_cmd(COAP)
        self.__log("##############")

    def select_coap_at(self):
        self.__log("### SELECT COAP COMPONENT FOR AT USE ###")
        status, _ = self.__execute_cmd(USELCP)
        self.__log("##############")

    # def do_ucoapc(self):
    #     self.__log("### DO COAPC ###")
    #     self.set_urc(1)
    #     self._complex_cmd = COAPC.format("1")
    #     status, _ = self.__execute_cmd(COAP)
    #     self.__log("--> Waiting for URC")
    #     urc = timeout_decorator.timeout(30)(self.read_urc(30))
    #     print(urc)
    #     self.set_urc(0)
    #     # while True:
    #     #     x = self.serial.readline()
    #     #
    #     #     try:
    #     #         x = x.decode()
    #     #     except UnicodeDecodeError as e:
    #     #         continue
    #     #
    #     #     x = x.replace('\r', '').replace('\n', '')
    #     #
    #     #     if len(x) == 0:
    #     #         time.sleep(0.1)
    #     #         continue
    #     #
    #     #     self.__log("<-- %s" % x)
    #     #     break

    #     self.__log("##############")

    def __execute_cmd(self, cmd):
        self._cmd = cmd
        self.__send_cmd()
        status, expected_value = self.__read_response()

        return status, expected_value

    def __send_cmd(self):
        full_cmd = None
        if not self._complex_cmd:
            full_cmd = "%s%s%s" % (PREFIX, self._cmd, POSTFIX)

        if self._complex_cmd:
            full_cmd = "%s%s%s" % (PREFIX, self._complex_cmd, POSTFIX)
            self._complex_cmd = None

        self.__log("---> %s" % full_cmd)
        self.serial.write(full_cmd)

    def __read_response(self):
        last_line, expected_pattern = RESPONSE[self._cmd]
        expected_line = None
        last_line_found = False
        status = False
        pattern = None

        if expected_pattern is not None:
            pattern = re.compile(expected_pattern)

        while not last_line_found:
            x = self.serial.readline()

            if x is None:
                continue

            try:
                x = x.decode()
            except UnicodeError:
                continue

            x = x.replace('\r', '').replace('\n', '')

            if len(x) == 0:
                time.sleep(0.1)
                continue

            self.__log("<-- %s" % x)

            if x == R_OK:
                status = True

            if x == R_ERROR:
                status = False
                break

            if expected_line is None and expected_pattern is not None:
                search = pattern.match(x)
                
                if search is None:
                    continue

                if len(search.group(0)) > 0:
                    expected_line = search.group(1)

            if x.find(last_line) >= 0:
                last_line_found = True

        return status, expected_line
