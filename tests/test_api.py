from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_reports_service_status():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "saleae-app",
    }


def test_configuration_can_be_read_and_updated():
    initial_response = client.get("/api/configuration")
    assert initial_response.status_code == 200
    assert initial_response.json()["sample_rate_hz"] == 1000000

    update_response = client.put(
        "/api/configuration",
        json={"sample_rate_hz": 2000000, "channel_count": 4},
    )

    assert update_response.status_code == 200
    assert update_response.json()["sample_rate_hz"] == 2000000
    assert update_response.json()["channel_count"] == 4


def test_acquisition_lifecycle_is_reported():
    start_response = client.post("/api/acquisition/start")
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"

    stop_response = client.post("/api/acquisition/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "idle"


def test_logic_can_be_ended_from_the_rest_api():
    response = client.post("/api/logic/stop")

    assert response.status_code == 200
    assert response.json() == {
        "status": "stopped",
        "service": "logic2",
    }


def test_unknown_hardware_is_reported_without_crashing():
    response = client.get("/api/hardware/status")

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["reason"] == "hardware adapter is not configured"
