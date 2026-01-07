# File Transfer Usage Guide

This guide provides practical code examples for interacting with the SyncroX File Transfer backend via the `SyncroXFileClient`.

---

## 🚀 Basic Upload Example

The following script demonstrates how to upload a local file to a specific room using the **Reno** algorithm.

```python
from backend.file_transfer.client import SyncroXFileClient
from config import SERVER_HOST, FILE_PORT

def perform_upload(room_code, file_path):
    # Initialize client
    client = SyncroXFileClient(host=SERVER_HOST, port=FILE_PORT, algo="reno")
    
    # Read file data
    with open(file_path, "rb") as f:
        data = f.read()
    
    filename = file_path.split("/")[-1]
    
    print(f"Uploading {filename} to room {room_code}...")
    
    # Perform reliable transfer
    result = client.upload_bytes(room_code, filename, data)
    
    if "OK" in result:
        print("Upload successful!")
    else:
        print(f"Error: {result}")
        
    client.close()

# Usage
perform_upload("1234", "./data/my_file.zip")
```

---

## 📂 Listing Files in a Room

Listing files is handled over the TCP control plane (Port 9010) to ensure a high-consistency view of the available files.

```python
client = SyncroXFileClient()
files = client.list_files("1234")

for name, size, created in files:
    print(f"Name: {name} | Size: {size} bytes | Created: {created}")
```

---

## 📥 Downloading a File

Downloading uses the same Reliable UDP engine as uploading, but in reverse. The receiver (client) sends ACKs to the sender (server).

```python
def perform_download(room_code, filename):
    client = SyncroXFileClient(algo="tahoe")
    
    print(f"Downloading {filename}...")
    data = client.download_bytes(room_code, filename)
    
    if data:
        with open(f"downloads_{filename}", "wb") as f:
            f.write(data)
        print("Download complete!")
    else:
        print("Download failed.")
        
    client.close()
```

---

## 📈 Monitoring Performance

During a transfer, you can access the `metrics` object to inspect living network statistics:

```python
# Metrics are updated in real-time during upload_bytes/download_bytes
# You can check the CSV logs at:
# data/metrics/room_<room_id>_file_metrics.csv
```
