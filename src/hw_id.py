def hardware_id():
    import ubinascii
    import machine

    return ubinascii.hexlify(machine.unique_id()).decode("ascii")

