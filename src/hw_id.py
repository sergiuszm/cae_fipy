def hardware_id():
    import ubinascii
    import machine

    return ubinascii.hexlify(machine.unique_id()).decode("ascii")

# OU_ID_PATH = "conf/ou-id.json"
# OU_ID_DEFAULTS = {
#             "hw_id": hardware_id(),
#             "site_code": None,
#         }
