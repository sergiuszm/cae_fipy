CK_BOOT_NR = 'boot_nr'
CK_DAY_CHANGED = 'day_changed'
CK_DAY_NR = 'day_nr'
CK_LAST_BOOT_DATE = 'last_boot_day'
CK_FIRST_BOOT_DATE = 'first_boot_day'
CK_RTC_SET = 'rtc_set'
CK_UPDATE_AVAILABLE = 'update'

CK_OP_FREQ = 10
# CK_BOOT_UPDATE_NR = 1         #check for update after every X boots
CK_SLEEP_FOR = 15*60             #sleep for X seconds
# CK_CHANGE_DAY_AFTER_BOOTS = int(24 * 60 / CK_SLEEP_FOR) + 1
# CK_SLEEP_AFTER = 180             #go to sleep (no matter what) after X seconds
# CK_SEND_DATA_EVERY = 7          #send data after every X boots
# CK_SEND_LOG_EVERY = 12          #send log after every X boots
# CK_UPDATE_WAITING_FOR = 300     #X seconds for the update to happen
# CK_MOVE_LOGS_WAITING_FOR = 120  #X seconds to move logs from /flash to /sd
CK_WDT_TIMEOUT = 180
CK_WDT_DOWNLOAD_TIMEOUT = 120

CK_MQTT_SERVER = 'lmi034-1.cs.uit.no'
CK_MQTT_PORT = 31417
CK_MQTT_USER = 'ou'
CK_MQTT_PASSWD = 'e90be0bf9fce33ab9c6f6b99d551e603f82897bd'
CK_MQTT_TEMP = 'temperature'
CK_MQTT_SQ = 'signal_quality'
CK_MQTT_SYS_VER = 'system_version'

CK_TCP_SERVER = 'lmi034-1.cs.uit.no'
CK_TCP_PORT = 31416
CK_TCP_BUFF_SIZE = 1024

CK_SYSTEM_VERSION = '0.9'