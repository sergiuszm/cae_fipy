import pycom    
pycom.heartbeat_on_boot(False)
pycom.smart_config_on_boot(False)
pycom.wifi_on_boot(False)
import network
server = network.Server()
server.deinit() 

import src.logging as logging
from src.globals import CK_OP_FREQ, CK_BOOT_NR, CK_DAY_CHANGED, CK_DAY_NR, CK_SLEEP_FOR, CK_UPDATE_AVAILABLE, CK_WDT_TIMEOUT
from machine import WDT
from src.timeutil import TimedStep
from src.pycom_util import mk_on_boot_fn

_logger = logging.getLogger("boot")
wdt = WDT(timeout=CK_WDT_TIMEOUT * 1000)

def boot():
    

    from machine import reset_cause, WDT_RESET
    if WDT_RESET == reset_cause():
        _logger.info('WDT reset happened!')
        deinit_and_deepsleep()

    _logger.info('Booting')

    boot_nr = mk_on_boot_fn(CK_BOOT_NR, default=0)()
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
            sd.move_logs(day_nr - 1)
            sd.deinit()
            mosfet_sensors(False)
        except Exception as e:
            _logger.traceback(e)
            wdt.feed()
            log_days = {day_nr - 1: False, day_nr: True}
            connect_and_send_log(log_days)

        _logger.info('Going into deepsleep for %d s ...', 1)
        deinit_and_deepsleep(1)

    # boot_nr % CK_OP_FREQ == 1: check for update and if there is one available prepare to download it next time
    # boot_nr % CK_OP_FREQ == 2: if there is scheduled update then it will be downloaded and installed
    try:
        if boot_nr % CK_OP_FREQ == 1:
            _logger.info('Checking for update')
            connect_and_get_update()
            deinit_and_deepsleep(1)
        
        if boot_nr % CK_OP_FREQ == 2:
            update_available = mk_on_boot_fn(CK_UPDATE_AVAILABLE, default=0)()
            if update_available:
                connect_and_get_update()
            deinit_and_deepsleep(1)
        
    except Exception as e:
        _logger.error('Update failed. Reason %s', e)
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
    selected_radio = connect_any([WLAN(), LTE()])
    sender = DataSender()
    for day_to_send in days_to_send:
        source = '/flash/logs/{}.txt'.format(day_to_send)   
        if fileutil.isfile(source) is False:
            continue
        
        live_log = days_to_send[day_to_send]
        sender.send_file(source, live_file=live_log)
    
    sender.deinit()
    selected_radio.deinit()
    current_day = mk_on_boot_fn(CK_DAY_NR, default=0)()
    
    from os import listdir, remove
    with TimedStep('Removing old logs', logger=_logger):
        files = listdir('/flash/logs')
        for f in files:
            p_day, _ = f.split('.')
            if int(p_day) in [int(current_day) - 1, int(current_day)]:
                continue
            
            _logger.info('Removing log: %s', '/flash/logs/{}'.format(f))
            remove('/flash/logs/{}'.format(f))


def connect_and_get_update():
    from src.comm import WLAN, LTE
    from src.netutil import connect_any

    selected_radio = connect_any([LTE(), WLAN()])
    if selected_radio is not None:
        from src.ota_updater import OTAUpdater
        token='ceab660119b1b41a87055d1b2eb9715c946a00b3'
        updater = OTAUpdater('https://github.com/sergiuszm/cae_fipy', headers={'Authorization': 'token {}'.format(token)})
        updater.download_and_install_update_if_available()
        selected_radio.deinit()

def deinit_and_deepsleep(sleep_for=CK_SLEEP_FOR):
    with TimedStep('Deinit for deepsleep', logger=_logger):
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
    if fileutil.isdir('/flash/logs') is False:
        from os import mkdir
        mkdir('/flash/logs')

    with TimedStep('Boot', logger=_logger):
        boot()
    
    deinit_and_deepsleep()
except Exception as e:
    _logger.traceback(e)
    deinit_and_deepsleep()
