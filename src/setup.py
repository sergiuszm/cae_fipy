import src.logging as logging
from src.comm import WLAN, LTE
import network
from src.globals import *
from src.timeutil import TimedStep

_logger = logging.getLogger("setup")

def hardware_id():
    import ubinascii
    import machine

    return ubinascii.hexlify(machine.unique_id()).decode("ascii")

def init_hw():
    _logger.info('HW setup started')
    init_rtc()
    _logger.info('HW setup ended')

def mosfet_sensors(state):
    from machine import Pin
    from time import sleep
    mosfet = Pin('P4', mode=Pin.OUT)
    mosfet(state)
    mosfet.hold(True)

    pins = ['P3', 'P9', 'P10', 'P22', 'P21']
    for pin in pins:
        if state is False:
            p = Pin(pin, mode=Pin.OUT)
            p(True)
            p.hold(True)

        if state is True:
            p = Pin(pin)
            p.hold(False)


def init_rtc():
    from machine import RTC
    import utime
    from src.ds3231 import DS3231
    from src.pycom_util import mk_on_boot_fn
    from src.timeutil import format_time, format_date
    msg = 'RTC is not set. Requires human intervention!'

    ds3231 = DS3231(0, pins=('P21', 'P22'))
    def _setup_from_ntp():
        rtc = RTC(id=0)
        rtc.ntp_sync("0.no.pool.ntp.org")
        utime.sleep_ms(750)

    def _setup_rtc():
        from src.comm import WLAN, LTE
        radios = [WLAN(), LTE()]
        time_set = False
        for radio in radios:
            try:
                radio.connect()
            except Exception as e:
                _logger.error('Connecting failed. Cause: %s. Repeating with next radio...', e)
                continue

            _setup_from_ntp()
            try:
                ds3231.save_time()
            except OSError as e:
                _logger.error('RTC setup failed. Cause: %s.', e)
                _logger.traceback(e)
                break

            mk_on_boot_fn(CK_RTC_SET)(value=1)
            _logger.info('RTC Time set from NTP')
            time_set = True
            radio.deinit()
            break

        if not time_set:
            _logger.error(msg)
            raise Exception(msg)

    correct_time = False
    yy, _, _, _, _, _, _, _ = ds3231.get_time()
    if yy >= 2019:
        correct_time = True

    if not mk_on_boot_fn(CK_RTC_SET, default=False)():
        _setup_rtc()

    if mk_on_boot_fn(CK_RTC_SET, default=False)() and not correct_time:
        _logger.error('RTC should have been already set but it is not. Something is wrong! System will try to fix it if possible...')
        _setup_rtc()
        
    if not mk_on_boot_fn(CK_RTC_SET, default=False)():
        _logger.error(msg)
        raise Exception(msg)

    tt = ds3231.get_time(set_rtc = True)
    _logger.info('Time is: %s', format_time(tt))
    
    first_boot_date = mk_on_boot_fn(CK_FIRST_BOOT_DATE, default=None)()
    if first_boot_date is None:
        first_boot_date = format_date(tt)
        mk_on_boot_fn(CK_FIRST_BOOT_DATE)(value=first_boot_date)

    _logger.info('First boot date: %s', first_boot_date)
    last_boot_date = mk_on_boot_fn(CK_LAST_BOOT_DATE, default=None)()
    if last_boot_date is None:
        last_boot_date = format_date(tt)
        mk_on_boot_fn(CK_LAST_BOOT_DATE)(value=first_boot_date)

def disable_radios():
    from src.comm import NBT
    with TimedStep('LTE deinit', logger=_logger):
        lte = network.LTE()
        lte.deinit()

    with TimedStep('WLAN deinit', logger=_logger):
        wlan = network.WLAN()
        wlan.deinit()

    with TimedStep('NB-IoT deinit', logger=_logger):
        nb = NBT()
        nb.deinit()

def clean_nvs():
    from src.pycom_util import nvs_erase
    from src.globals import CK_BOOT_NR, CK_DAY_CHANGED, CK_DAY_NR, CK_LAST_BOOT_DATE, CK_FIRST_BOOT_DATE, CK_RTC_SET, CK_UPDATE_AVAILABLE

    keys = [CK_BOOT_NR, CK_DAY_CHANGED, CK_DAY_NR, CK_LAST_BOOT_DATE, CK_FIRST_BOOT_DATE, CK_UPDATE_AVAILABLE]
    for key in keys:
        nvs_erase(key)

def clean_fs():
    import os
    from src.storage import uSD
    mosfet_sensors(True)

    files = os.listdir('/flash/logs')
    for f in files:
        os.remove('/flash/logs/{}'.format(f))

    sd = uSD()
    files = os.listdir('/sd/logs')
    for f in files:
        os.remove('/sd/logs/{}'.format(f))

    files = os.listdir('/sd/data')
    for f in files:
        os.remove('/sd/data/{}'.format(f))

    sd.deinit()
    mosfet_sensors(False)
    
