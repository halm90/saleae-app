"""Remote client for the Saleae application REST API.

The larger application can keep using the original SaleaeControl interface while
this class forwards lifecycle and capture operations to the laptop running the
Saleae application.
"""

from __future__ import annotations

import csv
import os
import re
from pathlib import Path
from typing import Any

import httpx


class SaleaeControl:
    """Compatibility wrapper around the Saleae REST API."""

    def __init__(self,
                 remote_url: str | None = None,
                 timeout: float = 30.0,
                 application_path: str | None = None,) -> None:
        self.remote_url = remote_url.rstrip("/") if remote_url else "http://127.0.0.1:8000"
        self.timeout = timeout
        self.app_path = application_path
        self.saleae_manager = None
        self.capture = None
        self._logic_running = False

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.request(method, f"{self.remote_url}{path}", **kwargs)
            response.raise_for_status()
            return response

    def _is_logic_running(self) -> bool:
        try:
            response = self._request("GET", "/api/logic/status")
            self._logic_running = response.json().get("connected", False)
        except (httpx.HTTPError, ValueError):
            self._logic_running = False
        return self._logic_running

    def start_up(self) -> None:
        """Start Logic2 on the remote laptop."""
        if self._is_logic_running():
            return
        response = self._request(
            "POST",
            "/api/logic/start",
            json={"application_path": self.app_path},
        )
        self._logic_running = response.json().get("status") == "started"
        if not self._logic_running:
            raise RuntimeError("Logic2 did not start on the remote host")

    def take_setup_measurement(self, attempt: int) -> bool:
        ref_file_name = self._get_file_path("data") + f"/mrm_reference_ambient_v{attempt}.csv"
        self.gather_data_saleae(5, file_name=ref_file_name)
        return self.check_ref_mrm_data(ref_file_name)

    def check_ref_mrm_data(self, file: str) -> bool:
        channel_0: list[float] = []
        channel_1: list[float] = []
        channel_2: list[float] = []

        with open(file, encoding="utf-8", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            columns = reader.fieldnames or []
            if len(columns) < 4:
                return False

            for row in reader:
                if re.search(r"[a-zA-Z]", row[columns[1]]):
                    continue
                channel_0.append(float(row[columns[1]]))
                channel_1.append(float(row[columns[2]]))
                channel_2.append(float(row[columns[3]]))

        average_channel_0 = sum(channel_0) / len(channel_0) if channel_0 else 0.0
        average_channel_1 = sum(channel_1) / len(channel_1) if channel_1 else 0.0
        average_channel_2 = sum(channel_2) / len(channel_2) if channel_2 else 0.0
        return not ( abs(average_channel_0) < 0.01
                     and abs(average_channel_1) < 0.01
                     and abs(average_channel_2) < 0.01 )

    def gather_data_saleae( self,
                            data_time: float,
                            file_name: str,
                            csv_out: bool = True,
                            channels: list[int] | None = None,
                            sample_rate: int | None = None,
                          ) -> None:
        """Run a timed capture on the remote host and download its CSV."""
        self.start_up()
        payload = {"data_time": data_time,
                   "channels": channels or [0, 1, 2],
                   "sample_rate_hz": sample_rate or 50,
                   "format": "csv" if csv_out else "binary",
                  }
        response = self._request("POST", "/api/capture/run", json=payload)
        capture_id = response.json()["capture_id"]
        download = self._request("GET",
                                 f"/api/capture/{capture_id}/download?format=csv" if csv_out else
                                 f"/api/capture/{capture_id}/download?format=binary",
        )

        output_path = Path(file_name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(download.content)
        self.capture = capture_id

    def stop_capture(self) -> None:
        """Stop the active remote acquisition."""
        if self.capture is not None:
            self._request("POST", "/api/acquisition/stop")
            self.capture = None

    def cleanup(self) -> None:
        """End Logic2 on the remote laptop."""
        if self._logic_running:
            self._request("POST", "/api/logic/stop")
        self._logic_running = False
        self.saleae_manager = None

    @staticmethod
    def _get_file_path(subdirectory: str) -> str:
        return os.path.abspath(subdirectory)
