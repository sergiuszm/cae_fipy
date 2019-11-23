# main.py -- put your code here!

import time
import utime
from machine import UART, Pin, deepsleep
from src.commands import Commands
from src.thread import Thread
import pycom
from src.nbiotpy import NbIoT
from src.setup import mosfet_sensors, init_hw, disable_radios
import src.logging as logging
from src.globals import *
from src.netutil import DataSender
from src.pycom_util import mk_on_boot_fn
from src.storage import uSD
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
        if last_boot_date != date:
            mk_on_boot_fn(CK_DAY_CHANGED)(value=1)
            mk_on_boot_fn(CK_LAST_BOOT_DATE)(value=date)

        from src.sensors import read_temp
        _logger.info('Read temperature')
        try:
            temps = read_temp()
            sd = uSD()
            if fileutil.isdir('/sd/data') is False:
                mkdir('/sd/data')

            data = '{};{}\n'.format(format_time(tt), temps)
            sd.write('data/temp-{}.txt'.format(date), data)
            sd.deinit()
        except TimeoutError as e:
            data = None
            _logger.error('No temperature readings')
        except Exception as e:
            data = None
            _logger.traceback(e)

        boot_nr = mk_on_boot_fn(CK_BOOT_NR, default=0)()
        if boot_nr % CK_SEND_LOG_EVERY == 0:
            day_nr = mk_on_boot_fn(CK_DAY_NR, default=0)()
            day_to_send = day_nr - 1
            if day_to_send < 0:
                day_to_send = 0

            from src.comm import LTE
            lte = LTE()
            lte.connect()

            sd = uSD()
            sender = DataSender()
            sender.send_file('/sd/logs/{}.txt'.format(day_to_send))
            sd.deinit()
            sender.deinit()
            lte.deinit()


        if boot_nr % CK_SEND_DATA_EVERY == 0:
            _logger.info('Sending data to backend')
            from src.comm import LTE
            lte = LTE()
            lte.connect()

            signal_data = '{};{};{}'.format(format_time(tt), 'LTE', lte._sql)
            sender = DataSender()
            sender.send_msg(CK_MQTT_SQ, signal_data)

            if data is not None:
                sender.send_msg(CK_MQTT_TEMP, data)

            version_data = '{};{}'.format(format_time(tt), OTAUpdater.get_version('/flash/src'))
            sender.send_msg(CK_MQTT_SYS_VER, version_data)
            sender.deinit()
            lte.deinit()

        # from src.comm import LTE
        # lte = LTE()
        # lte.connect()
        # lte.deinit()


        # if boot_nr % 2 == 0:
        # from src.comm import NBT
        # nbiot = NBT(debug=True)
        # nbiot.connect()
        # nbiot.get_id()
        # nbiot.deinit()

    except Exception as e:
        _logger.traceback(e)
        # _logger.error('Execution of main() failed, reason: %s', e)

    # from src.storage import uSD
    # sd = uSD()
    # print(sd.list_files())
    # sd.deinit()
    # mosfet_sensors(False)

    # from src.comm import WLAN
    # wlan = WLAN()
    # wlan.connect()
    
    # if not fileutil.isdir('/flash/data'):
    #     fileutil.mkdirs('/flash/data')

    # if not fileutil.isdir('/flash/log'):
    #     fileutil.mkdirs('/flash/log')


    # Thread(detect_beacon).start()
    # Thread(read_from_uart, commands).start()

    # Thread(cmd.disable_networks).start()
    # cmd.disable_networks()
    # Thread(test_nbiot).start()
    # Thread(sdcard_example).start()

