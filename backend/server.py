import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join("/app", "backend", ".env"))
except Exception:
    pass

# Database (MongoDB via Motor)
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# File handling and data
import pandas as pd

# Ensure local imports work even if run as a script (supervisor uvicorn)
import sys
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

# Drivers & Logger (absolute from backend folder)
from drivers.amil import AmilDriver
from drivers.bradesco import BradescoDriver
from drivers.unimed import UnimedDriver
from drivers.seguros_unimed import SegurosUnimedDriver
from drivers.sulamerica import SulamericaDriver
from drivers.base import DriverResult
from utils.logger import JobLogger

# Constants
API_PREFIX = "/api"
BASE_DIR = "/app"
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
EXPORT_DIR = os.path.join(BASE_DIR, "data", "exports")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

app = FastAPI(title="saude-fetch API", version="0.1.0")

# CORS - allow frontend (reads URL from env; fallback to *)
frontend_origin = os.environ.get("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mongo connection
mongo_client: Optional[AsyncIOMotorClient] = None
mongo_db: Optional[AsyncIOMotorDatabase] = None
MONGO_URL = os.environ.get("MONGO_URL")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "saude_fetch")

class JobOut(BaseModel):
    id: str
    filename: str
    type: str
    status: str
    total: int
    success: int
    error: int
    created_at: str
    completed_at: Optional[str] = None

class JobList(BaseModel):
    items: List[JobOut]

async def get_db():
    global mongo_client, mongo_db
    if mongo_db is None:
        if not MONGO_URL:
            raise RuntimeError("MONGO_URL not set in environment. Please configure backend/.env with MONGO_URL.")
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[MONGO_DB_NAME]
        mongo_client = client
        mongo_db = db
    return mongo_db

@app.on_event("shutdown")
async def shutdown_event():
    global mongo_client
    if mongo_client:
        mongo_client.close()

@app.get(f"{API_PREFIX}/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get(f"{API_PREFIX}/jobs", response_model=JobList)
async def list_jobs():
    db = await get_db()
    cursor = db.jobs.find({}, sort=[("created_at", -1)], limit=50)
    items: List[JobOut] = []
    async for doc in cursor:
        items.append(JobOut(
            id=str(doc.get("_id")),
            filename=doc.get("filename", ""),
            type=doc.get("type", "auto"),
            status=doc.get("status", "pending"),
            total=doc.get("total", 0),
            success=doc.get("success", 0),
            error=doc.get("error", 0),
            created_at=doc.get("created_at", ""),
            completed_at=doc.get("completed_at"),
        ))
    return JobList(items=items)

@app.get(f"{API_PREFIX}/jobs/{{job_id}}", response_model=JobOut)
async def get_job(job_id: str):
    db = await get_db()
    doc = await db.jobs.find_one({"_id": job_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(
        id=str(doc.get("_id")),
        filename=doc.get("filename", ""),
        type=doc.get("type", "auto"),
        status=doc.get("status", "pending"),
        total=doc.get("total", 0),
        success=doc.get("success", 0),
        error=doc.get("error", 0),
        created_at=doc.get("created_at", ""),
        completed_at=doc.get("completed_at"),
    )

@app.get(f"{API_PREFIX}/jobs/{{job_id}}/results")
async def get_results(job_id: str, format: str = "csv"):
    db = await get_db()
    doc = await db.jobs.find_one({"_id": job_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    export_path = doc.get("export_path")
    if not export_path or not os.path.exists(export_path):
        raise HTTPException(status_code=404, detail="Results not available yet")
    if format == "csv":
        return FileResponse(export_path, filename=os.path.basename(export_path), media_type="text/csv")
    elif format == "json":
        try:
            df = pd.read_csv(export_path)
            # Handle NaN values and ensure JSON compatibility
            df = df.fillna("")  # Replace NaN with empty strings
            return JSONResponse(df.to_dict(orient="records"))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read results: {e}")
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use csv or json.")

@app.post(f"{API_PREFIX}/jobs", response_model=JobOut)
async def create_job(background_tasks: BackgroundTasks, file: UploadFile = File(...), type: str = Form("auto")):
    # Basic validation for file type
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload CSV or Excel.")

    db = await get_db()
    job_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    # Persist initial job document with deterministic _id (UUID string)
    await db.jobs.insert_one({
        "_id": job_id,
        "filename": filename,
        "type": type,
        "status": "pending",
        "total": 0,
        "success": 0,
        "error": 0,
        "created_at": created_at,
        "completed_at": None,
        "export_path": None,
        "file_path": None,
        "error_message": None,
    })

    # Store upload to disk
    stored_name = f"{job_id}{ext}"
    stored_path = os.path.join(UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as out:
        chunk = await file.read()
        out.write(chunk)

    # Update job with file_path and status
    await db.jobs.update_one({"_id": job_id}, {"$set": {"status": "processing", "file_path": stored_path}})

    # Process in background
    background_tasks.add_task(process_job, job_id, stored_path, type)

    return JobOut(
        id=job_id,
        filename=filename,
        type=type,
        status="processing",
        total=0,
        success=0,
        error=0,
        created_at=created_at,
        completed_at=None,
    )


def clean_identifier(s: str) -> str:
    return "".join(ch for ch in str(s) if ch.isdigit())


def detect_type(identifier: str) -> str:
    if len(identifier) == 11:
        return "cpf"
    if len(identifier) == 14:
        return "cnpj"
    return "unknown"


def to_rows(df: pd.DataFrame, forced_type: str) -> List[str]:
    # Choose first non-empty column
    if df.empty:
        return []
    for col in df.columns.tolist():
        series = df[col].dropna().astype(str)
        if not series.empty:
            return [clean_identifier(x) for x in series.tolist() if str(x).strip()]
    # Fallback: try values
    return []


async def process_job(job_id: str, path: str, forced_type: str = "auto"):
    # Prepare drivers (no external interaction yet; mapping-driven)
    drivers = [UnimedDriver(), AmilDriver(), BradescoDriver(), SegurosUnimedDriver(), SulamericaDriver()]

    db = await get_db()
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(path, dtype=str)
        else:
            df = pd.read_excel(path, dtype=str)

        identifiers = to_rows(df, forced_type)
        total = len(identifiers)
        results = []
        success = 0
        error = 0

        for ident in identifiers:
            itype = detect_type(ident) if forced_type == "auto" else forced_type
            if itype not in ("cpf", "cnpj"):
                error += 1
                results.append({
                    "input": ident,
                    "type": itype,
                    "operator": "",
                    "status": "invalid",
                    "plan": "",
                    "message": "identificador inválido (esperado CPF/CNPJ)",
                    "captured_at": datetime.utcnow().isoformat(),
                })
                continue

            # Run through drivers with throttling and retries (safe placeholders)
            # For esta fase: retornos baseados no mapping (ou pendente)
            item_has_result = False
            for drv in drivers:
                try:
                    dres: DriverResult = await drv.consult(ident, itype)
                    results.append({
                        "input": ident,
                        "type": itype,
                        "operator": drv.name,
                        "status": dres.status,
                        "plan": dres.plan,
                        "message": dres.message,
                        "captured_at": datetime.utcnow().isoformat(),
                    })
                    item_has_result = True
                except Exception as e:
                    results.append({
                        "input": ident,
                        "type": itype,
                        "operator": drv.name,
                        "status": "error",
                        "plan": "",
                        "message": str(e),
                        "captured_at": datetime.utcnow().isoformat(),
                    })
            if item_has_result:
                success += 1
            else:
                error += 1

        export_name = f"{job_id}.csv"
        export_path = os.path.join(EXPORT_DIR, export_name)
        out_df = pd.DataFrame(results)
        out_df.to_csv(export_path, index=False)

        # Export also a JSON copy for convenience
        json_export_path = os.path.join(EXPORT_DIR, f"{job_id}.json")
        out_df.fillna("").to_json(json_export_path, orient="records", force_ascii=False)

        await db.jobs.update_one({"_id": job_id}, {"$set": {
            "status": "completed",
            "total": total,
            "success": success,
            "error": error,
            "completed_at": datetime.utcnow().isoformat(),
            "export_path": export_path,
        }})
    except Exception as e:
        await db.jobs.update_one({"_id": job_id}, {"$set": {
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }})

# Note: Uvicorn server is managed by Supervisor outside this file. Bind should remain 0.0.0.0:8001.
