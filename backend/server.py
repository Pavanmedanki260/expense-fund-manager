import os
import uuid
import asyncio
import httpx
import resend
import logging
from datetime import datetime, timezone, timedelta
from io import BytesIO
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

logger = logging.getLogger(__name__)

app = FastAPI(title="FundTrack API")

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
APP_URL = os.environ.get("APP_URL", "")

resend.api_key = RESEND_API_KEY

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        APP_URL,
        "http://localhost:3000",
        "https://b844d7d4-15d5-4ca4-8fbd-5ff90237ce2f.preview.emergentagent.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ── Models ──────────────────────────────────────────────────────
class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class InviteCreate(BaseModel):
    email: str
    role: str

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

class MemberRoleUpdate(BaseModel):
    role: str


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


async def get_group_member_role(user_id: str, group_id: str):
    """Get user's role in a specific group. Returns None if not a member."""
    member = await db.group_members.find_one(
        {"group_id": group_id, "user_id": user_id}, {"_id": 0}
    )
    return member["role"] if member else None


async def require_group_role(request: Request, group_id: str, allowed_roles: list):
    """Check user has required role in the group. Super admins bypass."""
    user = await get_current_user(request)
    if user.get("is_super_admin"):
        return user, "super_admin"
    role = await get_group_member_role(user["user_id"], group_id)
    if not role:
        raise HTTPException(status_code=403, detail="Not a member of this group")
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions in this group")
    return user, role


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
    else:
        user_count = await db.users.count_documents({})
        is_super = user_count == 0
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "google_uid": data.get("id", ""),
            "name": name,
            "email": email,
            "avatar_url": picture,
            "is_super_admin": is_super,
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        })
    # Auto-accept any pending invitations for this email
    pending_invites = await db.invitations.find(
        {"email": email, "status": "pending"}, {"_id": 0}
    ).to_list(100)
    for inv in pending_invites:
        existing_member = await db.group_members.find_one(
            {"group_id": inv["group_id"], "user_id": user_id}, {"_id": 0}
        )
        if not existing_member:
            await db.group_members.insert_one({
                "group_id": inv["group_id"],
                "user_id": user_id,
                "role": inv["role"],
                "joined_at": datetime.now(timezone.utc).isoformat(),
            })
        await db.invitations.update_one(
            {"invite_id": inv["invite_id"]},
            {"$set": {"status": "accepted", "accepted_by_user_id": user_id}}
        )

    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
        "created_at": datetime.now(timezone.utc)
    })
    response.set_cookie(
        key="session_token", value=session_token,
        httponly=True, secure=True, samesite="none", path="/",
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


# ── Group Endpoints ─────────────────────────────────────────────
@app.post("/api/groups")
async def create_group(body: GroupCreate, user=Depends(get_current_user)):
    group_id = f"grp_{uuid.uuid4().hex[:12]}"
    await db.groups.insert_one({
        "group_id": group_id,
        "name": body.name,
        "description": body.description,
        "created_by_user_id": user["user_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    # Creator becomes group admin
    await db.group_members.insert_one({
        "group_id": group_id,
        "user_id": user["user_id"],
        "role": "admin",
        "joined_at": datetime.now(timezone.utc).isoformat(),
    })
    group = await db.groups.find_one({"group_id": group_id}, {"_id": 0})
    return group


@app.get("/api/groups")
async def list_groups(user=Depends(get_current_user)):
    if user.get("is_super_admin"):
        groups = await db.groups.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    else:
        memberships = await db.group_members.find(
            {"user_id": user["user_id"]}, {"_id": 0}
        ).to_list(500)
        group_ids = [m["group_id"] for m in memberships]
        if not group_ids:
            return []
        groups = await db.groups.find(
            {"group_id": {"$in": group_ids}}, {"_id": 0}
        ).sort("created_at", -1).to_list(500)
    # Enrich with member count and user's role
    for g in groups:
        count = await db.group_members.count_documents({"group_id": g["group_id"]})
        g["member_count"] = count
        if user.get("is_super_admin"):
            g["user_role"] = "super_admin"
        else:
            membership = await db.group_members.find_one(
                {"group_id": g["group_id"], "user_id": user["user_id"]}, {"_id": 0}
            )
            g["user_role"] = membership["role"] if membership else "none"
    return groups


@app.get("/api/groups/{group_id}")
async def get_group(group_id: str, request: Request):
    user = await get_current_user(request)
    group = await db.groups.find_one({"group_id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if not user.get("is_super_admin"):
        role = await get_group_member_role(user["user_id"], group_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        group["user_role"] = role
    else:
        group["user_role"] = "super_admin"
    count = await db.group_members.count_documents({"group_id": group_id})
    group["member_count"] = count
    return group


@app.put("/api/groups/{group_id}")
async def update_group(group_id: str, body: GroupCreate, request: Request):
    user, role = await require_group_role(request, group_id, ["admin"])
    await db.groups.update_one(
        {"group_id": group_id},
        {"$set": {"name": body.name, "description": body.description,
                  "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    updated = await db.groups.find_one({"group_id": group_id}, {"_id": 0})
    return updated


@app.delete("/api/groups/{group_id}")
async def delete_group(group_id: str, request: Request):
    user, role = await require_group_role(request, group_id, ["admin"])
    await db.groups.delete_one({"group_id": group_id})
    await db.group_members.delete_many({"group_id": group_id})
    await db.funds.delete_many({"group_id": group_id})
    await db.utilizations.delete_many({"group_id": group_id})
    await db.invitations.delete_many({"group_id": group_id})
    return {"message": "Group deleted"}


# ── Group Members Endpoints ─────────────────────────────────────
@app.get("/api/groups/{group_id}/members")
async def list_group_members(group_id: str, request: Request):
    user = await get_current_user(request)
    if not user.get("is_super_admin"):
        role = await get_group_member_role(user["user_id"], group_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not a member")
    members = await db.group_members.find({"group_id": group_id}, {"_id": 0}).to_list(500)
    # Enrich with user info
    for m in members:
        u = await db.users.find_one({"user_id": m["user_id"]}, {"_id": 0})
        if u:
            m["name"] = u.get("name", "")
            m["email"] = u.get("email", "")
            m["avatar_url"] = u.get("avatar_url", "")
            m["is_active"] = u.get("is_active", True)
    return members


@app.put("/api/groups/{group_id}/members/{member_user_id}/role")
async def update_member_role(group_id: str, member_user_id: str, body: MemberRoleUpdate, request: Request):
    user, role = await require_group_role(request, group_id, ["admin"])
    if body.role not in ["admin", "contributor", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    existing = await db.group_members.find_one(
        {"group_id": group_id, "user_id": member_user_id}, {"_id": 0}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.group_members.update_one(
        {"group_id": group_id, "user_id": member_user_id},
        {"$set": {"role": body.role}}
    )
    return {"message": "Role updated"}


@app.delete("/api/groups/{group_id}/members/{member_user_id}")
async def remove_member(group_id: str, member_user_id: str, request: Request):
    user, role = await require_group_role(request, group_id, ["admin"])
    await db.group_members.delete_one({"group_id": group_id, "user_id": member_user_id})
    return {"message": "Member removed"}


# ── Invitation Endpoints ────────────────────────────────────────
@app.post("/api/groups/{group_id}/invite")
async def invite_member(group_id: str, body: InviteCreate, request: Request):
    user, role = await require_group_role(request, group_id, ["admin"])
    if body.role not in ["admin", "contributor", "viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    group = await db.groups.find_one({"group_id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    # Check if already a member
    existing_user = await db.users.find_one({"email": body.email}, {"_id": 0})
    if existing_user:
        existing_member = await db.group_members.find_one(
            {"group_id": group_id, "user_id": existing_user["user_id"]}, {"_id": 0}
        )
        if existing_member:
            raise HTTPException(status_code=400, detail="User is already a member of this group")
    # Check existing pending invite
    existing_invite = await db.invitations.find_one(
        {"group_id": group_id, "email": body.email, "status": "pending"}, {"_id": 0}
    )
    if existing_invite:
        raise HTTPException(status_code=400, detail="Invitation already sent to this email")

    invite_id = f"inv_{uuid.uuid4().hex[:12]}"
    await db.invitations.insert_one({
        "invite_id": invite_id,
        "group_id": group_id,
        "email": body.email,
        "role": body.role,
        "invited_by_user_id": user["user_id"],
        "invited_by_name": user["name"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Send invitation email via Resend
    invite_link = f"{APP_URL}/invite/{invite_id}"
    html_content = f"""
    <div style="font-family: 'Segoe UI', Tahoma, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px;">
      <div style="background: #1D9E75; color: white; padding: 16px 24px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="margin: 0; font-size: 22px;">FundTrack</h1>
      </div>
      <div style="background: #ffffff; border: 1px solid #E4E4E7; border-top: none; padding: 32px 24px; border-radius: 0 0 12px 12px;">
        <p style="font-size: 16px; color: #374151; margin-top: 0;">Hi,</p>
        <p style="font-size: 15px; color: #374151;"><strong>{user["name"]}</strong> has invited you to join <strong>{group["name"]}</strong> as a <strong style="color: #1D9E75;">{body.role}</strong>.</p>
        <div style="text-align: center; margin: 28px 0;">
          <a href="{invite_link}" style="background: #1D9E75; color: white; padding: 12px 32px; border-radius: 8px; text-decoration: none; font-size: 15px; font-weight: 600;">Accept Invitation</a>
        </div>
        <p style="font-size: 13px; color: #6B7280;">If the button doesn't work, copy this link:<br/><a href="{invite_link}" style="color: #1D9E75;">{invite_link}</a></p>
      </div>
    </div>
    """
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [body.email],
            "subject": f"You're invited to join {group['name']} on FundTrack",
            "html": html_content,
        }
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Invitation email sent to {body.email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        # Don't fail the invite creation even if email fails

    return {"invite_id": invite_id, "message": f"Invitation sent to {body.email}"}


@app.get("/api/invitations/{invite_id}")
async def get_invitation(invite_id: str):
    inv = await db.invitations.find_one({"invite_id": invite_id}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    group = await db.groups.find_one({"group_id": inv["group_id"]}, {"_id": 0})
    inv["group_name"] = group["name"] if group else "Unknown"
    return inv


@app.post("/api/invitations/{invite_id}/accept")
async def accept_invitation(invite_id: str, request: Request):
    user = await get_current_user(request)
    inv = await db.invitations.find_one({"invite_id": invite_id}, {"_id": 0})
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if inv["status"] != "pending":
        raise HTTPException(status_code=400, detail="Invitation already processed")
    if inv["email"] != user["email"]:
        raise HTTPException(status_code=403, detail="This invitation is for a different email")
    # Add to group
    existing = await db.group_members.find_one(
        {"group_id": inv["group_id"], "user_id": user["user_id"]}, {"_id": 0}
    )
    if not existing:
        await db.group_members.insert_one({
            "group_id": inv["group_id"],
            "user_id": user["user_id"],
            "role": inv["role"],
            "joined_at": datetime.now(timezone.utc).isoformat(),
        })
    await db.invitations.update_one(
        {"invite_id": invite_id},
        {"$set": {"status": "accepted", "accepted_by_user_id": user["user_id"]}}
    )
    return {"message": "Invitation accepted", "group_id": inv["group_id"]}


@app.get("/api/groups/{group_id}/invitations")
async def list_invitations(group_id: str, request: Request):
    user, role = await require_group_role(request, group_id, ["admin"])
    invites = await db.invitations.find(
        {"group_id": group_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return invites


# ── Fund Endpoints (Group-Scoped) ───────────────────────────────
@app.get("/api/groups/{group_id}/funds")
async def list_funds(
    group_id: str, request: Request,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
):
    user = await get_current_user(request)
    if not user.get("is_super_admin"):
        role = await get_group_member_role(user["user_id"], group_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not a member")
    query = {"group_id": group_id}
    if category:
        query["category"] = category
    if date_from:
        query.setdefault("date_received", {})["$gte"] = date_from
    if date_to:
        query.setdefault("date_received", {})["$lte"] = date_to
    if search:
        query["source_name"] = {"$regex": search, "$options": "i"}
    funds = await db.funds.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return funds


@app.post("/api/groups/{group_id}/funds")
async def create_fund(group_id: str, fund: FundCreate, request: Request):
    user, role = await require_group_role(request, group_id, ["admin", "contributor"])
    fund_id = f"fund_{uuid.uuid4().hex[:12]}"
    doc = {
        "fund_id": fund_id,
        "group_id": group_id,
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


@app.put("/api/groups/{group_id}/funds/{fund_id}")
async def update_fund(group_id: str, fund_id: str, fund: FundCreate, request: Request):
    user, role = await require_group_role(request, group_id, ["admin", "contributor"])
    existing = await db.funds.find_one({"fund_id": fund_id, "group_id": group_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Fund not found")
    if role not in ["admin", "super_admin"] and existing["added_by_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.funds.update_one(
        {"fund_id": fund_id},
        {"$set": {
            "source_name": fund.source_name, "amount_inr": fund.amount_inr,
            "category": fund.category, "date_received": fund.date_received,
            "notes": fund.notes, "attachment_url": fund.attachment_url,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    updated = await db.funds.find_one({"fund_id": fund_id}, {"_id": 0})
    return updated


@app.delete("/api/groups/{group_id}/funds/{fund_id}")
async def delete_fund(group_id: str, fund_id: str, request: Request):
    user, role = await require_group_role(request, group_id, ["admin", "contributor"])
    existing = await db.funds.find_one({"fund_id": fund_id, "group_id": group_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Fund not found")
    if role not in ["admin", "super_admin"] and existing["added_by_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.funds.delete_one({"fund_id": fund_id})
    return {"message": "Fund deleted"}


# ── Utilization Endpoints (Group-Scoped) ────────────────────────
@app.get("/api/groups/{group_id}/utilizations")
async def list_utilizations(
    group_id: str, request: Request,
    linked_fund_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    spent_by_user_id: Optional[str] = None,
):
    user = await get_current_user(request)
    if not user.get("is_super_admin"):
        role = await get_group_member_role(user["user_id"], group_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not a member")
    query = {"group_id": group_id}
    if linked_fund_id:
        query["linked_fund_id"] = linked_fund_id
    if date_from:
        query.setdefault("date_spent", {})["$gte"] = date_from
    if date_to:
        query.setdefault("date_spent", {})["$lte"] = date_to
    if spent_by_user_id:
        query["spent_by_user_id"] = spent_by_user_id
    items = await db.utilizations.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@app.post("/api/groups/{group_id}/utilizations")
async def create_utilization(group_id: str, util: UtilizationCreate, request: Request):
    user, role = await require_group_role(request, group_id, ["admin", "contributor"])
    fund = await db.funds.find_one({"fund_id": util.linked_fund_id, "group_id": group_id}, {"_id": 0})
    if not fund:
        raise HTTPException(status_code=400, detail="Linked fund not found in this group")
    util_id = f"util_{uuid.uuid4().hex[:12]}"
    doc = {
        "util_id": util_id,
        "group_id": group_id,
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


@app.put("/api/groups/{group_id}/utilizations/{util_id}")
async def update_utilization(group_id: str, util_id: str, util: UtilizationCreate, request: Request):
    user, role = await require_group_role(request, group_id, ["admin", "contributor"])
    existing = await db.utilizations.find_one({"util_id": util_id, "group_id": group_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Utilization not found")
    if role not in ["admin", "super_admin"] and existing["spent_by_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    fund = await db.funds.find_one({"fund_id": util.linked_fund_id, "group_id": group_id}, {"_id": 0})
    if not fund:
        raise HTTPException(status_code=400, detail="Linked fund not found")
    await db.utilizations.update_one(
        {"util_id": util_id},
        {"$set": {
            "purpose": util.purpose, "amount_inr": util.amount_inr,
            "date_spent": util.date_spent, "linked_fund_id": util.linked_fund_id,
            "linked_fund_name": fund["source_name"],
            "notes": util.notes, "receipt_url": util.receipt_url,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    updated = await db.utilizations.find_one({"util_id": util_id}, {"_id": 0})
    return updated


@app.delete("/api/groups/{group_id}/utilizations/{util_id}")
async def delete_utilization(group_id: str, util_id: str, request: Request):
    user, role = await require_group_role(request, group_id, ["admin", "contributor"])
    existing = await db.utilizations.find_one({"util_id": util_id, "group_id": group_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Utilization not found")
    if role not in ["admin", "super_admin"] and existing["spent_by_user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.utilizations.delete_one({"util_id": util_id})
    return {"message": "Utilization deleted"}


# ── Dashboard Endpoint (Group-Scoped) ───────────────────────────
@app.get("/api/groups/{group_id}/dashboard")
async def get_dashboard(group_id: str, request: Request):
    user = await get_current_user(request)
    if not user.get("is_super_admin"):
        role = await get_group_member_role(user["user_id"], group_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not a member")
    match_f = {"$match": {"group_id": group_id}}
    match_u = {"$match": {"group_id": group_id}}

    total_funds_res = await db.funds.aggregate([match_f, {"$group": {"_id": None, "total": {"$sum": "$amount_inr"}}}]).to_list(1)
    total_utils_res = await db.utilizations.aggregate([match_u, {"$group": {"_id": None, "total": {"$sum": "$amount_inr"}}}]).to_list(1)
    by_category_res = await db.funds.aggregate([match_f, {"$group": {"_id": "$category", "total": {"$sum": "$amount_inr"}}}]).to_list(100)
    monthly_funds_res = await db.funds.aggregate([match_f, {"$group": {"_id": {"$substr": ["$date_received", 0, 7]}, "total": {"$sum": "$amount_inr"}}}, {"$sort": {"_id": 1}}]).to_list(24)
    monthly_utils_res = await db.utilizations.aggregate([match_u, {"$group": {"_id": {"$substr": ["$date_spent", 0, 7]}, "total": {"$sum": "$amount_inr"}}}, {"$sort": {"_id": 1}}]).to_list(24)

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

    recent_funds = await db.funds.find({"group_id": group_id}, {"_id": 0}).sort("created_at", -1).to_list(5)
    recent_utils = await db.utilizations.find({"group_id": group_id}, {"_id": 0}).sort("created_at", -1).to_list(5)
    recent_activity = []
    for f in recent_funds:
        recent_activity.append({"type": "fund", "description": f"Fund added: {f['source_name']}", "amount": f["amount_inr"], "date": f["created_at"], "user": f.get("added_by_name", "")})
    for u in recent_utils:
        recent_activity.append({"type": "utilization", "description": f"Utilized: {u['purpose']}", "amount": u["amount_inr"], "date": u["created_at"], "user": u.get("spent_by_name", "")})
    recent_activity.sort(key=lambda x: x["date"], reverse=True)
    recent_activity = recent_activity[:10]

    return {
        "total_collected": total_collected, "total_utilized": total_utilized,
        "balance": balance, "pct_utilized": pct_utilized,
        "category_breakdown": category_breakdown, "monthly_data": monthly_data,
        "recent_activity": recent_activity,
    }


# ── Export Endpoint (Group-Scoped) ──────────────────────────────
@app.get("/api/groups/{group_id}/export/excel")
async def export_excel(
    group_id: str, request: Request,
    date_from: Optional[str] = None, date_to: Optional[str] = None,
    category: Optional[str] = None, user_id: Optional[str] = None,
):
    user = await get_current_user(request)
    if not user.get("is_super_admin"):
        role = await get_group_member_role(user["user_id"], group_id)
        if not role:
            raise HTTPException(status_code=403, detail="Not a member")
    fund_query = {"group_id": group_id}
    util_query = {"group_id": group_id}
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
    currency_fmt = '\u20b9#,##0.00'

    ws1 = wb.active
    ws1.title = "Funds"
    for col_idx, h in enumerate(["#", "Source", "Amount", "Category", "Date Received", "Added By", "Notes"], 1):
        c = ws1.cell(row=1, column=col_idx, value=h)
        c.font = header_font; c.fill = header_fill; c.alignment = Alignment(horizontal="center")
    total_f = 0
    for i, f in enumerate(funds, 1):
        ws1.cell(row=i+1, column=1, value=i)
        ws1.cell(row=i+1, column=2, value=f.get("source_name", ""))
        ac = ws1.cell(row=i+1, column=3, value=f.get("amount_inr", 0)); ac.number_format = currency_fmt
        total_f += f.get("amount_inr", 0)
        ws1.cell(row=i+1, column=4, value=f.get("category", ""))
        ws1.cell(row=i+1, column=5, value=f.get("date_received", ""))
        ws1.cell(row=i+1, column=6, value=f.get("added_by_name", ""))
        ws1.cell(row=i+1, column=7, value=f.get("notes", ""))
    sr = len(funds) + 2
    ws1.cell(row=sr, column=2, value="TOTAL").font = Font(bold=True)
    tc = ws1.cell(row=sr, column=3, value=total_f); tc.font = Font(bold=True); tc.number_format = currency_fmt
    for col in ws1.columns:
        ws1.column_dimensions[col[0].column_letter].width = min(max(len(str(c.value or "")) for c in col) + 4, 40)

    ws2 = wb.create_sheet("Utilization")
    for col_idx, h in enumerate(["#", "Purpose", "Amount", "Date Spent", "Linked Fund", "Spent By", "Notes"], 1):
        c = ws2.cell(row=1, column=col_idx, value=h)
        c.font = header_font; c.fill = header_fill; c.alignment = Alignment(horizontal="center")
    total_u = 0
    for i, u in enumerate(utils, 1):
        ws2.cell(row=i+1, column=1, value=i)
        ws2.cell(row=i+1, column=2, value=u.get("purpose", ""))
        ac = ws2.cell(row=i+1, column=3, value=u.get("amount_inr", 0)); ac.number_format = currency_fmt
        total_u += u.get("amount_inr", 0)
        ws2.cell(row=i+1, column=4, value=u.get("date_spent", ""))
        ws2.cell(row=i+1, column=5, value=u.get("linked_fund_name", ""))
        ws2.cell(row=i+1, column=6, value=u.get("spent_by_name", ""))
        ws2.cell(row=i+1, column=7, value=u.get("notes", ""))
    sr2 = len(utils) + 2
    ws2.cell(row=sr2, column=2, value="TOTAL").font = Font(bold=True)
    tc2 = ws2.cell(row=sr2, column=3, value=total_u); tc2.font = Font(bold=True); tc2.number_format = currency_fmt
    for col in ws2.columns:
        ws2.column_dimensions[col[0].column_letter].width = min(max(len(str(c.value or "")) for c in col) + 4, 40)

    ws3 = wb.create_sheet("Summary")
    for col_idx, h in enumerate(["Metric", "Value"], 1):
        c = ws3.cell(row=1, column=col_idx, value=h); c.font = header_font; c.fill = header_fill
    bal = total_f - total_u
    pct = round((total_u / total_f * 100), 1) if total_f > 0 else 0
    rows = [("Total Collected", total_f), ("Total Utilized", total_u), ("Balance", bal), ("% Utilized", f"{pct}%")]
    cat_p = [{"$match": fund_query}, {"$group": {"_id": "$category", "total": {"$sum": "$amount_inr"}}}]
    for c in await db.funds.aggregate(cat_p).to_list(100):
        rows.append((f"Category: {c['_id']}", c['total']))
    for i, (m, v) in enumerate(rows, 2):
        ws3.cell(row=i, column=1, value=m)
        cl = ws3.cell(row=i, column=2, value=v)
        if isinstance(v, (int, float)): cl.number_format = currency_fmt
    for col in ws3.columns:
        ws3.column_dimensions[col[0].column_letter].width = min(max(len(str(c.value or "")) for c in col) + 4, 40)

    buf = BytesIO(); wb.save(buf); buf.seek(0)
    group = await db.groups.find_one({"group_id": group_id}, {"_id": 0})
    gname = (group["name"] if group else "report").replace(" ", "_")
    filename = f"fundtrack_{gname}_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


# ── Health Check ────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
