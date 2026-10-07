# Saleae Application

The Saleae Pro16 channel logic analyzer is connected directly to an Ubuntu laptop.
Logic2 runs on that laptop and recognizes the analyzer through a USB connection.

The application uses the Saleae Logic2 automation library to provide a FastAPI REST
service for remote hosts. The remote host can configure acquisition parameters, start
and stop Logic2, start and stop acquisition, and retrieve captured data without needing
access to the Saleae laptop's graphical interface or its local filesystem layout.

A simple HTML interface presents the current settings and acquisition status.

## Design

### Remote laptop responsibilities

The laptop running this service owns the Logic2 process and the physical analyzer
connection. It is responsible for:

- Launching Logic2 with `Manager.launch()`.
- Creating timed captures through the Logic2 automation API.
- Exporting capture files in the format requested by the remote host.
- Keeping the capture artifact available until the host downloads it.
- Closing Logic2 and the automation manager when requested.

The remote laptop may place generated capture files in a temporary or otherwise
implementation-specific directory. The directory name and location are not part of
the public API contract.

### Host application responsibilities

The host running the larger application owns the local file and user-interface
behavior. It is responsible for:

- Calling the REST API.
- Selecting the local path where downloaded files are saved.
- Parsing CSV or binary files after download.
- Maintaining its own application GUI, configuration model, and file naming rules.
- Deciding how to reference, validate, and compare captured data.

The host does not need to preserve the Saleae laptop's GUI state or its internal
capture directory. The `SaleaeControl` compatibility client receives the data as
bytes and writes it to the path supplied by the host.

### API transport model

The REST API is language-agnostic and uses JSON request bodies. Captures are created
on the remote laptop, then returned to the host through a download endpoint. The
host may use any path, folder, or filename that is appropriate for its own application.

## REST API

| Method | Endpoint | Purpose | Request / response |
| --- | --- | --- | --- |
| `GET` | `/health` | Verify the service is running. | Returns `{"status":"ok","service":"saleae-app"}`. |
| `GET` | `/api/configuration` | Read the current runtime configuration. | Returns `Configuration`. |
| `PUT` | `/api/configuration` | Update the runtime configuration. | Accepts partial `ConfigurationUpdate` values. |
| `GET` | `/api/hardware/status` | Read the analyzer/hardware status. | Returns hardware connection and reason details. |
| `GET` | `/api/acquisition/status` | Read acquisition state. | Returns `idle`, `running`, or `stopped` status and sample count. |
| `POST` | `/api/acquisition/start` | Start the host-side acquisition lifecycle. | Returns `AcquisitionStatus`. |
| `POST` | `/api/acquisition/stop` | Stop the host-side acquisition lifecycle. | Returns the updated `AcquisitionStatus`. |
| `GET` | `/api/logic/status` | Check whether Logic2 is connected on the remote laptop. | Returns `connected` and `device` values. |
| `POST` | `/api/logic/start` | Launch Logic2 on the remote laptop. | Accepts an optional `application_path`; returns `started` or an error. |
| `POST` | `/api/capture/run` | Start a timed capture on the remote laptop. | Accepts `data_time`, `channels`, `sample_rate_hz`, and `format`. Returns a `capture_id`. |
| `GET` | `/api/capture/{capture_id}/download?format=csv` | Download the captured data as CSV to the host. | Returns the file bytes with `text/csv` content type. |
| `GET` | `/api/capture/{capture_id}/download?format=binary` | Download the captured data in Saleae binary format. | Returns the file bytes with `application/octet-stream` content type. |
| `POST` | `/api/logic/stop` | Close Logic2 on the remote laptop. | Returns `stopped` and the service name. |

### Configuration

`GET /api/configuration` returns the current configuration. `PUT /api/configuration`
accepts a partial update containing the following fields:

- `sample_rate_hz`: sample rate in samples per second.
- `channel_count`: number of channels, between 1 and 16.
- `channels`: optional channel identifiers.

### Capture request

`POST /api/capture/run` accepts:

```json
{
  "data_time": 5.0,
  "channels": [0, 1, 2],
  "sample_rate_hz": 50000,
  "format": "csv"
}
```

The response contains a capture identifier:

```json
{
  "capture_id": "capture-1",
  "status": "completed"
}
```

The client then requests the artifact using:

```text
GET /api/capture/capture-1/download?format=csv
```

The response body is written by `SaleaeControl.gather_data_saleae()` to the path
supplied by the host application. The remote laptop's temporary capture directory
is not exposed to the host and does not need to match the host's directory structure.

### Compatibility client

`SaleaeControl` keeps the original method names used by the larger application:

- `start_up()` launches Logic2 on the remote laptop.
- `gather_data_saleae()` runs a remote capture and saves the downloaded file to the
  host's requested path.
- `stop_capture()` stops the remote acquisition lifecycle.
- `cleanup()` closes Logic2 on the remote laptop.
- `check_ref_mrm_data()` validates a file downloaded to the host.

The compatibility client uses HTTPX and does not require the Logic2 package on the
host machine. The host only needs network access to the FastAPI service.

## Running the API

Start the service with the configured Logic2 application path:

```bash
export LOGIC2_APPLICATION_PATH=/path/to/Logic2
export SALEAE_CAPTURE_DIR=/tmp/saleae-captures
uvicorn app.main:app --reload
```

The remote laptop should run this service with the Saleae analyzer connected and the
Logic2 executable available. The host application should configure `remote_url` to the
address of this service and pass the desired local output path to
`gather_data_saleae()`.
