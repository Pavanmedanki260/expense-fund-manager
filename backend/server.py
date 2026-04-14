import os
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, numbers

app = FastAPI(title="FundTrack API")

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ── Models ──────────────────────────────────────────────────────
class FundCreate(BaseModel):
    source_name: str
    amount_inr: float
    category: str
    date_received: str
    notes: Optional[str] = ""
    attachment_url: Optional[str] = ""

class UtilizationCreate(BaseModel):
    purpose: str
    amount_inr: float
    date_spent: str
    linked_fund_id: str
    notes: Optional[str] = ""
    receipt_url: Optional[str] = ""

class RoleUpdate(BaseModel):
    role: str

class UserStatusUpdate(BaseModel):
    is_active: bool


# ── Auth Helpers ────────────────────────────────────────────────
async def get_current_user(request: Request):
    token = None
    session_token_cookie = request.cookies.get("session_token")
    auth_header = request.headers.get("Authorization")
    if session_token_cookie:
        token = session_token_cookie
    elif auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account deactivated")
    return user

def require_role(*roles):
    async def checker(request: Request):
        user = await get_current_user(request)
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


# ── Auth Endpoints ──────────────────────────────────────────────
@app.post("/api/auth/session")
async def exchange_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = resp.json()
    email = data["email"]
    name = data["name"]
    picture = data.get("picture", "")
    session_token = data["session_token"]
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    if existing_user:
        await db.users.update_one(
            {"email": email},
            {"$set": {"name": name, "avatar_url": picture}}
        )
        user_id = existing_user["user_id"]
        role = existing_user["role"]
    else:
        user_count = await db.users.count_documents({})
        role = "admin" if user_count == 0 else "viewer"
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "google_uid": data.get("id", ""),
            "name": name,
            "email": email,
            "avatar_url": picture,
            "role": role,
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        })
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc)
    })
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60,
    )
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user


@app.get("/api/auth/me")
async def get_me(user=Depends(get_current_user)):
    return user


@app.post("/api/auth/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"message": "Logged out"}


# ── Fund Endpoints ──────────────────────────────────────────────
@app.get("/api/funds")
async def list_funds(
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    user=Depends(get_current_user)
):
    query = {}
    if category:
        query["category"] = category
    if date_from:
        query.setdefault("date_received", {})["$gte"] = date_from
    if date_to:
        query.setdefault("date_received", {})["$lte"] = date_to
    if search:
        query["source_name"] = {"$regex": search, "$options": "i"}
    cursor = db.funds.find(query, {"_id": 0}).sort("created_at", -1)
    funds = await cursor.to_list(length=500)
    return funds


@app.post("/api/funds")
async def create_fund(fund: FundCreate, user=Depends(require_role("admin", "contributor"))):
    fund_id = f"fund_{uuid.uuid4().hex[:12]}"
    doc = {
        "fund_id": fund_id,
        "source_name": fund.source_name,
        "amount_inr": fund.amount_inr,
        "category": fund.category,
        "date_received": fund.date_received,
        "notes": fund.notes,
        "attachment_url": fund.attachment_url,
        "added_by_user_id": user["user_id"],
        "added_by_name": user["name"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.funds.insert_one(doc)
    created = await db.funds.find_one({"fund_id": fund_id}, {"_id": 0})
    return created


@app.put("/api/funds/{fund_id}")
async def update_fund(fund_id: str, fund: FundCreate, user=Depends(require_role("admin", "contributor"))):
    existing = await db.funds.find_one({"fund_id": fund_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Fund not found")
    if user["role"] != "admin" and existing["added_by_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.funds.update_one(
        {"fund_id": fund_id},
        {"$set": {
            "source_name": fund.source_name,
            "amount_inr": fund.amount_inr,
            "category": fund.category,
            "date_received": fund.date_received,
            "notes": fund.notes,
            "attachment_url": fund.attachment_url,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    updated = await db.funds.find_one({"fund_id": fund_id}, {"_id": 0})
    return updated


@app.delete("/api/funds/{fund_id}")
async def delete_fund(fund_id: str, user=Depends(require_role("admin", "contributor"))):
    existing = await db.funds.find_one({"fund_id": fund_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Fund not found")
    if user["role"] != "admin" and existing["added_by_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.funds.delete_one({"fund_id": fund_id})
    return {"message": "Fund deleted"}


# ── Utilization Endpoints ───────────────────────────────────────
@app.get("/api/utilizations")
async def list_utilizations(
    linked_fund_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    spent_by_user_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    query = {}
    if linked_fund_id:
        query["linked_fund_id"] = linked_fund_id
    if date_from:
        query.setdefault("date_spent", {})["$gte"] = date_from
    if date_to:
        query.setdefault("date_spent", {})["$lte"] = date_to
    if spent_by_user_id:
        query["spent_by_user_id"] = spent_by_user_id
    cursor = db.utilizations.find(query, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(length=500)
    return items


@app.post("/api/utilizations")
async def create_utilization(util: UtilizationCreate, user=Depends(require_role("admin", "contributor"))):
    fund = await db.funds.find_one({"fund_id": util.linked_fund_id}, {"_id": 0})
    if not fund:
        raise HTTPException(status_code=400, detail="Linked fund not found")
    util_id = f"util_{uuid.uuid4().hex[:12]}"
    doc = {
        "util_id": util_id,
        "purpose": util.purpose,
        "amount_inr": util.amount_inr,
        "date_spent": util.date_spent,
        "linked_fund_id": util.linked_fund_id,
        "linked_fund_name": fund["source_name"],
        "spent_by_user_id": user["user_id"],
        "spent_by_name": user["name"],
        "notes": util.notes,
        "receipt_url": util.receipt_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.utilizations.insert_one(doc)
    created = await db.utilizations.find_one({"util_id": util_id}, {"_id": 0})
    return created


@app.put("/api/utilizations/{util_id}")
async def update_utilization(util_id: str, util: UtilizationCreate, user=Depends(require_role("admin", "contributor"))):
    existing = await db.utilizations.find_one({"util_id": util_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Utilization not found")
    if user["role"] != "admin" and existing["spent_by_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    fund = await db.funds.find_one({"fund_id": util.linked_fund_id}, {"_id": 0})
    if not fund:
        raise HTTPException(status_code=400, detail="Linked fund not found")
    await db.utilizations.update_one(
        {"util_id": util_id},
        {"$set": {
            "purpose": util.purpose,
            "amount_inr": util.amount_inr,
            "date_spent": util.date_spent,
            "linked_fund_id": util.linked_fund_id,
            "linked_fund_name": fund["source_name"],
            "notes": util.notes,
            "receipt_url": util.receipt_url,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    updated = await db.utilizations.find_one({"util_id": util_id}, {"_id": 0})
    return updated


@app.delete("/api/utilizations/{util_id}")
async def delete_utilization(util_id: str, user=Depends(require_role("admin", "contributor"))):
    existing = await db.utilizations.find_one({"util_id": util_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Utilization not found")
    if user["role"] != "admin" and existing["spent_by_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.utilizations.delete_one({"util_id": util_id})
    return {"message": "Utilization deleted"}


# ── Dashboard Endpoint ──────────────────────────────────────────
@app.get("/api/dashboard")
async def get_dashboard(user=Depends(get_current_user)):
    pipeline_total_funds = [{"$group": {"_id": None, "total": {"$sum": "$amount_inr"}}}]
    pipeline_total_utils = [{"$group": {"_id": None, "total": {"$sum": "$amount_inr"}}}]
    pipeline_by_category = [{"$group": {"_id": "$category", "total": {"$sum": "$amount_inr"}}}]
    pipeline_monthly_funds = [
        {"$group": {"_id": {"$substr": ["$date_received", 0, 7]}, "total": {"$sum": "$amount_inr"}}},
        {"$sort": {"_id": 1}}
    ]
    pipeline_monthly_utils = [
        {"$group": {"_id": {"$substr": ["$date_spent", 0, 7]}, "total": {"$sum": "$amount_inr"}}},
        {"$sort": {"_id": 1}}
    ]

    total_funds_res = await db.funds.aggregate(pipeline_total_funds).to_list(1)
    total_utils_res = await db.utilizations.aggregate(pipeline_total_utils).to_list(1)
    by_category_res = await db.funds.aggregate(pipeline_by_category).to_list(100)
    monthly_funds_res = await db.funds.aggregate(pipeline_monthly_funds).to_list(24)
    monthly_utils_res = await db.utilizations.aggregate(pipeline_monthly_utils).to_list(24)

    total_collected = total_funds_res[0]["total"] if total_funds_res else 0
    total_utilized = total_utils_res[0]["total"] if total_utils_res else 0
    balance = total_collected - total_utilized
    pct_utilized = round((total_utilized / total_collected * 100), 1) if total_collected > 0 else 0

    category_breakdown = [{"category": c["_id"], "amount": c["total"]} for c in by_category_res]

    months_set = set()
    fund_by_month = {}
    util_by_month = {}
    for m in monthly_funds_res:
        months_set.add(m["_id"])
        fund_by_month[m["_id"]] = m["total"]
    for m in monthly_utils_res:
        months_set.add(m["_id"])
        util_by_month[m["_id"]] = m["total"]
    monthly_data = sorted([
        {"month": m, "collected": fund_by_month.get(m, 0), "utilized": util_by_month.get(m, 0)}
        for m in months_set
    ], key=lambda x: x["month"])

    recent_funds = await db.funds.find({}, {"_id": 0}).sort("created_at", -1).to_list(5)
    recent_utils = await db.utilizations.find({}, {"_id": 0}).sort("created_at", -1).to_list(5)
    recent_activity = []
    for f in recent_funds:
        recent_activity.append({"type": "fund", "description": f"Fund added: {f['source_name']}", "amount": f["amount_inr"], "date": f["created_at"], "user": f.get("added_by_name", "")})
    for u in recent_utils:
        recent_activity.append({"type": "utilization", "description": f"Utilized: {u['purpose']}", "amount": u["amount_inr"], "date": u["created_at"], "user": u.get("spent_by_name", "")})
    recent_activity.sort(key=lambda x: x["date"], reverse=True)
    recent_activity = recent_activity[:10]

    return {
        "total_collected": total_collected,
        "total_utilized": total_utilized,
        "balance": balance,
        "pct_utilized": pct_utilized,
        "category_breakdown": category_breakdown,
        "monthly_data": monthly_data,
        "recent_activity": recent_activity,
    }


# ── User Management Endpoints ──────────────────────────────────
@app.get("/api/users")
async def list_users(user=Depends(require_role("admin"))):
    cursor = db.users.find({}, {"_id": 0}).sort("created_at", -1)
    users = await cursor.to_list(length=200)
    return users


@app.put("/api/users/{user_id}/role")
async def update_user_role(user_id: str, body: RoleUpdate, user=Depends(require_role("admin"))):
    if body.role not in ["admin", "contributor", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    existing = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"user_id": user_id}, {"$set": {"role": body.role}})
    updated = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return updated


@app.put("/api/users/{user_id}/status")
async def update_user_status(user_id: str, body: UserStatusUpdate, user=Depends(require_role("admin"))):
    existing = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"user_id": user_id}, {"$set": {"is_active": body.is_active}})
    updated = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return updated


# ── Export Endpoint ─────────────────────────────────────────────
@app.get("/api/export/excel")
async def export_excel(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    category: Optional[str] = None,
    user_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    fund_query = {}
    util_query = {}
    if category:
        fund_query["category"] = category
    if date_from:
        fund_query.setdefault("date_received", {})["$gte"] = date_from
        util_query.setdefault("date_spent", {})["$gte"] = date_from
    if date_to:
        fund_query.setdefault("date_received", {})["$lte"] = date_to
        util_query.setdefault("date_spent", {})["$lte"] = date_to
    if user_id:
        fund_query["added_by_user_id"] = user_id
        util_query["spent_by_user_id"] = user_id

    funds = await db.funds.find(fund_query, {"_id": 0}).sort("date_received", -1).to_list(5000)
    utils = await db.utilizations.find(util_query, {"_id": 0}).sort("date_spent", -1).to_list(5000)

    wb = Workbook()
    header_font = Font(bold=True, color="000000")
    header_fill = PatternFill(start_color="B4D7E8", end_color="B4D7E8", fill_type="solid")
    currency_format = '₹#,##0.00'

    ws1 = wb.active
    ws1.title = "Funds"
    fund_headers = ["#", "Source", "Amount (₹)", "Category", "Date Received", "Added By", "Notes"]
    for col_idx, h in enumerate(fund_headers, 1):
        cell = ws1.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    total_fund_amount = 0
    for i, f in enumerate(funds, 1):
        ws1.cell(row=i+1, column=1, value=i)
        ws1.cell(row=i+1, column=2, value=f.get("source_name", ""))
        amt_cell = ws1.cell(row=i+1, column=3, value=f.get("amount_inr", 0))
        amt_cell.number_format = currency_format
        total_fund_amount += f.get("amount_inr", 0)
        ws1.cell(row=i+1, column=4, value=f.get("category", ""))
        ws1.cell(row=i+1, column=5, value=f.get("date_received", ""))
        ws1.cell(row=i+1, column=6, value=f.get("added_by_name", ""))
        ws1.cell(row=i+1, column=7, value=f.get("notes", ""))
    summary_row = len(funds) + 2
    ws1.cell(row=summary_row, column=2, value="TOTAL").font = Font(bold=True)
    total_cell = ws1.cell(row=summary_row, column=3, value=total_fund_amount)
    total_cell.font = Font(bold=True)
    total_cell.number_format = currency_format
    for col in ws1.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws1.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    ws2 = wb.create_sheet("Utilization")
    util_headers = ["#", "Purpose", "Amount (₹)", "Date Spent", "Linked Fund", "Spent By", "Notes"]
    for col_idx, h in enumerate(util_headers, 1):
        cell = ws2.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    total_util_amount = 0
    for i, u in enumerate(utils, 1):
        ws2.cell(row=i+1, column=1, value=i)
        ws2.cell(row=i+1, column=2, value=u.get("purpose", ""))
        amt_cell = ws2.cell(row=i+1, column=3, value=u.get("amount_inr", 0))
        amt_cell.number_format = currency_format
        total_util_amount += u.get("amount_inr", 0)
        ws2.cell(row=i+1, column=4, value=u.get("date_spent", ""))
        ws2.cell(row=i+1, column=5, value=u.get("linked_fund_name", ""))
        ws2.cell(row=i+1, column=6, value=u.get("spent_by_name", ""))
        ws2.cell(row=i+1, column=7, value=u.get("notes", ""))
    summary_row2 = len(utils) + 2
    ws2.cell(row=summary_row2, column=2, value="TOTAL").font = Font(bold=True)
    total_cell2 = ws2.cell(row=summary_row2, column=3, value=total_util_amount)
    total_cell2.font = Font(bold=True)
    total_cell2.number_format = currency_format
    for col in ws2.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws2.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    ws3 = wb.create_sheet("Summary")
    summary_headers = ["Metric", "Value"]
    for col_idx, h in enumerate(summary_headers, 1):
        cell = ws3.cell(row=1, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
    balance = total_fund_amount - total_util_amount
    pct = round((total_util_amount / total_fund_amount * 100), 1) if total_fund_amount > 0 else 0
    summary_data = [
        ("Total Collected", total_fund_amount),
        ("Total Utilized", total_util_amount),
        ("Balance", balance),
        ("% Utilized", f"{pct}%"),
    ]
    cat_pipeline = [{"$match": fund_query}, {"$group": {"_id": "$category", "total": {"$sum": "$amount_inr"}}}]
    cat_breakdown = await db.funds.aggregate(cat_pipeline).to_list(100)
    for c in cat_breakdown:
        summary_data.append((f"Category: {c['_id']}", c['total']))
    for i, (metric, value) in enumerate(summary_data, 2):
        ws3.cell(row=i, column=1, value=metric)
        cell = ws3.cell(row=i, column=2, value=value)
        if isinstance(value, (int, float)):
            cell.number_format = currency_format
    for col in ws3.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws3.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"fundtrack_report_{today}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ── Health Check ────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
