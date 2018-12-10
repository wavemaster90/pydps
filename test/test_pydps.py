from pydps import ParamName, PyDPS
import pytest
import minimalmodbus
import numpy as np


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

        print("DPS: Register %s read." % info[0])
        return info[2]

    def read_registers(self, start_register, num_registers):
        """
        Handle read register queries made from the client

        :param start_register: address of first register
        :param num_registers: number of registers to read
        :return:
        """
        vals = []
        for register in range(start_register, start_register + num_registers):
            info = self._check_valid_register(register)
            vals.append(info[2])
            print("DPS: Register %s read." % info[0])
        return vals

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
        print("DPS: %s into register %s." % (info[2], info[0]))

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
            print("DPS: Register not recognized.")
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
            'read_registers': cls.mock_dps.read_registers,
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


@pytest.mark.parametrize(
    "parameter",
    [
        ParamName.V_SET,
        ParamName.I_SET,
        ParamName.V_OUT,
        ParamName.I_OUT,
        ParamName.P_OUT,
        ParamName.LOCK,
        ParamName.PROTECT,
        ParamName.CV_CC,
        ParamName.ON_OFF,
        ParamName.B_LED,
    ],
)
def test_generic_getters_setters(parameter, mocker):
    dps, modbus, device = initialize_connection(mocker)

    info = dps.get_parameter_info(parameter)

    if info.integer:
        tries = np.arange(info.value_range[0], info.value_range[1] + 1)
    else:
        tries = np.round(np.random.uniform(info.value_range[0], info.value_range[1], 100), 2)

    if info.write:
        for value in tries:
            dps.set_parameter(parameter, value)
            assert dps.get_parameter(parameter) == value
    else:
        for value in tries:
            device.param_registers[parameter.value][2] = value
            assert dps.get_parameter(parameter) == value


def test_generic_v_in_getter(mocker):
    dps, modbus, device = initialize_connection(mocker)

    assert dps.get_parameter(ParamName.V_IN) == 48


def test_generic_model_getter(mocker):
    dps, modbus, device = initialize_connection(mocker)

    assert dps.get_parameter(ParamName.MODEL) == 50.15


def test_generic_version_getter(mocker):
    dps, modbus, device = initialize_connection(mocker)

    assert isinstance(dps.get_parameter(ParamName.VERSION), float)


def test_get_all_parameters(mocker):
    dps, modbus, device = initialize_connection(mocker)

    vals = dps.get_all_parameters()

    params = {
        ParamName.V_SET,
        ParamName.I_SET,
        ParamName.V_OUT,
        ParamName.I_OUT,
        ParamName.P_OUT,
        ParamName.V_IN,
        ParamName.LOCK,
        ParamName.PROTECT,
        ParamName.CV_CC,
        ParamName.ON_OFF,
        ParamName.B_LED,
        ParamName.MODEL,
        ParamName.VERSION,
    }

    assert set(vals.keys()) == params


def test_get_all_measurements(mocker):
    dps, modbus, device = initialize_connection(mocker)

    vals = dps.get_all_measurements()

    params = {
        ParamName.V_OUT,
        ParamName.I_OUT,
        ParamName.P_OUT,
        ParamName.V_IN,
    }

    assert set(vals.keys()) == params


def test_get_all_variables(mocker):
    dps, modbus, device = initialize_connection(mocker)

    vals = dps.get_all_variables()

    params = {
        ParamName.V_SET,
        ParamName.I_SET,
        ParamName.V_OUT,
        ParamName.I_OUT,
        ParamName.P_OUT,
        ParamName.V_IN,
        ParamName.LOCK,
        ParamName.PROTECT,
        ParamName.CV_CC,
        ParamName.ON_OFF,
        ParamName.B_LED,
    }

    assert set(vals.keys()) == params


def test_get_set_values(mocker):
    dps, modbus, device = initialize_connection(mocker)

    vals = dps.get_set_values()

    params = {
        ParamName.V_SET,
        ParamName.I_SET,
    }

    assert set(vals.keys()) == params


def test_get_full_state_info(mocker):
    dps, modbus, device = initialize_connection(mocker)

    vals = dps.get_full_state_info()

    params = {
        ParamName.LOCK,
        ParamName.PROTECT,
        ParamName.CV_CC,
        ParamName.ON_OFF,
    }

    assert set(vals.keys()) == params


def test_get_device_info(mocker):
    dps, modbus, device = initialize_connection(mocker)

    vals = dps.get_device_info()

    params = {
        ParamName.MODEL,
        ParamName.VERSION,
    }

    assert set(vals.keys()) == params

# TODO: Test boiler plate getters and setters
# TODO: Test read invalid register
# TODO: Test write to read-only register
# TODO: Test write values outside of permitted range
# TODO: Test write wrong data tyepe (float instead of int)
