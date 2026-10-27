"""
modbus_service.py — Global Modbus scanning service for VMS 3000
Provides Modbus RTU/TCP functionality that can be used throughout the application.
"""

import sys
from typing import Optional, Tuple, List, Dict, Any
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse
import serial.tools.list_ports
import pymodbus


# Serial config combinations: 8N1, 8E1, 8O1, 7E1, 7O1, etc.
SERIAL_CONFIGS = {
    "8N1": {"bytesize": 8, "parity": "N", "stopbits": 1},
    "8E1": {"bytesize": 8, "parity": "E", "stopbits": 1},
    "8O1": {"bytesize": 8, "parity": "O", "stopbits": 1},
    "7E1": {"bytesize": 7, "parity": "E", "stopbits": 1},
    "7O1": {"bytesize": 7, "parity": "O", "stopbits": 1},
    "8N2": {"bytesize": 8, "parity": "N", "stopbits": 2},
    "8E2": {"bytesize": 8, "parity": "E", "stopbits": 2},
    "8O2": {"bytesize": 8, "parity": "O", "stopbits": 2},
}

# Function codes
FUNCTION_CODES = {
    "01": "Coil Status",
    "02": "Input Status",
    "03": "Holding Register",
    "04": "Input Register",
    "08": "Diagnostics",
}


class ModbusService:
    """Global Modbus service for scanning and communication."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.client: Optional[ModbusTcpClient | ModbusSerialClient] = None
        self.is_connected = False
        self.connection_type = None  # "rtu" or "tcp"
        self.current_function_code = "04"  # Default to Input Register
        self.current_address = 0
        self.current_length = 10
        self.current_unit_id = 1

    def get_serial_ports(self) -> List[str]:
        """Get list of available serial ports."""
        ports = serial.tools.list_ports.comports()
        return [p.device for p in ports]

    def connect_rtu(self, port: str, baud_rate: int, serial_config: str = "8N1",
                    unit_id: int = 1, timeout: float = 2.0) -> Tuple[bool, str]:
        """
        Connect using Modbus RTU (Serial).

        Args:
            port: COM port (e.g., "COM1")
            baud_rate: Baud rate (e.g., 9600)
            serial_config: Serial config string (e.g., "8N1")
            unit_id: Device/Unit ID
            timeout: Connection timeout in seconds

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            config = SERIAL_CONFIGS.get(serial_config, SERIAL_CONFIGS["8N1"])
            self.client = ModbusSerialClient(
                port=port,
                baudrate=baud_rate,
                bytesize=config["bytesize"],
                parity=config["parity"],
                stopbits=config["stopbits"],
                timeout=timeout
            )

            if self.client.connect():
                self.is_connected = True
                self.connection_type = "rtu"
                self.current_unit_id = unit_id
                return True, f"Connected to {port} at {baud_rate} baud ({serial_config})"
            else:
                self.client = None
                return False, "Unable to establish connection"
        except Exception as e:
            self.client = None
            return False, f"Connection error: {str(e)}"

    def connect_tcp(self, host: str, port: int, unit_id: int = 1,
                   timeout: float = 3.0) -> Tuple[bool, str]:
        """
        Connect using Modbus TCP.

        Args:
            host: IP address
            port: TCP port
            unit_id: Device/Unit ID
            timeout: Connection timeout in seconds

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.client = ModbusTcpClient(host=host, port=port, timeout=timeout)

            if self.client.connect():
                self.is_connected = True
                self.connection_type = "tcp"
                self.current_unit_id = unit_id
                return True, f"Connected to {host}:{port}"
            else:
                self.client = None
                return False, "Unable to establish connection"
        except Exception as e:
            self.client = None
            return False, f"Connection error: {str(e)}"

    def disconnect(self) -> None:
        """Disconnect from the device."""
        if self.client:
            self.client.close()
            self.client = None
        self.is_connected = False
        self.connection_type = None

    def read_registers(self, address: int, length: int, function_code: str = "04",
                       unit_id: Optional[int] = None) -> Tuple[bool, Any, str]:
        """
        Read registers using the specified function code.

        Args:
            address: Starting address (0-based or 1-based, will be converted)
            length: Number of registers to read
            function_code: Function code ("01", "02", "03", "04", "08")
            unit_id: Device ID (uses current if not specified)

        Returns:
            Tuple of (success: bool, response_data: Any, message: str)
        """
        if not self.client or not self.is_connected:
            return False, None, "Not connected"

        unit = unit_id if unit_id is not None else self.current_unit_id
        func_idx = int(function_code)

        pymodbus_ver = tuple(map(int, pymodbus.__version__.split('.')[:2]))
        slave_kwarg = {"device_id": unit} if pymodbus_ver >= (3, 11) else {"slave": unit}

        try:
            pymodbus_address = address - 1 if address > 0 else 0

            if func_idx == 1:
                response = self.client.read_coils(address=pymodbus_address, count=length, **slave_kwarg)
            elif func_idx == 2:
                response = self.client.read_discrete_inputs(address=pymodbus_address, count=length, **slave_kwarg)
            elif func_idx == 3:
                response = self.client.read_holding_registers(address=pymodbus_address, count=length, **slave_kwarg)
            elif func_idx == 4:
                response = self.client.read_input_registers(address=pymodbus_address, count=length, **slave_kwarg)
            else:
                return False, None, f"Unsupported function code: {function_code}"

            if response.isError():
                return False, None, f"Modbus error: {response}"

            # Extract data based on function type
            if func_idx in (1, 2):  # Coil/Input Status
                data = response.bits[:length]
            else:  # Holding/Input Registers
                data = response.registers[:length]

            return True, data, "Success"

        except ModbusException as e:
            return False, None, f"Modbus exception: {str(e)}"
        except Exception as e:
            return False, None, f"Error: {str(e)}"

    def set_function_code(self, function_code: str) -> None:
        """Set the default function code for reading."""
        if function_code in FUNCTION_CODES:
            self.current_function_code = function_code

    def get_function_code(self) -> str:
        """Get the current function code."""
        return self.current_function_code

    def get_connection_info(self) -> Dict[str, Any]:
        """Get current connection information."""
        return {
            "is_connected": self.is_connected,
            "connection_type": self.connection_type,
            "unit_id": self.current_unit_id,
            "function_code": self.current_function_code,
        }


# Global instance
modbus_service = ModbusService()
