from pymodbus.client import ModbusTcpClient
import json
from ..core.processor_type_name_utils import ProcessorType
from .extension_processor import ContextAwareExtensionProcessor
from ...context.processor_context import ProcessorContext
from ..model import Field, NodeConfig


class ModbusOutputProcessor(ContextAwareExtensionProcessor):
    processor_type = ProcessorType.MODBUS_OUTPUT.value

    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 502)
        self.unit_id = config.get("unit_id", 1)
        self.register_type = config.get("register_type", "holding")
        self.start_address = config.get("start_address", 0)
        self.data_input = config.get("data_input", "")

    def process(self):
        """Write data to Modbus device"""
        try:
            # Parse input data
            if isinstance(self.data_input, str):
                try:
                    data = json.loads(self.data_input)
                    if isinstance(data, dict) and 'values' in data:
                        values = data['values']
                    else:
                        values = data if isinstance(data, list) else [data]
                except:
                    # If not JSON, treat as comma-separated values
                    values = [int(float(x.strip())) for x in self.data_input.split(',') if x.strip()]
            else:
                values = self.data_input if isinstance(self.data_input, list) else [self.data_input]
            
            if not values:
                raise Exception("No data provided to write")
            
            client = ModbusTcpClient(self.host, port=self.port)
            client.connect()
            
            if self.register_type == "holding":
                result = client.write_registers(self.start_address, values, slave=self.unit_id)
            elif self.register_type == "coil":
                # Convert to boolean values for coils
                bool_values = [bool(v) for v in values]
                result = client.write_coils(self.start_address, bool_values, slave=self.unit_id)
            else:
                raise Exception(f"Unsupported register type for writing: {self.register_type}")
            
            client.close()
            
            if result.isError():
                raise Exception(f"Modbus write error: {result}")
            
            response = {
                "success": True,
                "host": self.host,
                "port": self.port,
                "unit_id": self.unit_id,
                "register_type": self.register_type,
                "start_address": self.start_address,
                "values_written": values,
                "count": len(values)
            }
            
            return json.dumps(response)
            
        except Exception as e:
            error_response = {
                "success": False,
                "error": str(e)
            }
            return json.dumps(error_response)

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
                {"label": "Coils", "value": "coil"}
            ],
            description="Type of Modbus register to write"
        )
        
        start_address_field = Field(
            name="start_address",
            label="Start Address",
            type="inputInt",
            required=True,
            defaultValue=0,
            description="Starting register address"
        )
        
        data_input_field = Field(
            name="data_input",
            label="Data to Write",
            type="textarea",
            required=True,
            placeholder="Enter data as JSON array or comma-separated values",
            description="Data to write to Modbus device (JSON array or comma-separated numbers)"
        )

        return NodeConfig(
            processorType=self.processor_type,
            nodeName="Modbus Output",
            icon="AiOutlineExport",
            section="tools",
            outputType="text",
            defaultHideOutput=False,
            fields=[host_field, port_field, unit_id_field, register_type_field, start_address_field, data_input_field]
        )

    def cancel(self):
        pass