from typing import Protocol

from app.logic import Logic2Adapter
from app.models import (
    AcquisitionStatus,
    CaptureRequest,
    CaptureResponse,
    Configuration,
    ConfigurationUpdate,
    HardwareStatus,
)


class HardwareAdapter(Protocol):
    """Boundary for a later Saleae Logic2 integration."""

    def status(self) -> HardwareStatus: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...


class UnconfiguredHardwareAdapter:
    """Safe fallback used until a Logic2 adapter is configured."""

    def status(self) -> HardwareStatus:
        return HardwareStatus(
            connected=False,
            reason="hardware adapter is not configured",
        )

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None


class ApplicationService:
    def __init__(
        self,
        hardware_adapter: HardwareAdapter | None = None,
        logic_adapter: Logic2Adapter | None = None,
    ) -> None:
        self.hardware_adapter = hardware_adapter or UnconfiguredHardwareAdapter()
        self.logic_adapter = logic_adapter or Logic2Adapter()
        self.configuration = Configuration()
        self.acquisition = AcquisitionStatus(status="idle")

    def get_configuration(self) -> Configuration:
        return self.configuration

    def update_configuration(self, update: ConfigurationUpdate) -> Configuration:
        values = update.model_dump(exclude_none=True)
        self.configuration = self.configuration.model_copy(update=values)
        return self.configuration

    def get_hardware_status(self) -> HardwareStatus:
        return self.hardware_adapter.status()

    def get_acquisition_status(self) -> AcquisitionStatus:
        return self.acquisition

    def start_acquisition(self) -> AcquisitionStatus:
        self.hardware_adapter.start()
        self.acquisition = AcquisitionStatus(status="running", sample_count=0)
        return self.acquisition

    def stop_acquisition(self) -> AcquisitionStatus:
        self.hardware_adapter.stop()
        self.acquisition = AcquisitionStatus(status="idle", sample_count=0)
        return self.acquisition

    def start_logic(self) -> dict[str, str]:
        self.logic_adapter.launch()
        return {"status": "started", "service": "logic2"}

    def get_logic_status(self) -> dict[str, object]:
        return self.logic_adapter.status()

    def run_capture(self, request: CaptureRequest) -> CaptureResponse:
        capture_id, _ = self.logic_adapter.run_capture(
            data_time=request.data_time,
            channels=request.channels,
            sample_rate_hz=request.sample_rate_hz,
            output_format=request.format,
        )
        return CaptureResponse(capture_id=capture_id, status="completed")

    def download_capture(self, capture_id: str, output_format: str) -> bytes:
        return self.logic_adapter.download_capture(capture_id, output_format)

    def stop_logic(self) -> dict[str, str]:
        self.logic_adapter.stop()
        return {"status": "stopped", "service": "logic2"}
