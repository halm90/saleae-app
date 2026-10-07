from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import FileResponse

from app.models import (
    AcquisitionStatus,
    CaptureRequest,
    CaptureResponse,
    Configuration,
    ConfigurationUpdate,
    HardwareStatus,
)
from app.service import ApplicationService


app = FastAPI(
    title="Saleae Application",
    version="0.1.0",
    description="Remote control and status interface for Saleae Logic2 acquisition.",
)
service = ApplicationService()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "saleae-app"}


@app.get("/api/configuration", response_model=Configuration)
def get_configuration() -> Configuration:
    return service.get_configuration()


@app.put("/api/configuration", response_model=Configuration)
def update_configuration(update: ConfigurationUpdate) -> Configuration:
    return service.update_configuration(update)


@app.get("/api/hardware/status", response_model=HardwareStatus)
def get_hardware_status() -> HardwareStatus:
    return service.get_hardware_status()


@app.get("/api/acquisition/status", response_model=AcquisitionStatus)
def get_acquisition_status() -> AcquisitionStatus:
    return service.get_acquisition_status()


@app.post("/api/acquisition/start", response_model=AcquisitionStatus)
def start_acquisition() -> AcquisitionStatus:
    try:
        return service.start_acquisition()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@app.post("/api/acquisition/stop", response_model=AcquisitionStatus)
def stop_acquisition() -> AcquisitionStatus:
    return service.stop_acquisition()


@app.get("/api/logic/status")
def get_logic_status() -> dict[str, object]:
    return service.get_logic_status()


@app.post("/api/logic/start")
def start_logic() -> dict[str, str]:
    return service.start_logic()


@app.post("/api/capture/run", response_model=CaptureResponse)
def run_capture(request: CaptureRequest) -> CaptureResponse:
    try:
        return service.run_capture(request)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@app.get("/api/capture/{capture_id}/download")
def download_capture(capture_id: str, format: str = "csv") -> Response:
    try:
        content = service.download_capture(capture_id, format)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="text/csv" if format == "csv" else "application/octet-stream",
    )


@app.post("/api/logic/stop")
def stop_logic() -> dict[str, str]:
    return service.stop_logic()


static_dir = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/{path:path}", include_in_schema=False)
def static_file(path: str) -> FileResponse:
    requested = static_dir / path
    if requested.is_file() and requested.resolve().is_relative_to(static_dir.resolve()):
        return FileResponse(requested)
    raise HTTPException(status_code=404, detail="Not found")
