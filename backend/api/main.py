from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List, Dict
from pathlib import Path
import os
import datetime

app = FastAPI(title="SyncroX API")

# ---------- Paths ----------

# Project root: .../syncroX
BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------- Models / helpers ----------

def file_info(path: Path) -> Dict:
    stat = path.stat()
    return {
        "name": path.name,
        "size": stat.st_size,
        "created": datetime.datetime.fromtimestamp(stat.st_ctime).isoformat(timespec="seconds"),
    }


# ---------- Routes ----------

@app.get("/")
def root():
    return {"message": "SyncroX API is running", "upload_dir": str(UPLOAD_DIR)}


@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a single file. Saved to data/uploads/<original_name>.
    Overwrites if same name exists (simple behaviour, fine for lab).
    """
    dest = UPLOAD_DIR / file.filename
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB chunks
                if not chunk:
                    break
                f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {e}")

    return {"status": "ok", "filename": file.filename}


@app.get("/files/list")
def list_files():
    """Return a list of uploaded files with basic info."""
    files = []
    for path in UPLOAD_DIR.iterdir():
        if path.is_file():
            files.append(file_info(path))
    # sort by created time descending
    files.sort(key=lambda x: x["created"], reverse=True)
    return {"files": files}


@app.get("/files/download/{filename}")
def download_file(filename: str):
    """Download a file by name."""
    path = UPLOAD_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=filename,
    )
