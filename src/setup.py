import src.logging as logging

_logger = logging.getLogger("setup")

def init_hw():
    _logger.info('HW setup started')
    init_rtc()
    _logger.info('HW setup ended')

def mosfet_sensors(state):
    from machine import Pin
    mosfet = Pin('P4', mode=Pin.OUT)
    mosfet(state)

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
                break

            mk_on_boot_fn('rtc_set')(value=1)
            _logger.info('RTC Time set from NTP')
            time_set = True
            radio.deinit()
            break

        if not time_set:
            _logger.error(msg)
            raise Exception(msg)

    correct_time = True
    yy, _, _, _, _, _, _, _ = ds3231.get_time()
    if yy < 2019:
        correct_time = False

    if not mk_on_boot_fn('rtc_set', default=False)():
        _setup_rtc()

    if mk_on_boot_fn('rtc_set', default=False)() and not correct_time:
        _logger.error('RTC should have been already set but it is not. Something is wrong! System will try to fix it if possible...')
        _setup_rtc()
        
    if not mk_on_boot_fn('rtc_set', default=False)():
        _logger.error(msg)
        raise Exception(msg)

    tt = ds3231.get_time(set_rtc = True)
    _logger.info('Time is: %s', format_time(tt))
