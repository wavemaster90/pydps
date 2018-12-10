import minimalmodbus
import serial
import enum
import numpy as np


class ParamName(enum.Enum):
    """
    Enum class containing the register addresses of all DPS variables and parameters
    """
    V_SET = 0x0000      #: Set voltage (R/W)
    I_SET = 0x0001      #: Set current
    V_OUT = 0x0002      #: Output voltage
    I_OUT = 0x0003      #: Output current
    P_OUT = 0x0004      #: Output power
    V_IN = 0x0005       #: Input voltage
    LOCK = 0x0006       #: Key lock
    PROTECT = 0x0007    #: Protection status
    CV_CC = 0x0008      #: Regulation mode
    ON_OFF = 0x0009     #: Output enable
    B_LED = 0x000A      #: LED backlight brightness
    MODEL = 0x000B      #: Model number
    VERSION = 0x000C    #: Firmware version number


class SettingName(enum.Enum):
    """
    Enum class containing the relative addresses of all DPS data group settings
    """
    V_SET = 0x0000  #: Set voltage
    I_SET = 0x0001  #: Set  current
    OVP = 0x0002    #: Over voltage protection voltage
    OCP = 0x0003    #: Over current protection current
    OPP = 0x0004    #: Over power protection power
    B_LED = 0x0005  #: LED backlight brightness
    M_PRE = 0x0006  #: Memory preset number
    INI = 0x0007    #: Initial output state


class DataGroup(enum.Enum):
    """
    Enum class containing all data group base addresses
    """
    M0 = 0x0000
    M1 = 0x0010
    M2 = 0x0020
    M3 = 0x0030
    M4 = 0x0040
    M5 = 0x0050
    M6 = 0x0060
    M7 = 0x0070
    M8 = 0x0080
    M9 = 0x0090


class ParamInfo:
    """
    'Data class' containing all information about a parameter

    :param read: read access flag
    :param write: write access flag
    :param unit: scientific unit of parameter
    :param description: human readable value description
    :param value_range: value range of parameter
    :param integer: flag indicating only integer values are allowed
    """
    def __init__(self, read, write, unit, description, value_range=None, integer=False):
        """
        Class constructor

        :param read: read access flag
        :param write: write access flag
        :param unit: scientific unit of parameter
        :param description: human readable value description
        :param value_range: value range of parameter
        :param integer: flag indicating only integer values are allowed
        """
        self.read = read                #: read access flag
        self.write = write              #: write access flag
        self.unit = unit                #: scientific unit of parameter
        self.description = description  #: human readable value description
        self.value_range = value_range  #: value range of parameter
        self.integer = integer          #: flag indicating only integer values are allowed


class PyDPS(minimalmodbus.Instrument):
    """
    DPS interface class for python.

    The DPSXXXX power supplies use the ModBus protocol for communication. This class uses the
    :class:`minimalmodbus.Instrument` class to take care of the low-level ModBus implementation and provides a boiler
    plate to easily access and control the power supply, without the need of remembering register addresses

    :param port_name: ParamName of the COM port as string
    :param slave_address: Slave address (defaults to one)
    """

    def __init__(self, port_name, slave_address=1):
        """
        Class constructor

        :param port_name: ParamName of the COM port as string
        :param slave_address: Slave address (defaults to one)
        """
        # --------------------------------
        # Initialize the modbus connection
        # --------------------------------
        super().__init__(port_name, slave_address, mode='rtu')
        self.serial.baudrate = 9600
        self.serial.bytesize = 8
        self.serial.parity = serial.PARITY_NONE
        self.serial.stopbits = 1
        self.serial.timeout = 0.5

        # ----------------------------------------
        # Populate the parameter info dictionaries
        # ----------------------------------------
        #: Dictionary containing information about every parameter
        self.ParameterInfo = {
            ParamName.V_SET.value: ParamInfo(True, True, "V", "Set voltage"),
            ParamName.I_SET.value: ParamInfo(True, True, "A", "Set current"),
            ParamName.V_OUT.value: ParamInfo(True, False, "V", "Measured output voltage"),
            ParamName.I_OUT.value: ParamInfo(True, False, "A", "Measured output current"),
            ParamName.P_OUT.value: ParamInfo(True, False, "W", "Measured output power"),
            ParamName.V_IN.value: ParamInfo(True, False, "V", "Measured input voltage"),
            ParamName.LOCK.value: ParamInfo(True, True, "-", "Key lock", [0, 1], True),
            ParamName.PROTECT.value: ParamInfo(True, False, "-", "Protection status", [0, 1], True),
            ParamName.CV_CC.value: ParamInfo(True, False, "-", "Voltage control or current limit mode", [0, 1], True),
            ParamName.ON_OFF.value: ParamInfo(True, True, "-", "Output active state", [0, 1], True),
            ParamName.B_LED.value: ParamInfo(True, True, "-", "Backlight brightness level", [0, 5], True),
            ParamName.MODEL.value: ParamInfo(True, False, "-", "Product model"),
            ParamName.VERSION.value: ParamInfo(True, False, "-", "Firmware version"),
        }

        #: Dictionary containing info about every setting
        self.SettingInfo = {
            SettingName.V_SET.value: ParamInfo(True, True, "V", "Set voltage"),
            SettingName.I_SET.value: ParamInfo(True, True, "A", "Set current"),
            SettingName.OVP.value: ParamInfo(True, True, "V", "Over-voltage protection value"),
            SettingName.OCP.value: ParamInfo(True, True, "A", "Over-current protection value"),
            SettingName.OPP.value: ParamInfo(True, True, "W", "Over-power protection value"),
            SettingName.B_LED.value: ParamInfo(True, True, "-", "Backlight brightness level", [0, 5], True),
            SettingName.M_PRE.value: ParamInfo(True, True, "-", "Memory preset number", [0, 9], True),
            SettingName.INI.value: ParamInfo(True, True, "-", "Power output switch", [0, 1], True),
        }

        # --------------------------------------------------------------------
        # Coerce initial information with data from the connected power supply
        # --------------------------------------------------------------------
        model = str(self.get_model())
        voltage = int(model.split(".")[0])
        current = int(model.split(".")[1])

        max_current = current
        max_voltage = self.get_input_voltage() / 1.1

        self.ParameterInfo[ParamName.V_SET.value].value_range = [0, max_voltage]
        self.ParameterInfo[ParamName.I_SET.value].value_range = [0, max_current]
        self.ParameterInfo[ParamName.V_OUT.value].value_range = [0, max_voltage]
        self.ParameterInfo[ParamName.I_OUT.value].value_range = [0, max_current]
        self.ParameterInfo[ParamName.P_OUT.value].value_range = [0, max_current * max_voltage]

        self.SettingInfo[SettingName.V_SET.value].value_range = [0, max_voltage]
        self.SettingInfo[SettingName.I_SET.value].value_range = [0, max_current]
        self.SettingInfo[SettingName.OVP.value].value_range = [0, voltage * 1.02]
        self.SettingInfo[SettingName.OCP.value].value_range = [0, current * 1.01]
        self.SettingInfo[SettingName.OPP.value].value_range = [0, current * voltage * 1.01]

    # ------------------------------------------------
    # Generic getters and setters for programmatic use
    # ------------------------------------------------
    def get_parameter(self, name):
        """
        Get the current value of a parameter or setting by using either its address or the corresponding enum value

        :param name: register address or corresponding :class:`ParamName`/:class:`SettingName` enum
        :return: the current value of the queried modbus register
        """
        address = self._check_name(name)

        return self.read_register(address, 2)

    def set_parameter(self, name, value):
        """
        Sets a given value to a ModBus register either using its address or the corresponding enum value

        Before writing the register, the value get checked, whether it is writable, in is allowed range and is of
        allowed type.

        :param name: register address or corresponding :class:`ParamName`/:class:`SettingName` enum
        :param value: value to set
        :return:
        """
        address = self._check_name(name)
        self._check_writable(address)
        boolean = self._check_value(address, value)

        if boolean:
            self.write_register(address, value, 0)
        else:
            self.write_register(address, value, 2)

    def get_parameter_info(self, name):
        """
        Get the parameter info of the given parameter

        :param name: register address or corresponding :class:`ParamName`/:class:`SettingName` enum
        :return:
        """
        address = self._check_name(name)

        return self.ParameterInfo[address]

    # -------------------------------
    # Get lists of parameters at once
    # -------------------------------
    def get_all_parameters(self):
        """
        Get all parameters of the power supply in one query

        :return: Dictionary containing the returned values. Accessible via :class:ParamName enum
        """
        response = self.read_registers(0x00, 13)
        data = {
            ParamName.V_SET: response[0] * 0.01,
            ParamName.I_SET: response[1] * 0.01,
            ParamName.V_OUT: round(response[2] * 0.01, 2),
            ParamName.I_OUT: round(response[3] * 0.01, 2),
            ParamName.P_OUT: round(response[4] * 0.01, 2),
            ParamName.V_IN: response[5] * 0.01,
            ParamName.LOCK: response[6],
            ParamName.PROTECT: response[7],
            ParamName.CV_CC: response[8],
            ParamName.ON_OFF: response[9],
            ParamName.B_LED: response[10],
            ParamName.MODEL: response[11],
            ParamName.VERSION: response[12],
        }
        return data

    def get_all_variables(self):
        """
        Get all variable values of the power supply in one query

        :return: Dictionary containing the returned values. Accessible via :class:ParamName enum
        """
        response = self.read_registers(0x00, 11)
        data = {
            ParamName.V_SET: response[0] * 0.01,
            ParamName.I_SET: response[1] * 0.01,
            ParamName.V_OUT: round(response[2] * 0.01, 2),
            ParamName.I_OUT: round(response[3] * 0.01, 2),
            ParamName.P_OUT: round(response[4] * 0.01, 2),
            ParamName.V_IN: response[5] * 0.01,
            ParamName.LOCK: response[6],
            ParamName.PROTECT: response[7],
            ParamName.CV_CC: response[8],
            ParamName.ON_OFF: response[9],
            ParamName.B_LED: response[10]
        }
        return data

    def get_all_measurements(self):
        """
        Get all physical measurement of the power supply in one query

        :return: Dictionary containing the returned values. Accessible via :class:ParamName enum
        """
        response = self.read_registers(ParamName.V_OUT.value, 4)
        data = {
            ParamName.V_OUT: round(response[0] * 0.01, 2),
            ParamName.I_OUT: round(response[1] * 0.01, 2),
            ParamName.P_OUT: round(response[2] * 0.01, 2),
            ParamName.V_IN: round(response[3] * 0.01, 2),
        }
        return data

    def get_set_values(self):
        """
        Get all set values of the power supply in one query

        :return: Dictionary containing the returned values. Accessible via :class:ParamName enum
        """
        response = self.read_registers(ParamName.V_SET.value, 2)
        data = {
            ParamName.V_SET: round(response[0] * 0.01, 2),
            ParamName.I_SET: round(response[1] * 0.01, 2),
        }
        return data

    def get_full_state_info(self):
        """
        Get all state related parameters of the power supply in one query

        :return: Dictionary containing the returned values. Accessible via :class:ParamName enum
        """
        response = self.read_registers(ParamName.LOCK.value, 4)
        data = {
            ParamName.LOCK: response[0],
            ParamName.PROTECT: response[1],
            ParamName.CV_CC: response[2],
            ParamName.ON_OFF: response[3],
        }
        return data

    def get_device_info(self):
        """
        Get all parameters containing information about power supply itself in one query

        :return: Dictionary containing the returned values. Accessible via :class:ParamName enum
        """
        response = self.read_registers(ParamName.MODEL.value, 2)
        data = {
            ParamName.MODEL: response[0],
            ParamName.VERSION: response[1],
        }
        return data

    # ---------------------------------------------------------------
    # Boiler plate getters and setters, for easy use in console style
    # ---------------------------------------------------------------
    def set_voltage(self, voltage):
        """
        Set the set voltage of the power supply with 10 mV precision

        :param voltage: desired voltage with 10 mV precision
        :return:
        """
        self.set_parameter(ParamName.V_SET, voltage)

    def get_set_voltage(self):
        """
        Get the set voltage

        :return: set voltage
        """
        return self.get_parameter(ParamName.V_SET)

    def set_current(self, current):
        """
        Set the current limit of the power supply with 10 mV precision

        :param current: max. current with 10 mV precision
        :return:
        """
        self.set_parameter(ParamName.I_SET, current)

    def get_set_current(self):
        """
        Get the set current

        :return: set current
        """
        return self.get_parameter(ParamName.I_SET)

    def get_voltage(self):
        """
        Get the current output voltage with 30 mV precision

        :return: current output voltage
        """
        return self.get_parameter(ParamName.V_OUT)

    def get_current(self):
        """
        Get the output current with 10 mV precision

        :return: output current
        """
        return self.get_parameter(ParamName.I_OUT)

    def get_power(self):
        """
        Get the output power

        :return: output power
        """
        return self.get_parameter(ParamName.P_OUT)

    def get_input_voltage(self):
        """
        Get the input voltage to the DPS

        :return: input voltage
        """
        return self.get_parameter(ParamName.V_IN)

    def set_key_lock(self, lock):
        """
        Enable or disable the key lock for the embedded interface

        :param lock: True to enable lock, false otherwise
        :return:
        """
        self.set_parameter(ParamName.LOCK, lock)

    def get_key_lock(self):
        """
        Get the current status of the key lock

        :return: status of the key lock
        """
        return self.get_parameter(ParamName.LOCK)

    def get_protection_status(self):
        """
        Get the current status of the protection circuit

        :return: status of the protection circuit
        """
        return self.get_parameter(ParamName.PROTECT)

    def get_cc_cv_status(self):
        """
        Get the regulation status of the power supply

        If the returned value is True, the supply is in constant voltage mode. Otherwise it operates in current limit
        mode

        :return: True for CV, False for CC
        """
        return self.get_parameter(ParamName.CV_CC)

    def set_output(self, enable):
        """
        Enable or disable the output

        :param enable: True for enabled, False else
        :return:
        """
        self.set_parameter(ParamName.ON_OFF, enable)

    def get_output(self):
        """
        Query whether the supply has an active output or not

        :return: True if output is active, False else
        """
        return self.get_parameter(ParamName.ON_OFF)

    def set_brightness(self, brightness):
        """
        Set the brightness of the LED backlight

        :param brightness: brightness value from 0 - 5
        :return:
        """
        return self.set_parameter(ParamName.B_LED, brightness)

    def get_brightness(self):
        """
        Get the current brightness level of the LED backlight

        :return: brightness level from 0 - 5
        """
        return self.get_parameter(ParamName.B_LED)

    def get_model(self):
        """
        Get the DPS model number e.g. 50.15

        :return: DPS model number
        """
        return self.get_parameter(ParamName.MODEL)

    def get_firmware_version(self):
        """
        Read the firmware version

        :return: version number
        """
        return self.get_parameter(ParamName.VERSION)

    # -------------------------
    # Variable and value checks
    # -------------------------
    def _check_name(self, name):
        """
        Check the given enum value or register address. Raise an error, if the address is unknown

        :param name: name or register address of the parameter
        :return: register address of the parameter
        """
        if isinstance(name, enum.Enum):
            address = name.value
        else:
            address = name
        if address not in self.ParameterInfo:
            raise ValueError("The parameter address is not known")
        return address

    def _check_writable(self, address):
        """
        Check whether the parameter of the given address is writable

        :param address: verified parameter address
        :return:
        """
        if address in self.ParameterInfo:
            writable = self.ParameterInfo[address].write
        else:
            writable = self.SettingInfo[address].write
        if not writable:
            raise ValueError("The parameter is not writable")

    def _check_value(self, address, value):
        """
        Check whether the given value is allowed to be written into the given register address

        :param address: parameter register address for write operation
        :param value: value to be written
        :return:
        """
        if address in self.ParameterInfo:
            info = self.ParameterInfo[address]
        else:
            info = self.SettingInfo[address]

        if info.integer and not isinstance(value, (int, bool, np.int8, np.int16, np.int32, np.int64, np.intc,
                                                   np.uint, np.uint8, np.uint16, np.uint32, np.uint64, np.uintc)):
            raise ValueError("The value needs to be integer or boolean")

        value_range = info.value_range
        if not value_range:
            raise ValueError("No value range is given")
        elif value < value_range[0] or value > value_range[1]:
            raise ValueError("Value outside of allowed range")

        return info.integer
