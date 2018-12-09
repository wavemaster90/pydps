from pydps import ParamName, PyDPS
import pytest
import unittest.mock as mock
import minimalmodbus


class MockDPS:
    """
    Mock class for the DPS power supply.

    :param v_max: maximum output voltage
    :param i_max: maximum output current
    :param v_in: given input voltage
    """
    def __init__(self, v_max, i_max, v_in):
        """
        Class constructor

        :param v_max: maximum output voltage
        :param i_max: maximum output current
        :param v_in: given input voltage
        """

        model = float(str(v_max) + "." + str(i_max))

        self.param_registers = {
            0x0000: ["U-SET", True, 5.0],
            0x0001: ["I-SET", True, 1.0],
            0x0002: ["UOUT", False, 0.0],
            0x0003: ["IOUT", False, 0.0],
            0x0004: ["POWER", False, 0.0],
            0x0005: ["UIN", False, v_in],
            0x0006: ["LOCK", True, False],
            0x0007: ["PROTECT", False, False],
            0x0008: ["CV/CC", False, False],
            0x0009: ["ONOFF", True, False],
            0x000A: ["B_LED", True, False],
            0x000B: ["MODEL", False, model],
            0x000C: ["VERSION", False, 0.127],
        }

        v_protect = round(v_max * 1.02, 2)
        i_protect = round(i_max * 1.0133, 2)
        p_protect = round(i_max * v_max * 1.0133, 2)

        self.sett_registers = {
            0x0000: ["U-SET", True, 5.0],
            0x0001: ["I-SET", True, 1.0],
            0x0002: ["S-OVP", True, v_protect],
            0x0003: ["S-OCP", True, i_protect],
            0x0004: ["S-OPP", True, p_protect],
            0x0005: ["B-LED", True, 4],
            0x0006: ["M-PRE", True, 0],
            0x0007: ["S-INI", True, False],
        }

    def read_register(self, register, numberOfDecimals=0):
        """
        Handle read register queries made from the client

        :param register: address of register
        :param numberOfDecimals: precision
        :return:
        """
        info = self._check_valid_register(register)

        print("Register %s read." % info[0])
        return info[2]

    def write_register(self, register, value, numberOfDecimals=0):
        """
        Handle write register commands to DPS

        :param register: address of register
        :param value: Value to be set
        :param numberOfDecimals: precision
        :return:
        """
        info = self._check_valid_register(register)
        self._check_writable(info)

        info[2] = value

    def _check_valid_register(self, register):
        """
        Check if the given register address is valid

        :param register: register address
        :return: register info
        """
        if register in self.param_registers:
            info = self.param_registers[register]
        elif register in self.sett_registers:
            info = self.sett_registers[register]
        else:
            print("Register not recognized.")
            assert False

        return info

    @staticmethod
    def _check_writable(info):
        """
        check if the info states that the register is writable

        :param info: register info
        :return: True, if writable
        """
        if not info[1]:
            print("Tried to write into read-only register")


class MockBase(object):
    """
    New base class, used to replace the modbus.Instrument class with mocks
    """
    mock_modbus = None
    mock_dps = None

    @staticmethod
    def set_mocks(modbus, dps):
        """
        Set the mocks that shall be used as a replacement. Needs to be called prior to :method:`replace`

        :param modbus: modbus mock
        :param dps: dps mock
        :return:
        """
        MockBase.mock_modbus = modbus
        MockBase.mock_dps = dps

    @classmethod
    def replace(cls):
        """
        Replace the real Instrument class with mocks

        :return:
        """
        mock_map = {
            'read_register': cls.mock_dps.read_register,
            'write_register': cls.mock_dps.write_register,
        }
        keep_list = [
            '__repr__'
        ]
        for name in minimalmodbus.Instrument.__dict__:
            if name in mock_map:
                setattr(cls, name, mock_map[name])
            elif name not in keep_list:
                try:
                    setattr(cls, name, cls.mock_modbus)
                except (AttributeError, TypeError):
                    pass
        cls.serial = cls.mock_modbus.serial
        return cls


def initialize_connection(mocker):
    """
    Initialize the connection of :class:`PyDPS` with a mocked DPS over a mocked modbus connection

    :param mocker: mocker object
    :return: PyDPS instance
    :return: mocked modbus
    :return: mocked DPS
    """
    # -------------------
    # Create Mock classes
    # -------------------
    device = MockDPS(50, 15, 48)
    modbus = mocker.Mock()
    serial = mocker.Mock()
    baudrate_mock = mocker.PropertyMock()
    type(serial).baudrate = baudrate_mock
    bytesize_mock = mocker.PropertyMock()
    type(serial).bytesize = bytesize_mock
    parity_mock = mocker.PropertyMock()
    type(serial).parity = parity_mock
    stopbits_mock = mocker.PropertyMock()
    type(serial).stopbits = stopbits_mock
    timeout_mock = mocker.PropertyMock()
    type(serial).timeout = timeout_mock
    type(modbus).serial = serial

    # -----------------------------
    # Replace base class with mocks
    # -----------------------------
    MockBase.set_mocks(modbus, device)
    PyDPS.__bases__ = (MockBase.replace(),)

    # -----------------
    # Initialite client
    # -----------------
    dps = PyDPS("COM8", 1)

    # ---------------------
    # Assert initialization
    # ---------------------
    modbus.assert_called_with("COM8", 1, mode='rtu')
    baudrate_mock.assert_called_with(9600)
    bytesize_mock.assert_called_with(8)
    parity_mock.assert_called_with('N')
    stopbits_mock.assert_called_with(1)
    timeout_mock.assert_called_with(0.5)

    return dps, modbus, device

