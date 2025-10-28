import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment

from drivers.driver_manager import manager as driver_manager
from drivers.base import DriverResult
from utils.logger import JobLogger
from utils.auth import create_access_token, verify_token, check_credentials, AuthError


# --- APP PRINCIPAL ---
app = FastAPI(title="saude-fetch API", version="0.2.0")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- NOVO ENDPOINT: recarregar mappings ---
@app.post("/api/mappings/reload")
def reload_mappings():
    try:
        driver_manager.reload()
        return {"detail": "Mappings recarregados com sucesso"}
    except Exception as e:
        return {"detail": f"Erro ao recarregar mappings: {e}"}


# --- Diretórios ---
BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
EXPORT_DIR = os.path.join(BASE_DIR, "data", "exports")
LOGS_DIR = os.path.join(BASE_DIR, "data", "logs")
LAST_RUN_LOG = os.path.join(LOGS_DIR, "last_run.log")

for d in [UPLOAD_DIR, EXPORT_DIR, LOGS_DIR]:
    os.makedirs(d, exist_ok=True)

# --- Mongo ---
mongo_client: Optional[AsyncIOMotorClient] = None
mongo_db: Optional[AsyncIOMotorDatabase] = None
MONGO_URL = os.environ.get("MONGO_URL")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "saude_fetch")


# --- MODELOS ---
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
    processed: Optional[int] = 0


class JobList(BaseModel):
    items: List[JobOut]


async def get_db():
    global mongo_client, mongo_db
    if mongo_db is None:
        if not MONGO_URL:
            raise RuntimeError("MONGO_URL not set in environment.")
        client = AsyncIOMotorClient(MONGO_URL)
        await client.admin.command("ping")
        mongo_client = client
        mongo_db = client[MONGO_DB_NAME]
    return mongo_db


@app.on_event("shutdown")
async def shutdown_event():
    global mongo_client
    if mongo_client:
        mongo_client.close()


# --- AUTH ---
class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    expires_in_hours: int


async def require_auth(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = authorization.split(" ", 1)[1]
    try:
        user = verify_token(token)
        return user
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/login", response_model=LoginOut)
async def login(data: LoginIn):
    if not check_credentials(data.username, data.password):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = create_access_token(data.username, 24)
    return LoginOut(token=token, expires_in_hours=24)


# --- HEALTH ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/ping")
async def ping():
    return {"status": "ok"}


# --- JOBS ---
@app.get("/api/jobs", response_model=JobList)
async def list_jobs(user: str = Depends(require_auth)):
    db = await get_db()
    cursor = db.jobs.find({}, sort=[("created_at", -1)], limit=50)
    items = []
    async for doc in cursor:
        items.append(JobOut(
            id=str(doc.get("_id")),
            filename=doc.get("filename", ""),
            type=str(doc.get("type", "auto")),
            status=doc.get("status", "pending"),
            total=int(doc.get("total", 0)),
            success=int(doc.get("success", 0)),
            error=int(doc.get("error", 0)),
            created_at=str(doc.get("created_at", "")),
            completed_at=str(doc.get("completed_at", "")) if doc.get("completed_at") else None,
            processed=int(doc.get("processed", 0)),
        ))
    return JobList(items=items)


@app.get("/api/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str, user: str = Depends(require_auth)):
    db = await get_db()
    doc = await db.jobs.find_one({"_id": job_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut(
        id=str(doc.get("_id")),
        filename=doc.get("filename", ""),
        type=str(doc.get("type", "auto")),
        status=doc.get("status", "pending"),
        total=int(doc.get("total", 0)),
        success=int(doc.get("success", 0)),
        error=int(doc.get("error", 0)),
        created_at=str(doc.get("created_at", "")),
        completed_at=str(doc.get("completed_at", "")) if doc.get("completed_at") else None,
        processed=int(doc.get("processed", 0)),
    )


@app.post("/api/jobs", response_model=JobOut)
async def create_job(background_tasks: BackgroundTasks, file: UploadFile = File(...), user: str = Depends(require_auth)):
    try:
        filename = file.filename or "upload"
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".csv", ".xlsx", ".xls"]:
            raise HTTPException(status_code=400, detail="Unsupported file type. Upload CSV or Excel.")

        db = await get_db()
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        doc = {
            "_id": job_id,
            "filename": filename,
            "type": "cpf",
            "status": "pending",
            "total": 0,
            "success": 0,
            "error": 0,
            "processed": 0,
            "created_at": created_at,
            "completed_at": None,
            "export_path": None,
            "xlsx_path": None,
            "file_path": None,
            "error_message": None,
        }
        await db.jobs.insert_one(doc)

        stored_name = f"{job_id}{ext}"
        stored_path = os.path.join(UPLOAD_DIR, stored_name)
        with open(stored_path, "wb") as out:
            chunk = await file.read()
            out.write(chunk)

        await db.jobs.update_one({"_id": job_id}, {"$set": {"status": "processing", "file_path": stored_path}})

        background_tasks.add_task(process_job, job_id, stored_path, "cpf")

        return JobOut(
            id=job_id,
            filename=filename,
            type="cpf",
            status="processing",
            total=0,
            success=0,
            error=0,
            created_at=created_at,
            completed_at=None,
            processed=0,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# --- HELPERS ---
def clean_identifier(s: str) -> str:
    return "".join(ch for ch in str(s) if ch.isdigit())


def format_cpf(cpf_digits: str) -> str:
    if len(cpf_digits) != 11:
        return cpf_digits
    return f"{cpf_digits[0:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:11]}"


def detect_type(identifier: str) -> str:
    if len(identifier) == 11:
        return "cpf"
    if len(identifier) == 14:
        return "cnpj"
    return "unknown"


def to_rows(df: pd.DataFrame, forced_type: str) -> List[str]:
    if df.empty:
        return []
    for col in df.columns.tolist():
        series = df[col].dropna().astype(str)
        if not series.empty:
            return [clean_identifier(x) for x in series.tolist() if str(x).strip()]
    return []


async def process_job(job_id: str, path: str, forced_type: str = "auto"):
    db = await get_db()
    logger = JobLogger(job_id, LOGS_DIR)
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".csv":
            df = pd.read_csv(path, dtype=str)
        else:
            df = pd.read_excel(path, dtype=str)

        identifiers = to_rows(df, forced_type)
        total = len(identifiers)
        results, success, error, processed = [], 0, 0, 0
        drivers = driver_manager.drivers

        for ident in identifiers:
            itype = detect_type(ident) if forced_type == "auto" else forced_type
            if itype not in ("cpf", "cnpj"):
                error += 1
                processed += 1
                results.append({
                    "input": ident,
                    "type": itype,
                    "operator": "",
                    "status": "invalid",
                    "plan": "",
                    "message": "identificador inválido",
                    "captured_at": datetime.utcnow().isoformat(),
                })
                await db.jobs.update_one({"_id": job_id}, {"$set": {"processed": processed, "total": total}})
                continue

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
            processed += 1
            await db.jobs.update_one({"_id": job_id}, {"$set": {"processed": processed, "total": total}})

        out_df = pd.DataFrame(results)
        xlsx_path = os.path.join(EXPORT_DIR, f"{job_id}.xlsx")
        build_xlsx_from_results(out_df, xlsx_path)

        write_last_run_log(job_id, total, success, error, None, xlsx_path)

        await db.jobs.update_one({"_id": job_id}, {"$set": {
            "status": "completed",
            "total": total,
            "success": success,
            "error": error,
            "processed": processed,
            "completed_at": datetime.utcnow().isoformat(),
            "xlsx_path": xlsx_path,
        }})
    except Exception as e:
        write_last_run_log(job_id, 0, 0, 0, None, None, error_message=str(e))
        await db.jobs.update_one({"_id": job_id}, {"$set": {
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        }})


def build_xlsx_from_results(df: pd.DataFrame, out_path: str):
    header = ["CPF", "amil", "bradesco", "unimed", "unimed seguros"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Consulta CPF"
    ws.append(header)
    by_cpf = {}
    for _, row in df.iterrows():
        if row.get("type") != "cpf":
            continue
        cpf_digits = str(row.get("input", ""))
        cpf_fmt = format_cpf(cpf_digits)
        op = str(row.get("operator", "")).lower()
        plan = str(row.get("plan", ""))
        status = str(row.get("status", ""))
        val = plan if plan else status
        if not cpf_fmt:
            continue
        if cpf_fmt not in by_cpf:
            by_cpf[cpf_fmt] = {}
        by_cpf[cpf_fmt][op] = val
    for cpf_fmt, ops in by_cpf.items():
        row = [cpf_fmt, ops.get("amil", ""), ops.get("bradesco", ""), ops.get("unimed", ""), ops.get("seguros_unimed", "")]
        ws.append(row)
    for cell in ws["A"]:
        cell.number_format = "@"
        cell.alignment = Alignment(horizontal="left")
    wb.save(out_path)


def write_last_run_log(job_id, total, success, error, csv_path, xlsx_path, error_message=None):
    lines = [
        f"job_id: {job_id}",
        f"total: {total}",
        f"success: {success}",
        f"error: {error}",
    ]
    if csv_path:
        lines.append(f"csv: {csv_path}")
    if xlsx_path:
        lines.append(f"xlsx: {xlsx_path}")
    if error_message:
        lines.append(f"error_message: {error_message}")
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(LAST_RUN_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
