import pycom

pycom.heartbeat(False)
pycom.smart_config_on_boot(False)

from src.main import main
main()