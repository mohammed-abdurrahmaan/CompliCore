"""
ADP Integration Routes
Handles OAuth flow, connection management, and payroll data sync.
"""
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from services.adp_service import (
    is_adp_configured,
    build_auth_url,
    exchange_code_for_token,
    refresh_adp_token,
    fetch_workers,
    transform_adp_worker,
)

logger = logging.getLogger(__name__)


class ADPCallbackRequest(BaseModel):
    code: str
    employer_id: str


class ADPDisconnectRequest(BaseModel):
    employer_id: str


def register_adp_routes(api_router: APIRouter, db, get_current_user):
    @api_router.get("/adp/status/{employer_id}")
    async def adp_connection_status(employer_id: str, user=Depends(get_current_user)):
        configured = is_adp_configured()
        conn = await db.adp_connections.find_one(
            {"employer_id": employer_id}, {"_id": 0}
        )
        connected = bool(conn and conn.get("access_token"))
        return {
            "configured": configured,
            "connected": connected,
            "last_sync": conn.get("last_sync") if conn else None,
            "worker_count": conn.get("worker_count", 0) if conn else 0,
            "environment": conn.get("environment", "sandbox") if conn else "sandbox",
        }

    @api_router.get("/adp/auth-url/{employer_id}")
    async def get_adp_auth_url(employer_id: str, user=Depends(get_current_user)):
        if not is_adp_configured():
            raise HTTPException(status_code=400, detail="ADP credentials not configured. Add ADP_CLIENT_ID and ADP_CLIENT_SECRET to your environment.")
        url = build_auth_url(state=employer_id)
        return {"auth_url": url}

    @api_router.post("/adp/callback")
    async def adp_oauth_callback(req: ADPCallbackRequest, user=Depends(get_current_user)):
        if not is_adp_configured():
            raise HTTPException(status_code=400, detail="ADP not configured")
        try:
            token_data = await exchange_code_for_token(req.code)
            await db.adp_connections.update_one(
                {"employer_id": req.employer_id},
                {"$set": {
                    "employer_id": req.employer_id,
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in", 3600),
                    "obtained_at": token_data.get("obtained_at"),
                    "connected_at": datetime.now(timezone.utc).isoformat(),
                    "connected_by": user.get("id"),
                }},
                upsert=True,
            )
            return {"success": True, "message": "ADP connected successfully"}
        except Exception as e:
            logger.error(f"ADP OAuth callback failed: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to connect ADP: {str(e)}")

    @api_router.post("/adp/sync/{employer_id}")
    async def sync_adp_payroll(employer_id: str, user=Depends(get_current_user)):
        conn = await db.adp_connections.find_one({"employer_id": employer_id}, {"_id": 0})
        if not conn or not conn.get("access_token"):
            raise HTTPException(status_code=400, detail="ADP not connected for this employer")

        access_token = conn["access_token"]

        try:
            adp_workers = await fetch_workers(access_token)
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "Unauthorized" in err_str:
                refresh_tok = conn.get("refresh_token")
                if refresh_tok:
                    try:
                        new_tokens = await refresh_adp_token(refresh_tok)
                        await db.adp_connections.update_one(
                            {"employer_id": employer_id},
                            {"$set": {
                                "access_token": new_tokens.get("access_token"),
                                "refresh_token": new_tokens.get("refresh_token", refresh_tok),
                                "obtained_at": new_tokens.get("obtained_at"),
                            }},
                        )
                        adp_workers = await fetch_workers(new_tokens["access_token"])
                    except Exception as refresh_err:
                        logger.error(f"ADP token refresh failed: {refresh_err}")
                        raise HTTPException(status_code=401, detail="ADP session expired. Please reconnect.")
                else:
                    raise HTTPException(status_code=401, detail="ADP session expired. Please reconnect.")
            else:
                raise HTTPException(status_code=500, detail=f"Failed to fetch ADP data: {err_str}")

        payroll_employees = [transform_adp_worker(w, employer_id) for w in adp_workers]

        await db.payroll_employees.delete_many({"employer_id": employer_id})
        if payroll_employees:
            await db.payroll_employees.insert_many(payroll_employees)

        await db.adp_connections.update_one(
            {"employer_id": employer_id},
            {"$set": {
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "worker_count": len(payroll_employees),
            }},
        )

        clean = await db.payroll_employees.find(
            {"employer_id": employer_id}, {"_id": 0}
        ).to_list(500)

        return {
            "success": True,
            "message": f"Synced {len(clean)} employees from ADP",
            "count": len(clean),
            "employees": clean,
        }

    @api_router.post("/adp/disconnect/{employer_id}")
    async def disconnect_adp(employer_id: str, user=Depends(get_current_user)):
        await db.adp_connections.delete_one({"employer_id": employer_id})
        return {"success": True, "message": "ADP disconnected"}
