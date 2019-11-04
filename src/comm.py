import src.logging as logging
from machine import Timer, Pin
import network
import time
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


    def __init__(self, mosfet='P8', pins=('P3', 'P16'), debug=False):

        self._mosfet = Pin(mosfet, mode=Pin.OUT)
        self._mosfet(True)
        self._pins = pins
        self._nb = None
        self._sql = None
        self.__debug = debug

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

    def get_id(self):
        if self._nb is None:
            return

        cimi = self._nb.get_imsi()
        ccid = self._nb.get_ccid()
        _logger.info("NBIoT CIMI: %s, CCID: %s", cimi, ccid)


class LTE:
    def __init__(self):
        self._lte = None
        self._sql = None

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
            return

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
    def __init__(self):
        self._ssid = None
        self._sql = None
        self._wlan = None

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
        if self._wlan is not None:
            with TimedStep("WLAN deinit"):
                self._wlan.deinit()
        
        self._ssid = None
        self._sql = None