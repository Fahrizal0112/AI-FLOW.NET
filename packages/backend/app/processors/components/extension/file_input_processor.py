from ..core.processor_type_name_utils import ProcessorType
from .extension_processor import ContextAwareExtensionProcessor
from ...context.processor_context import ProcessorContext
from ..model import Field, NodeConfig


class FileInputProcessor(ContextAwareExtensionProcessor):
    processor_type = ProcessorType.FILE_INPUT.value

    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
        self.file_url = config.get("file_url", "")
        self.file_name = config.get("file_name", "")

    def process(self):
        """Return the file URL that can be used by other processors"""
        return self.file_url

    def get_node_config(self):
        file_url_field = Field(
            name="file_url",
            label="File Upload",
            type="fileUpload",
            required=True,
            placeholder="Upload a file",
            description="Select a file to upload and use in the workflow"
        )
        
        file_name_field = Field(
            name="file_name",
            label="File Name",
            type="input",
            required=False,
            placeholder="File name (optional)",
            description="Optional custom name for the file"
        )

        return NodeConfig(
            processorType=self.processor_type,
            nodeName="File Input",
            icon="AiOutlineFile",
            section="input",
            outputType="fileUrl",
            defaultHideOutput=True,
            fields=[file_url_field, file_name_field]
        )

    def cancel(self):
        pass