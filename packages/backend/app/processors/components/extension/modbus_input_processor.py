from pymodbus.client import ModbusTcpClient
import json
from ..core.processor_type_name_utils import ProcessorType
from .extension_processor import ContextAwareExtensionProcessor
from ...context.processor_context import ProcessorContext
from ..model import Field, NodeConfig


class ModbusInputProcessor(ContextAwareExtensionProcessor):
    processor_type = ProcessorType.MODBUS_INPUT.value

    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 502)
        self.unit_id = config.get("unit_id", 1)
        self.register_type = config.get("register_type", "holding")
        self.start_address = config.get("start_address", 0)
        self.count = config.get("count", 1)

    def process(self):
        """Read data from Modbus device"""
        try:
            client = ModbusTcpClient(self.host, port=self.port)
            client.connect()
            
            if self.register_type == "holding":
                result = client.read_holding_registers(self.start_address, self.count, slave=self.unit_id)
            elif self.register_type == "input":
                result = client.read_input_registers(self.start_address, self.count, slave=self.unit_id)
            elif self.register_type == "coil":
                result = client.read_coils(self.start_address, self.count, slave=self.unit_id)
            elif self.register_type == "discrete":
                result = client.read_discrete_inputs(self.start_address, self.count, slave=self.unit_id)
            else:
                raise Exception(f"Unsupported register type: {self.register_type}")
            
            client.close()
            
            if result.isError():
                raise Exception(f"Modbus read error: {result}")
            
            data = {
                "host": self.host,
                "port": self.port,
                "unit_id": self.unit_id,
                "register_type": self.register_type,
                "start_address": self.start_address,
                "count": self.count,
                "values": result.registers if hasattr(result, 'registers') else result.bits
            }
            
            return json.dumps(data)
            
        except Exception as e:
            raise Exception(f"Modbus read error: {str(e)}")

    def get_node_config(self):
        host_field = Field(
            name="host",
            label="Host",
            type="input",
            required=True,
            defaultValue="localhost",
            description="Modbus device IP address or hostname"
        )
        
        port_field = Field(
            name="port",
            label="Port",
            type="inputInt",
            required=False,
            defaultValue=502,
            description="Modbus TCP port"
        )
        
        unit_id_field = Field(
            name="unit_id",
            label="Unit ID",
            type="inputInt",
            required=False,
            defaultValue=1,
            description="Modbus unit/slave ID"
        )
        
        register_type_field = Field(
            name="register_type",
            label="Register Type",
            type="select",
            required=True,
            defaultValue="holding",
            options=[
                {"label": "Holding Registers", "value": "holding"},
                {"label": "Input Registers", "value": "input"},
                {"label": "Coils", "value": "coil"},
                {"label": "Discrete Inputs", "value": "discrete"}
            ],
            description="Type of Modbus register to read"
        )
        
        start_address_field = Field(
            name="start_address",
            label="Start Address",
            type="inputInt",
            required=True,
            defaultValue=0,
            description="Starting register address"
        )
        
        count_field = Field(
            name="count",
            label="Count",
            type="inputInt",
            required=True,
            defaultValue=1,
            description="Number of registers to read"
        )

        return NodeConfig(
            processorType=self.processor_type,
            nodeName="Modbus Input",
            icon="AiOutlineDatabase",
            section="input",
            outputType="text",
            defaultHideOutput=False,
            fields=[host_field, port_field, unit_id_field, register_type_field, start_address_field, count_field]
        )

    def cancel(self):
        pass