import os
import src.pycom_util as pycom_util
import src.sdcard as sdcard
import src.sdcard_wrapper as sdcard_wrapper
from machine import SPI
import _thread
from src.globals import CK_DAY_NR
import src.fileutil as fileutil
from src.timeutil import TimedStep
import src.logging as logging

_logger = logging.getLogger("storage", to_file=False)

class uSD:

    def __init__(self, cs_pin='P9', pins=('P10', 'P11', 'P14')):
        _spi = pycom_util.SpiWrapper()
        _spi.init(SPI.MASTER, pins=pins)
        self._sd = sdcard_wrapper.SdCardWrapper(_spi, pycom_util.PinWrapper(cs_pin))
        os.mount(self._sd, '/sd')
        self._lock = _thread.allocate_lock()

    def deinit(self):
        os.umount('/sd')
        self._sd = None

    def list_files(self):
        return os.listdir('/sd')
    
    def write(self, file_name, content):
        with self._lock:
            f = open('/sd/{}'.format(file_name), 'a')
            f.write(content)
            f.close()

    def move_logs(self, day_nr):
        if fileutil.isdir('/sd/logs') is False:
            os.mkdir('/sd/logs')

        source = '/flash/logs/{}.txt'.format(day_nr)   
        if fileutil.isfile('/flash/logs/{}.txt'.format(day_nr)) is False:
            return

        destination = '/sd/logs/{}.txt'.format(day_nr)

        with TimedStep('Moving log file', logger=_logger):
            fileutil.copy_file(source, destination)
            os.remove(source)

        with TimedStep('Removing old logs', logger=_logger):
            files = os.listdir('/flash/logs')
            for f in files:
                os.remove('/flash/logs/{}'.format(f))

