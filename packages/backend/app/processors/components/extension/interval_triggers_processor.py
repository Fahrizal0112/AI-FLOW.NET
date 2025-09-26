import time
import threading
from ..core.processor_type_name_utils import ProcessorType
from .extension_processor import ContextAwareExtensionProcessor
from ...context.processor_context import ProcessorContext
from ..model import Field, NodeConfig

class IntervalTriggerProcessor(ContextAwareExtensionProcessor):
    """
    Memicu downstream dengan cara dipanggil berulang (oleh UI/flow lain) atau manual.
    Saran: gunakan ini untuk mengirim "tick" ke node kamera.
    """
    processor_type = "INTERVAL_TRIGGER"

    def __init__(self, config, context: ProcessorContext):
        super().__init__(config, context)
        self.interval_ms = int(config.get("interval_ms", 300))
        # Outputnya string sederhana (timestamp/tick), supaya node lain punya dependency
        # dan editor menjalankan node kamera setelahnya.

    def process(self):
        # Keluarkan "tick" setiap kali dipanggil.
        # (Editor perlu punya mekanisme auto-run/loop. Kalau tidak ada, klik Run berulang
        # atau gunakan fitur 'auto play' bila ada.)
        return [f"tick_{int(time.time()*1000)}"]

    def cancel(self):
        pass

    def get_node_config(self):
        return NodeConfig(
            processorType=self.processor_type,
            nodeName="Interval Trigger",
            icon="AiOutlineClockCircle",
            section="input",
            outputType="string",
            defaultHideOutput=True,
            fields=[
                Field(
                    name="interval_ms", label="Interval (ms)", type="inputInt",
                    required=False, defaultValue=300,
                    description="Interval pemanggilan berikutnya (jika editor mendukung auto-run)."
                )
            ]
        )
