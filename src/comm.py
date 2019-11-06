import src.logging as logging
from machine import Timer, Pin
import network
import time
import ubinascii
from src.nbiotpy import NbIoT

_logger = logging.getLogger("comm")

class TimedStep(object):
    def __init__(self, desc="", suppress_exception=False):
        self.desc = desc
        self.suppress_exception = suppress_exception
        self._tschrono = Timer.Chrono()

    def __enter__(self):
        # wdt.feed()
        self._tschrono.start()
        _logger.info("%s ...", self.desc)

    def __exit__(self, exc_type, exc_value, traceback):
        elapsed = self._tschrono.read_ms()
        # wdt.feed()
        if exc_type:
            _logger.warning("%s failed (%d ms). %s: %s", self.desc, elapsed, exc_type.__name__, exc_value)
            if self.suppress_exception:
                return True
        else:
            _logger.info("%s OK (%f s)", self.desc, elapsed / 1000.0)


class NBT:
    __instance = None

    def __init__(self, mosfet='P8', pins=('P3', 'P16'), debug=False):
        """ Virtually private constructor. """
        if NBT.__instance != None:
            return
        else:
            NBT.__instance = self

        self._mosfet = Pin(mosfet, mode=Pin.OUT)
        self._mosfet(True)
        self._pins = pins
        self._nb = None
        self._sql = None
        self.__debug = debug

    @staticmethod
    def was_created():
        """ Static access method. """
        if NBT.__instance == None:
            return False
        return True

    def connect(self):
        self._nb = NbIoT(pins=self._pins, debug=self.__debug)
        with TimedStep("NBIoT attach"):
            self._nb.connect()
        self._sql = self._nb.get_signal_strength()
        _logger.info("NBIoT attached: %s. Signal quality %s", self._nb.is_attached, self._sql)

    def deinit(self):
        with TimedStep("NBIoT disconnect"):
            self._nb.disconnect()
        
        del self._nb
        self._nb = None
        self._sql = None
        self._mosfet(False)
        NBT.__instance = None

    def get_id(self):
        if self._nb is None:
            return

        cimi = self._nb.get_imsi()
        ccid = self._nb.get_ccid()
        _logger.info("NBIoT CIMI: %s, CCID: %s", cimi, ccid)


class LTE:
    __instance = None

    def __init__(self):
        """ Virtually private constructor. """
        if LTE.__instance != None:
            raise Exception('Call getInstance()')
        else:
            LTE.__instance = self

        self._lte = None
        self._sql = None

    @staticmethod
    def getInstance():
        if LTE.__instance == None:
            LTE()
        return LTE.__instance

    def connect(self):
        tschrono = Timer.Chrono()
        tschrono.start()

        with TimedStep("LTE init"):
            self._lte = network.LTE()

        with TimedStep("LTE attach"):
            self._lte.attach()
            try:
                while True:
                    # wdt.feed()
                    if self._lte.isattached(): 
                        break
                    
                    if tschrono.read_ms() > 180 * 1000: 
                        raise TimeoutError("Timeout during LTE attach")
                    
                    time.sleep_ms(250)
            finally:
                try:
                    self._sql = self.get_signal_strength()['rssi_dbm']
                    _logger.info("LTE attached: %s. Signal quality %s", self._lte.isattached(), self._sql)
                except Exception as e:
                    _logger.exception("While trying to measure and log signal strength: {}".format(e))

        tschrono.reset()
        with TimedStep("LTE connect"):
            self._lte.connect()
            while True:
                # wdt.feed()
                if self._lte.isconnected(): 
                    break
                if tschrono.read_ms() > 120 * 1000: 
                    raise TimeoutError("Timeout during LTE connect")
                
                time.sleep_ms(250)

    def deinit(self):
        self._sql = None

        if self._lte is None:
            self._lte = network.LTE()

        try:
            if self._lte.isconnected():
                with TimedStep("LTE disconnect"):
                    self._lte.disconnect()

            if self._lte.isattached():
                with TimedStep("LTE detach"):
                    self._lte.detach()

        finally:
            with TimedStep("LTE deinit"):
                self._lte.deinit()

        self._lte = None
        LTE.__instance = None

    def get_signal_strength(self):
        output = self._lte.send_at_cmd("AT+CSQ")
        prefix = "\r\n+CSQ: "
        suffix = "\r\n\r\nOK\r\n"
        rssi_raw, ber_raw, rssi_dbm = None, None, None
        if output.startswith(prefix) and output.endswith(suffix):
            output = output[len(prefix):-len(suffix)]
            try:
                rssi_raw, ber_raw = output.split(",")
                rssi_raw, ber_raw = int(rssi_raw), int(ber_raw)
                rssi_dbm = -113 + (rssi_raw * 2)
            except:
                pass

        return {"rssi_raw": rssi_raw, "ber_raw": ber_raw, "rssi_dbm": rssi_dbm}


class WLAN:
    __instance = None

    def __init__(self):
        """ Virtually private constructor. """
        if WLAN.__instance != None:
            raise Exception('Call getInstance()!')
        else:
            WLAN.__instance = self

        self._ssid = None
        self._sql = None
        self._wlan = None

    @staticmethod
    def getInstance():
        if WLAN.__instance == None:
            WLAN()
        return WLAN.__instance

    def connect(self):
        tschrono = Timer.Chrono()
        self._wlan = network.WLAN(mode=network.WLAN.STA)
        WIFI_TO_CONNECT = {'cpsl': 'quadflawhoAxslope9245', 'Indivisus': 'wcy2150z'}
        nets = self._wlan.scan()
        for net in nets:
            if net.ssid in WIFI_TO_CONNECT:
                self._sql = net.rssi
                self._ssid = net.ssid

                tschrono.start()
                _logger.info("WLAN network found: '%s'. Signal quality %s", self._ssid, self._sql)
                with TimedStep('WLAN connect'):
                    self._wlan.connect(net.ssid, auth=(net.sec, WIFI_TO_CONNECT[net.ssid]), timeout=5000)
                    while not self._wlan.isconnected():
                        if tschrono.read_ms() > 20 * 1000: 
                            raise TimeoutError("Timeout during WiFi connect")
                        time.sleep_ms(250)

                return
        
        raise Exception('Network not found')


    def deinit(self):
        self._ssid = None
        self._sql = None

        if self._wlan is not None:
            with TimedStep("WLAN deinit"):
                self._wlan.deinit()
        
        WLAN.__instance = None


class BLE:
    def __init__(self):
        self._bt = network.Bluetooth()

    def detect_beacon(self):
        self._bt.start_scan(-1)

        def get_adv():
            while True:
                adv = self._bt.get_adv()

                if adv:
                    name = self._bt.resolve_adv_data(adv.data, Bluetooth.ADV_NAME_CMPL)
                    # if name not in ['Holy', 'Fipy']:
                    if name is None:
                        continue
                    
                    # pycom.rgbled(0xff00)
                    # time.sleep(1)
                    # pycom.rgbled(0x0000)
                    # try to get the complete name
                    print('########################################')
                    print("NAME: [{}] {}".format(adv.rssi, name))
                    print("MAC: {}".format(ubinascii.hexlify(adv.mac).decode('utf-8')))
                    mfg_data = self._bt.resolve_adv_data(adv.data, network.Bluetooth.ADV_MANUFACTURER_DATA)

                    if mfg_data:
                        mfg_data = ubinascii.hexlify(mfg_data).decode('utf-8')
                        # try to get the manufacturer data (Apple's iBeacon data is sent here)
                        print("MFG DATA: %s" % (mfg_data))

                    print("DATA: {}".format(ubinascii.hexlify(adv.data).decode('utf-8')))

                    print('#############----------#################')

                time.sleep(1)

        # Thread(get_adv).start()