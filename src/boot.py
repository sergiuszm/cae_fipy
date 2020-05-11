import pycom    
pycom.heartbeat_on_boot(False)
pycom.wifi_on_boot(False)
import network
server = network.Server()
server.deinit() 

import src.logging as logging
from src.globals import CK_OP_FREQ, CK_BOOT_NR, CK_DAY_CHANGED, CK_DAY_NR, CK_SLEEP_FOR, CK_UPDATE_AVAILABLE, CK_WDT_TIMEOUT, BOOT, DEINIT
from src.globals import WATCHDOG, TRACEBACK, ALLOWED_COM_RADIO, RADIO_LTE, RADIO_WLAN, CK_UPDATES_ENABLED, CK_FLASH_LOG_DIR, CK_SD_LOG_DIR
from src.globals import CK_FLASH_DATA_DIR, CK_SD_DATA_DIR, CK_FREE_SPACE_THRESHOLD, CK_LOG_FILES_PATTERN, CK_DATA_FILES_PATTERN
from machine import WDT
from src.timeutil import TimedStep
from src.pycom_util import mk_on_boot_fn
from src.storage import AggregatedMetric

_logger = logging.getLogger("boot")
wdt = WDT(timeout=CK_WDT_TIMEOUT * 1000)

def boot():
    from machine import reset_cause, WDT_RESET
    boot_nr = mk_on_boot_fn(CK_BOOT_NR, default=0)()
    if WDT_RESET == reset_cause():
        AggregatedMetric.write(WATCHDOG, 1)
        _logger.info('WDT reset happened!')
        deinit_and_deepsleep()

    _logger.info('Booting')

    boot_nr += 1
    mk_on_boot_fn(CK_BOOT_NR)(value=boot_nr)

    day_changed = mk_on_boot_fn(CK_DAY_CHANGED, default=0)()
    day_nr = mk_on_boot_fn(CK_DAY_NR, default=0)()
    _logger.info('Boot nr: %d. Day nr: %d', boot_nr, day_nr)
    # log_days = {day_nr - 1: False, day_nr: True}
    # connect_and_send_log(log_days)
    # return

    from os import statvfs
    stat = statvfs('/flash')
    free_space = (stat[0] * stat[3]) / 1024.0 / 1024.0
    _logger.info('Free flash space: %f MB', free_space)

    if float(free_space) < CK_FREE_SPACE_THRESHOLD:
        from src.storage import Flash
        _logger.info('Flash space threshold ({}) reached!'.format(CK_FREE_SPACE_THRESHOLD))
        Flash.remove_old_files(CK_FLASH_LOG_DIR, CK_LOG_FILES_PATTERN)
        Flash.remove_old_files(CK_FLASH_DATA_DIR, CK_DATA_FILES_PATTERN)

    # Saving logs to SD card if day has changed
    if day_changed:
        from src.storage import uSD
        from src.setup import mosfet_sensors
        from machine import reset
        _logger.info('Day has changed (%d -> %d), mooving logs to SD', day_nr, day_nr + 1)
        mk_on_boot_fn(CK_DAY_CHANGED)(value=0)

        day_nr += 1
        mk_on_boot_fn(CK_DAY_NR)(value=day_nr)
        _logger.update_path()
        _logger.info('Changing boot nr to: 0 - new day')
        mk_on_boot_fn(CK_BOOT_NR)(value=0)

        try:
            mosfet_sensors(True)
            sd = uSD()
            wdt.feed()
            sd.move_file(day_nr - 1, '{}.txt'.format(day_nr - 1), CK_FLASH_LOG_DIR, CK_SD_LOG_DIR)
            sd.move_file(day_nr - 1, '{}_aggr.txt'.format(day_nr - 1), CK_FLASH_LOG_DIR, CK_SD_LOG_DIR)
            sd.move_file(day_nr - 1, 'temp-{}.txt'.format(day_nr - 1), CK_FLASH_DATA_DIR, CK_SD_DATA_DIR)
            sd.deinit()
            mosfet_sensors(False)
        except Exception as e:
            _logger.traceback(e)
            AggregatedMetric.write(TRACEBACK, 1)
            wdt.feed()
            log_days = {day_nr - 1: False}
            connect_and_send_log(log_days)

        _logger.info('Going into deepsleep for %d s ...', 1)
        deinit_and_deepsleep(1)

    # boot_nr % CK_OP_FREQ == 1: check for update and if there is one available prepare to download it next time
    # boot_nr % CK_OP_FREQ == 2: if there is scheduled update then it will be downloaded and installed
    try:
        if boot_nr % CK_OP_FREQ == 1 and CK_UPDATES_ENABLED:
            _logger.info('Checking for update')
            connect_and_get_update()
            deinit_and_deepsleep(1)
        
        if boot_nr % CK_OP_FREQ == 2 and CK_UPDATES_ENABLED:
            update_available = mk_on_boot_fn(CK_UPDATE_AVAILABLE, default=0)()
            if update_available:
                connect_and_get_update()
            deinit_and_deepsleep(1)
        
    except Exception as e:
        _logger.error('Update failed. Reason %s', e)
        AggregatedMetric.write(TRACEBACK, 1)
        deinit_and_deepsleep(1)

    # Normal stage of execution
    _logger.info('Normal stage of execution')
    with TimedStep('Main', logger=_logger):
        from src.main import main
        main()

def connect_and_send_log(days_to_send):
    import src.fileutil as fileutil
    from src.comm import WLAN, LTE
    from src.netutil import connect_any, DataSender
    from src.storage import Flash
    
    allowed_radios = [WLAN()]
    if RADIO_LTE in ALLOWED_COM_RADIO:
        allowed_radios.append(LTE())

    # if RADIO_WLAN in ALLOWED_COM_RADIO:
    #     allowed_radios.append(WLAN())

    selected_radio = connect_any(allowed_radios)
    if selected_radio is None:
        return

    sender = DataSender(selected_radio)
    for day_to_send in days_to_send:
        for source_pattern in CK_LOG_FILES_PATTERN:
            f_name = source_pattern.format(day_to_send)
            source = '{}/{}'.format(CK_FLASH_LOG_DIR, f_name)   
            if fileutil.isfile(source) is False:
                continue
        
            live_log = days_to_send[day_to_send]
            sender.send_file_tcp(source, live_file=live_log)
            fileutil.remove_file(source)
    
    sender.deinit()
    selected_radio.deinit()
    Flash.remove_old_files(CK_FLASH_LOG_DIR, CK_LOG_FILES_PATTERN)


def connect_and_get_update():
    from src.comm import WLAN, LTE
    from src.netutil import connect_any

    allowed_radios = []
    if RADIO_LTE in ALLOWED_COM_RADIO:
        allowed_radios.append(LTE())

    if RADIO_WLAN in ALLOWED_COM_RADIO:
        allowed_radios.append(WLAN())

    selected_radio = connect_any(allowed_radios)
    if selected_radio is not None:
        from src.ota_updater import OTAUpdater
        token='ceab660119b1b41a87055d1b2eb9715c946a00b3'
        updater = OTAUpdater('https://github.com/sergiuszm/cae_fipy', headers={'Authorization': 'token {}'.format(token)})
        updater.download_and_install_update_if_available()
        selected_radio.deinit()

def deinit_and_deepsleep(sleep_for=CK_SLEEP_FOR):
    with TimedStep('Deinit for deepsleep', code=DEINIT, logger=_logger):
        from src.setup import mosfet_sensors, disable_radios
        from time import sleep
        from machine import deepsleep

        _logger.info('Mosfet off')
        mosfet_sensors(False)
        disable_radios()
    
    _logger.info('Going into deepsleep for %d s ...', sleep_for)
    deepsleep(sleep_for * 1000)

try:
    import src.fileutil as fileutil
    if fileutil.isdir(CK_FLASH_LOG_DIR) is False:
        from os import mkdir
        mkdir(CK_FLASH_LOG_DIR)

    with TimedStep('Boot', code=BOOT, logger=_logger):
        pycom.rgbled(0x0000FF)
        boot()
        pycom.rgbled(0x007F00)
    
    deinit_and_deepsleep()
except Exception as e:
    pycom.rgbled(0x7F0000)
    _logger.traceback(e)
    AggregatedMetric.write(TRACEBACK, 1)
    deinit_and_deepsleep()
