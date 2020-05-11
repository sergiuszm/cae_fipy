# main.py -- put your code here!

import time
import utime
from machine import UART, Pin, deepsleep
import pycom
from src.setup import mosfet_sensors, init_hw, disable_radios
import src.logging as logging
from src.globals import *
from src.netutil import DataSender
from src.pycom_util import mk_on_boot_fn
from src.storage import uSD, AggregatedMetric, Flash
import src.fileutil as fileutil
from src.timeutil import format_date, format_time
from os import mkdir
from src.ota_updater import OTAUpdater
from src.exceptions import TimeoutError

_logger = logging.getLogger("main")

def main():
    try:
        _logger.info('Starting main()')

        _logger.info('Mosfet ON')
        mosfet_sensors(True)
        _logger.info('Init HW')
        init_hw()

        last_boot_date = mk_on_boot_fn(CK_LAST_BOOT_DATE, default=None)()
        tt = utime.gmtime()
        date = format_date(tt)
        day_nr = mk_on_boot_fn(CK_DAY_NR, default=0)()
        boot_nr = mk_on_boot_fn(CK_BOOT_NR, default=0)()

        # from src.comm import NBT
        
        # sd = uSD()
        # time.sleep(1)
        # sender = DataSender(NBT(debug=True))
        # sender.send_file_udp('{}/{}_aggr.txt'.format(CK_SD_LOG_DIR, 2))
        # sd.deinit()
        # sender.deinit()
        # return

        #TODO: remove the second condition - it is for testing only!
        if last_boot_date != date:# or int(boot_nr) > 110:
            mk_on_boot_fn(CK_DAY_CHANGED)(value=1)
            mk_on_boot_fn(CK_LAST_BOOT_DATE)(value=date)

        from src.sensors import read_temp
        _logger.info('Read temperature')
        try:
            temps = read_temp()
            if fileutil.isdir(CK_FLASH_DATA_DIR) is False:
                mkdir(CK_FLASH_DATA_DIR)

            data = '{}|{}'.format(format_time(tt), temps)
            Flash.write('{}/temp-{}.txt'.format(CK_FLASH_DATA_DIR, day_nr), data)
        except TimeoutError as e:
            data = None
            _logger.error('No temperature readings')
        except Exception as e:
            data = None
            AggregatedMetric.write(TRACEBACK, 1)
            _logger.traceback(e)

        
        if boot_nr % CK_OP_FREQ == 3:
            day_to_send = day_nr - 1
            if day_to_send < 0:
                day_to_send = 0

            if RADIO_LTE in ALLOWED_COM_RADIO:
                from src.comm import LTE

                sd = uSD()
                sender = DataSender(LTE())
                sender.send_file_tcp('{}/{}.txt'.format(CK_SD_LOG_DIR, day_to_send))
                sender.send_file_tcp('{}/{}_aggr.txt'.format(CK_SD_LOG_DIR, day_to_send))
                sender.send_file_tcp('{}/temp-{}.txt'.format(CK_SD_DATA_DIR, day_to_send))
                sd.deinit()
                sender.deinit()

            if RADIO_NBT in ALLOWED_COM_RADIO:
                from src.comm import NBT
                
                sd = uSD()
                sender = DataSender(NBT(debug=True))
                sender.send_file_udp('{}/{}_aggr.txt'.format(CK_SD_LOG_DIR, day_to_send))
                sd.deinit()
                sender.deinit()

    except Exception as e:
        pycom.rgbled(0x007F00)
        _logger.traceback(e)
        AggregatedMetric.write(TRACEBACK, 1)

