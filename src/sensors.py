import src.logging as logging
import src.onewire as onewire
from machine import Pin
import time
import ubinascii
from machine import Timer
from src.exceptions import TimeoutError

_logger = logging.getLogger("sensors")

def read_temp():
    # external: 284ec84a070000e5
    # internal: 28c2ce170a0000bb
    ow = onewire.OneWire(Pin('P23'))
    sensors = ow.scan()

    while len(sensors) < 2:
        sensors = ow.scan()
        time.sleep_ms(100)

    temp = ""
    _logger.info("Found %d x ds18b20", len(sensors))
    time.sleep_ms(100)
    tschrono = Timer.Chrono()
    tschrono.start()
    for sensor in sensors:
        t = onewire.DS18X20(ow)
        t_reading = None

        t.start_conversion(rom=sensor)
        while not t_reading:
            t_reading = t.read_temp_async(rom=sensor)
            if t_reading == 85.0:
                t_reading = False
            time.sleep_ms(5)

            if tschrono.read_ms() > 15 * 1000: 
                raise TimeoutError("Timeout during reading ds18b20")

        temp += "{} ".format(t_reading)
        tschrono.reset()

    _logger.info("TEMPS: {}".format(temp))

    return temp.strip().replace(' ', ';')

def make_row(ou_id, reading):
    (YY, MM, DD, hh, mm, ss, _, _) = reading["rtime"]
    dateval = "{:04}-{:02}-{:02}".format(YY,MM,DD)
    timeval = "{:02}:{:02}:{:02}".format(hh,mm,ss)
    temp = reading["temp"]
    row_arr = [
            ou_id.hw_id,
            ou_id.site_code,
            dateval,
            timeval,
            temp.join(';')
            ]
    return row_arr

READING_FILE_MATCH = ("readings-", ".csv")
READING_FILE_SIZE_CUTOFF = const(100 * 1024)

def store_reading(ou_id, reading_data_dir, reading):
    row = make_row(ou_id, reading)
    row = ";".join([str(i) for i in row])

    _logger.debug("Data row: %s", row)
    row = row + "\n"
    _logger.debug("Data row: %s bytes", len(row) + 1)

    # Store data in sequential files, in case RTC gets messed up.
    # Then we might be able to guess the times by the sequence of wrong times.

    target = fileutil.prep_append_file(
            dir=reading_data_dir,
            match=READING_FILE_MATCH, size_limit=READING_FILE_SIZE_CUTOFF)

    _logger.debug("Writing data to %s ...", target)
    with open(target, "at") as f:
        f.write(row)
        f.write("\n")
    _logger.info("Wrote row to %s: %s\t", target, row)
    return (target, row)
