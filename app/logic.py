import os
import uuid
from pathlib import Path
from typing import Any

from saleae.automation import (
    CaptureConfiguration,
    LogicDeviceConfiguration,
    Manager,
    TimedCaptureMode,
)


class Logic2Adapter:
    """Owns the Logic2 process, captures, and export files."""

    def __init__(self, application_path: str | None = None) -> None:
        self.application_path = application_path or os.getenv(
            "LOGIC2_APPLICATION_PATH"
        )
        self.manager: Manager | None = None
        self.capture_files: dict[str, Path] = {}

    def launch(self) -> None:
        if self.manager is not None:
            return

        if self.application_path is None:
            raise RuntimeError(
                "LOGIC2_APPLICATION_PATH is not configured; "
                "set it to the Logic2 executable path"
            )

        application_path = Path(self.application_path)
        if not application_path.is_file():
            raise RuntimeError(
                f"Logic2 application does not exist: {application_path}"
            )

        self.manager = Manager.launch(application_path=application_path)

    def status(self) -> dict[str, Any]:
        return {
            "connected": self.manager is not None,
            "device": "Logic2" if self.manager is not None else None,
        }

    def run_capture(
        self,
        data_time: float,
        channels: list[int],
        sample_rate_hz: int,
        output_format: str,
    ) -> tuple[str, Path]:
        self.launch()
        if self.manager is None:
            raise RuntimeError("Logic2 manager was not initialized")

        capture_id = str(uuid.uuid4())
        output_directory = Path(os.getenv("SALEAE_CAPTURE_DIR", "/tmp/saleae-captures"))
        output_directory.mkdir(parents=True, exist_ok=True)
        capture_directory = output_directory / capture_id
        capture_directory.mkdir()

        device_configuration = LogicDeviceConfiguration(
            enabled_analog_channels=channels,
            analog_sample_rate=sample_rate_hz,
        )
        capture_configuration = CaptureConfiguration(
            capture_mode=TimedCaptureMode(duration_seconds=data_time)
        )
        capture = self.manager.start_capture(
            device_configuration=device_configuration,
            capture_configuration=capture_configuration,
        )
        capture.wait()

        if output_format == "csv":
            capture.export_raw_data_csv(
                str(capture_directory),
                analog_channels=channels,
                analog_downsample_ratio=1,
            )
            output_path = capture_directory / "analog.csv"
        else:
            capture.export_raw_data_binary(
                str(capture_directory),
                analog_channels=channels,
                analog_downsample_ratio=1,
            )
            output_path = capture_directory / f"{channels[0]}.bin"

        capture.close()
        if not output_path.is_file():
            raise RuntimeError(f"Saleae export was not created: {output_path}")

        self.capture_files[capture_id] = output_path
        return capture_id, output_path

    def download_capture(self, capture_id: str, output_format: str) -> bytes:
        output_path = self.capture_files.get(capture_id)
        if output_path is None:
            raise FileNotFoundError(f"Unknown capture ID: {capture_id}")
        if output_format == "csv" and output_path.suffix != ".csv":
            raise ValueError("The requested capture format is not available")
        return output_path.read_bytes()

    def stop(self) -> None:
        if self.manager is not None:
            self.manager.close()
            self.manager = None
        for capture_path in self.capture_files.values():
            capture_path.unlink(missing_ok=True)
        self.capture_files.clear()
