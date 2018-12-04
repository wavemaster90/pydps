import minimalmodbus
import serial


class PyDPS(minimalmodbus.Instrument):
    """
    DPS interface class for python.

    The DPSXXXX power supplies use the ModBus protocol for communication. This class uses the
    :class:`minimalmodbus.Instrument` class to take care of the low-level ModBus implementation and provides a boiler
    plate to easily access and control the power supply, without the need of remembering register addresses

    :param port_name: Name of the COM port as string
    :param slave_address: Slave address (defaults to one)
    """

    def __init__(self, port_name, slave_address=1):
        """
        Class constructor

        :param port_name: Name of the COM port as string
        :param slave_address: Slave address (defaults to one)
        """
        minimalmodbus.Instrument.__init__(self, port_name, slave_address, mode='rtu')
        self.serial.baudrate = 9600
        self.serial.bytesize = 8
        self.serial.parity = serial.PARITY_NONE
        self.serial.stopbits = 1
        self.serial.timeout = 0.5

    def set_voltage(self, voltage):
        """
        Set the set voltage of the power supply with 10 mV precision

        :param voltage: desired voltage with 10 mV precision
        :return:
        """
        self.write_register(0x0000, voltage, 2)

    def set_current(self, current):
        """
        Set the current limit of the power supply with 10 mV precision

        :param current: max. current with 10 mV precision
        :return:
        """
        self.write_register(0x0001, current, 2)

    def get_voltage(self):
        """
        Get the current output voltage with 30 mV precision

        :return: current output voltage
        """
        return self.read_register(0x0002, 2)

    def get_current(self):
        """
        Get the output current with 10 mV precision

        :return: output current
        """
        return self.read_register(0x0003, 2)

    def get_power(self):
        """
        Get the output power

        :return: output power
        """
        return self.read_register(0x0004, 2)

    def set_output(self, enabled):
        """
        Enable or disable the output

        :param enabled: True for enabled, False else
        :return:
        """
        self.write_register(0x0009, (1 if enabled else 0), 0)

    def get_input_voltage(self):
        """
        Get the input voltage to the DPS

        :return: input voltage
        """
        return self.read_register(0x0005, 2)

    def get_firmware_version(self):
        """
        Read the firmware version

        :return: version number
        """
        return self.read_register(0x000C, 0)

    def get_model(self):
        """
        Get the DPS model number e.g. 50.15

        :return: DPS model number
        """
        return self.read_register(0x000B, 0)

    def set_key_lock(self, enable):
        """
        Enable or disable the key lock for the embedded interface

        :param enable: True to enable lock, false otherwise
        :return:
        """
        self.write_register(0x0006, (1 if enable else 0), 0)

    def get_full_data(self):
        """
        Read all variables at once

        :return: dictionary containing the variable readings
        """
        buffer = self.read_registers(0x00, 10)
        data = {
            "u-set": buffer[0]*0.01,
            "i-set": buffer[1]*0.001,
            "u-out": round(buffer[2]*0.01, 2),
            "i-out": round(buffer[3]*0.01, 2),
            "power": round(buffer[4]*0.01, 2),
            "u-in": buffer[5]*0.01,
            "lock": buffer[6],
            "protect": buffer[7],
            "cvcc": buffer[8],
            "on": buffer[9]}
        return data
