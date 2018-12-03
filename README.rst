A small helper library using minimalmodbus for the popular DPSXXXX power supply modules

Dependencies:

*   minimalmodbus
*   pyserial


Usage::

    import pydps

     # connect, using port name and slave address
    dps = pydps.PyDPS('COM3', 1)

    # Show model
    print(dps.get_model())

    # Lock keys on embedded interface
    dps.set_key_lock(True)

    # Set voltage to 12 V
    dps.set_voltage(12)

    # Enable output
    dps.set_output(True)

    # Get current output voltage and current
    print(dps.get_voltage())
    print(dps.get_current())

    # Get all variables at once
    dat = dps.get_full_data()

    # Disable output
    dps.set_output(False)

    # Unlock keys again
    dps.set_key_lock(False)
    
