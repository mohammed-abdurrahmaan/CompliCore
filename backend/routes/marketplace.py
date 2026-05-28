from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import os
import shutil

router = APIRouter(prefix="/api/marketplace")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "marketplace")


# --- Pydantic Models ---

class QuoteRequestCreate(BaseModel):
    actuary_id: str
    plan_id: str
    employer_id: str
    plan_name: str
    message: Optional[str] = ""

class QuoteResponseUpdate(BaseModel):
    action: str  # "accept" or "reject"
    quoted_price: Optional[float] = None
    turnaround_days: Optional[int] = None
    actuary_message: Optional[str] = ""

class QuotePayment(BaseModel):
    payment_method: str = "platform"  # mock payment

class CertificationDelivery(BaseModel):
    mv_percentage: float
    certification_notes: str = ""
    document_name: str = ""

class CertificationValidation(BaseModel):
    valid: bool
    rejection_reason: Optional[str] = ""

class CertificationResubmission(BaseModel):
    mv_percentage: float
    certification_notes: str = ""
    document_name: str = ""

class ChatMessage(BaseModel):
    message: str


# --- Helper to create in-app notifications ---

async def create_notification(db, user_id: str, title: str, message: str, link: str = "", quote_id: str = ""):
    notif = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "link": link,
        "quote_id": quote_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notif)
    return notif


def register_marketplace_routes(parent_router, db, get_current_user, MOCK_ACTUARIES):
    """Register all marketplace routes on the parent router."""

    # --- Quote Requests ---

    @parent_router.post("/marketplace/quotes")
    async def create_quote_request(data: QuoteRequestCreate, user=Depends(get_current_user)):
        """Employer requests a quote from an actuary."""
        actuary = next((a for a in MOCK_ACTUARIES if a["id"] == data.actuary_id), None)
        if not actuary:
            raise HTTPException(status_code=404, detail="Actuary not found")

        plan = await db.plan_library.find_one({"id": data.plan_id}, {"_id": 0})
        if not plan:
            plan = await db.plans.find_one({"id": data.plan_id}, {"_id": 0})
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Check for duplicate active requests
        existing = await db.quote_requests.find_one({
            "employer_id": data.employer_id,
            "actuary_id": data.actuary_id,
            "plan_id": data.plan_id,
            "status": {"$in": ["pending", "accepted", "paid", "delivered"]}
        }, {"_id": 0})
        if existing:
            raise HTTPException(status_code=400, detail="An active quote request already exists for this actuary and plan")

        quote_id = str(uuid.uuid4())
        quote_doc = {
            "id": quote_id,
            "employer_id": data.employer_id,
            "employer_user_id": user["id"],
            "employer_name": user.get("company_name") or user["name"],
            "actuary_id": data.actuary_id,
            "actuary_name": actuary["name"],
            "actuary_firm": actuary["firm"],
            "actuary_email": actuary.get("email", ""),
            "plan_id": data.plan_id,
            "plan_name": data.plan_name,
            "plan_details": {
                "plan_type": plan.get("plan_type", ""),
                "individual_deductible": plan.get("individual_deductible", 0),
                "oop_max_individual": plan.get("oop_max_individual", 0),
                "coinsurance_rate": plan.get("coinsurance_rate", 0),
                "mv_percentage": plan.get("mv_percentage"),
            },
            "message": data.message or "",
            "status": "pending",  # pending -> accepted/rejected -> paid -> delivered -> validated/resubmit_needed
            "quoted_price": actuary.get("price", 0),
            "turnaround_days": actuary.get("turnaround_days", 14),
            "actuary_message": "",
            "payment_status": "unpaid",
            "certification": None,
            "validation": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.quote_requests.insert_one(quote_doc)
        quote_doc.pop("_id", None)

        # Notify actuary (mock user lookup for demo)
        await create_notification(
            db, data.actuary_id,
            "New Certification Request",
            f"{user['name']} requested MV certification for plan '{data.plan_name}'",
            f"/marketplace/quotes/{quote_id}",
            quote_id
        )

        return quote_doc

    @parent_router.get("/marketplace/quotes")
    async def get_quote_requests(user=Depends(get_current_user)):
        """Get all quote requests for the current user."""
        if user["role"] == "employer":
            quotes = await db.quote_requests.find(
                {"employer_user_id": user["id"]}, {"_id": 0}
            ).sort("created_at", -1).to_list(100)
        else:
            # Actuaries see only requests directed to them (matched by email)
            user_email = user.get("email", "")
            # Find actuary profile matching the user's email
            matching_actuary = next((a for a in MOCK_ACTUARIES if a.get("email") == user_email), None)
            if matching_actuary:
                quotes = await db.quote_requests.find(
                    {"actuary_id": matching_actuary["id"]}, {"_id": 0}
                ).sort("created_at", -1).to_list(100)
            else:
                # Fallback: match by actuary_email field
                quotes = await db.quote_requests.find(
                    {"actuary_email": user_email}, {"_id": 0}
                ).sort("created_at", -1).to_list(100)
        return quotes

    @parent_router.get("/marketplace/quotes/{quote_id}")
    async def get_quote_detail(quote_id: str, user=Depends(get_current_user)):
        quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        if not quote:
            raise HTTPException(status_code=404, detail="Quote request not found")

        # Enrich with full plan data from plan_library
        plan = await db.plan_library.find_one({"id": quote.get("plan_id")}, {"_id": 0})
        if plan:
            quote["full_plan"] = {
                "plan_name": plan.get("plan_name"),
                "carrier_name": plan.get("carrier_name"),
                "plan_type": plan.get("plan_type"),
                "category": plan.get("category"),
                "premiums": plan.get("premiums", {}),
                "employer_contribution": plan.get("employer_contribution", {}),
                "employee_cost": plan.get("employee_cost", {}),
                "individual_deductible": plan.get("individual_deductible", 0),
                "family_deductible": plan.get("family_deductible", 0),
                "coinsurance_rate": plan.get("coinsurance_rate", 0),
                "oop_max_individual": plan.get("oop_max_individual", 0),
                "oop_max_family": plan.get("oop_max_family", 0),
                "copay_primary": plan.get("copay_primary", 0),
                "copay_specialist": plan.get("copay_specialist", 0),
                "copay_er": plan.get("copay_er", 0),
                "copay_generic_rx": plan.get("copay_generic_rx", 0),
                "copay_brand_rx": plan.get("copay_brand_rx", 0),
                "mv_percentage": plan.get("mv_percentage"),
                "mv_certified": plan.get("mv_certified", False),
                "mec_qualified": plan.get("mec_qualified", False),
                "plan_year_start": plan.get("plan_year_start", ""),
                "plan_year_end": plan.get("plan_year_end", ""),
                "sbc_url": plan.get("sbc_url", ""),
            }

            # Get employee count and demographics for this employer
            employees = await db.employee_profiles.find(
                {"employer_id": quote.get("employer_id")},
                {"_id": 0, "name": 1, "annual_salary": 1, "department": 1}
            ).to_list(500)
            if not employees:
                employees = await db.payroll_employees.find(
                    {"employer_id": quote.get("employer_id")},
                    {"_id": 0, "name": 1, "annual_salary": 1, "department": 1}
                ).to_list(500)

            quote["employee_count"] = len(employees)

            # Document checklist for MV certification
            quote["document_checklist"] = [
                {"name": "Summary Plan Description (SPD)", "description": "Full benefits, copays, deductibles", "format": "PDF", "required": True, "available": True},
                {"name": "Summary of Benefits & Coverage (SBC)", "description": "ACA-mandated plan summary", "format": "PDF", "required": True, "available": bool(plan.get("sbc_url"))},
                {"name": "Plan Document", "description": "Legal benefit definitions", "format": "PDF", "required": True, "available": True},
                {"name": "Rate Sheets", "description": "Premiums by tier (self-only required)", "format": "Excel", "required": True, "available": bool(plan.get("premiums", {}).get("self_only"))},
                {"name": "Evidence of Coverage (EOC)", "description": "Detailed policy language", "format": "PDF", "required": True, "available": False},
                {"name": "Network Details", "description": "In-network vs out-of-network", "format": "Excel/PDF", "required": False, "available": False},
                {"name": "Prescription Formulary", "description": "Tier 1/2/3 copays", "format": "PDF", "required": True, "available": bool(plan.get("copay_generic_rx") or plan.get("copay_brand_rx"))},
                {"name": "Recent Claims Data (12 months)", "description": "Utilization for MVC adjustments", "format": "CSV/Claims run", "required": False, "available": False},
                {"name": "Employer Contributions", "description": "% paid by employer per tier", "format": "Excel", "required": True, "available": bool(plan.get("employer_contribution", {}).get("self_only"))},
                {"name": "Non-Standard Features", "description": "Wellness, HRA, spousal surcharges", "format": "Memo", "required": True, "available": False},
                {"name": "Demographics", "description": "Age/gender distribution of covered employees", "format": "Excel", "required": False, "available": len(employees) > 0},
                {"name": "Prior MV Certification", "description": "Year-over-year comparison", "format": "PDF", "required": False, "available": bool(plan.get("mv_certified"))},
            ]

        return quote

    @parent_router.post("/marketplace/quotes/{quote_id}/upload")
    async def upload_quote_document(
        quote_id: str,
        file: UploadFile = File(...),
        doc_type: str = Form("general"),
        doc_label: str = Form(""),
        user=Depends(get_current_user)
    ):
        """Upload a document to a quote (employer or actuary)."""
        quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        if not quote:
            raise HTTPException(status_code=404, detail="Quote request not found")

        # Validate file size (max 20MB)
        contents = await file.read()
        if len(contents) > 20 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 20MB)")

        doc_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename or "")[1] or ".pdf"
        safe_name = f"{doc_id}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(contents)

        doc_meta = {
            "id": doc_id,
            "filename": file.filename,
            "stored_name": safe_name,
            "doc_type": doc_type,
            "doc_label": doc_label or file.filename,
            "content_type": file.content_type or "application/octet-stream",
            "size": len(contents),
            "uploaded_by": user["id"],
            "uploaded_by_role": user["role"],
            "uploaded_by_name": user.get("name", ""),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        # Add to quote's documents array
        field = "employer_documents" if user["role"] == "employer" else "actuary_documents"
        await db.quote_requests.update_one(
            {"id": quote_id},
            {"$push": {field: doc_meta}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
        )

        return {"id": doc_id, "filename": file.filename, "doc_label": doc_label or file.filename, "size": len(contents)}

    @parent_router.delete("/marketplace/documents/{doc_id}")
    async def delete_quote_document(doc_id: str, user=Depends(get_current_user)):
        """Delete a document from a quote."""
        # Find the quote containing this document
        quote = await db.quote_requests.find_one(
            {"$or": [{"employer_documents.id": doc_id}, {"actuary_documents.id": doc_id}]}, {"_id": 0}
        )
        if not quote:
            raise HTTPException(status_code=404, detail="Document not found")

        # Remove from the appropriate array
        for field in ["employer_documents", "actuary_documents"]:
            docs = quote.get(field, [])
            for doc in docs:
                if doc["id"] == doc_id:
                    # Delete file
                    file_path = os.path.join(UPLOAD_DIR, doc["stored_name"])
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    await db.quote_requests.update_one(
                        {"id": quote["id"]},
                        {"$pull": {field: {"id": doc_id}}}
                    )
                    return {"deleted": True}

        raise HTTPException(status_code=404, detail="Document not found")

    @parent_router.get("/marketplace/documents/{doc_id}/download")
    async def download_quote_document(doc_id: str, user=Depends(get_current_user)):
        """Download a document from a quote."""
        quote = await db.quote_requests.find_one(
            {"$or": [{"employer_documents.id": doc_id}, {"actuary_documents.id": doc_id}]}, {"_id": 0}
        )
        if not quote:
            raise HTTPException(status_code=404, detail="Document not found")

        for field in ["employer_documents", "actuary_documents"]:
            for doc in quote.get(field, []):
                if doc["id"] == doc_id:
                    file_path = os.path.join(UPLOAD_DIR, doc["stored_name"])
                    if not os.path.exists(file_path):
                        raise HTTPException(status_code=404, detail="File not found on disk")
                    return FileResponse(
                        file_path,
                        media_type=doc.get("content_type", "application/octet-stream"),
                        filename=doc["filename"]
                    )

        raise HTTPException(status_code=404, detail="Document not found")

    @parent_router.put("/marketplace/quotes/{quote_id}/respond")
    async def respond_to_quote(quote_id: str, data: QuoteResponseUpdate, user=Depends(get_current_user)):
        """Actuary accepts or rejects a quote request."""
        quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        if not quote:
            raise HTTPException(status_code=404, detail="Quote request not found")
        if quote["status"] != "pending":
            raise HTTPException(status_code=400, detail="Quote is not in pending state")

        if data.action == "accept":
            update = {
                "status": "accepted",
                "quoted_price": data.quoted_price or quote["quoted_price"],
                "turnaround_days": data.turnaround_days or quote["turnaround_days"],
                "actuary_message": data.actuary_message or "",
                "accepted_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            notif_title = "Quote Accepted"
            notif_msg = f"{quote['actuary_name']} accepted your certification request for '{quote['plan_name']}'. Price: ${update['quoted_price']:,.0f}"
        elif data.action == "reject":
            update = {
                "status": "rejected",
                "actuary_message": data.actuary_message or "Request declined",
                "rejected_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            notif_title = "Quote Declined"
            notif_msg = f"{quote['actuary_name']} declined your certification request for '{quote['plan_name']}'"
        else:
            raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'")

        await db.quote_requests.update_one({"id": quote_id}, {"$set": update})

        await create_notification(
            db, quote["employer_user_id"],
            notif_title, notif_msg,
            f"/marketplace/quotes/{quote_id}", quote_id
        )

        updated = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        return updated

    @parent_router.put("/marketplace/quotes/{quote_id}/pay")
    async def pay_quote(quote_id: str, data: QuotePayment, user=Depends(get_current_user)):
        """Employer pays for the accepted quote (mock payment)."""
        quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        if not quote:
            raise HTTPException(status_code=404, detail="Quote request not found")
        if quote["status"] != "accepted":
            raise HTTPException(status_code=400, detail="Quote must be accepted before payment")

        # Require at least one employer document before payment
        employer_docs = quote.get("employer_documents", [])
        if not employer_docs:
            raise HTTPException(status_code=400, detail="Please upload at least one document before paying")

        update = {
            "status": "paid",
            "payment_status": "paid",
            "payment_method": data.payment_method,
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.quote_requests.update_one({"id": quote_id}, {"$set": update})

        await create_notification(
            db, quote["actuary_id"],
            "Payment Received",
            f"Payment received for '{quote['plan_name']}' certification. Please begin your review.",
            f"/marketplace/quotes/{quote_id}", quote_id
        )

        updated = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        return updated

    @parent_router.put("/marketplace/quotes/{quote_id}/deliver")
    async def deliver_certification(quote_id: str, data: CertificationDelivery, user=Depends(get_current_user)):
        """Actuary delivers the certification result."""
        quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        if not quote:
            raise HTTPException(status_code=404, detail="Quote request not found")
        if quote["status"] not in ["paid", "resubmit_needed"]:
            raise HTTPException(status_code=400, detail="Quote must be paid or in resubmission before delivery")

        # Require at least one actuary document before delivery
        actuary_docs = quote.get("actuary_documents", [])
        if not actuary_docs:
            raise HTTPException(status_code=400, detail="Please upload at least one document before delivering certification")

        certification = {
            "mv_percentage": data.mv_percentage,
            "certification_notes": data.certification_notes,
            "document_name": data.document_name or f"MV_Certification_{quote['plan_name']}.pdf",
            "delivered_at": datetime.now(timezone.utc).isoformat(),
            "delivery_count": (quote.get("certification", {}) or {}).get("delivery_count", 0) + 1
        }

        update = {
            "status": "delivered",
            "certification": certification,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.quote_requests.update_one({"id": quote_id}, {"$set": update})

        # Update plan_library with the actuary's MV result immediately on delivery
        mv_pct = data.mv_percentage
        await db.plan_library.update_one(
            {"id": quote["plan_id"]},
            {"$set": {
                "mv_calculated": True,
                "mv_percentage": mv_pct,
                "mv_certified": True,
                "mv_meets_minimum": mv_pct >= 60.0,
                "certification_source": "actuary",
                "certified_by": user.get("name", ""),
                "certified_at": datetime.now(timezone.utc).isoformat(),
            }}
        )

        await create_notification(
            db, quote["employer_user_id"],
            "Certification Delivered",
            f"MV certification for '{quote['plan_name']}' has been delivered. MV: {data.mv_percentage}%",
            f"/marketplace/quotes/{quote_id}", quote_id
        )

        updated = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        return updated

    @parent_router.put("/marketplace/quotes/{quote_id}/validate")
    async def validate_certification(quote_id: str, data: CertificationValidation, user=Depends(get_current_user)):
        """Platform validates the certification document."""
        quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        if not quote:
            raise HTTPException(status_code=404, detail="Quote request not found")
        if quote["status"] != "delivered":
            raise HTTPException(status_code=400, detail="Certification must be delivered before validation")

        validation = {
            "valid": data.valid,
            "rejection_reason": data.rejection_reason if not data.valid else "",
            "validated_at": datetime.now(timezone.utc).isoformat()
        }

        if data.valid:
            new_status = "validated"
            cert = quote.get("certification", {})
            mv_pct = cert.get("mv_percentage", 0) if cert else 0
            await db.plan_library.update_one(
                {"id": quote["plan_id"]},
                {"$set": {
                    "mv_calculated": True,
                    "mv_percentage": mv_pct,
                    "mv_certified": True,
                    "mv_meets_minimum": mv_pct >= 60.0,
                    "certification_source": "actuary",
                    "certification_status": "accepted",
                    "certified_by": quote["actuary_name"],
                    "certified_at": datetime.now(timezone.utc).isoformat(),
                    "validated_at": datetime.now(timezone.utc).isoformat(),
                }}
            )
            await db.plans.update_one(
                {"id": quote["plan_id"]},
                {"$set": {
                    "mv_calculated": True,
                    "mv_percentage": mv_pct,
                    "mv_meets_minimum": mv_pct >= 60.0,
                    "certification_source": "actuary",
                    "certification_status": "accepted",
                    "certified_by": quote["actuary_name"],
                    "certified_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            notif_title = "Certification Accepted"
            notif_msg = f"You accepted the MV certification for '{quote['plan_name']}'. MV: {mv_pct}%. Plan updated."
            notif_actuary_msg = f"Employer accepted your certification for '{quote['plan_name']}'. MV: {mv_pct}%."
        else:
            new_status = "resubmit_needed"
            # Revert plan to pre-certification state since employer rejected
            await db.plan_library.update_one(
                {"id": quote["plan_id"]},
                {"$set": {
                    "certification_source": "actuary",
                    "certification_status": "rejected",
                    "rejection_reason": data.rejection_reason,
                }}
            )
            notif_title = "Certification Rejected"
            notif_msg = f"You rejected the MV certification for '{quote['plan_name']}'. Reason: {data.rejection_reason}. Actuary will resubmit."
            notif_actuary_msg = f"Employer rejected your certification for '{quote['plan_name']}'. Reason: {data.rejection_reason}. Please resubmit."

        update = {
            "status": new_status,
            "validation": validation,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.quote_requests.update_one({"id": quote_id}, {"$set": update})

        await create_notification(
            db, quote["employer_user_id"],
            notif_title, notif_msg,
            f"/marketplace/quotes/{quote_id}", quote_id
        )
        await create_notification(
            db, quote["actuary_id"],
            notif_title, notif_actuary_msg,
            f"/marketplace/quotes/{quote_id}", quote_id
        )

        updated = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        return updated

    # --- Chat / Messaging ---

    @parent_router.get("/marketplace/quotes/{quote_id}/messages")
    async def get_quote_messages(quote_id: str, user=Depends(get_current_user)):
        """Get all chat messages for a quote."""
        quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        if not quote:
            raise HTTPException(status_code=404, detail="Quote request not found")
        messages = await db.quote_messages.find(
            {"quote_id": quote_id}, {"_id": 0}
        ).sort("created_at", 1).to_list(200)
        return messages

    @parent_router.post("/marketplace/quotes/{quote_id}/messages")
    async def send_quote_message(quote_id: str, data: ChatMessage, user=Depends(get_current_user)):
        """Send a chat message on a quote (available after acceptance)."""
        quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0})
        if not quote:
            raise HTTPException(status_code=404, detail="Quote request not found")

        allowed_statuses = ["accepted", "paid", "delivered", "resubmit_needed", "validated"]
        if quote["status"] not in allowed_statuses:
            raise HTTPException(status_code=400, detail="Chat is available after the quote is accepted")

        if not data.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        msg_doc = {
            "id": str(uuid.uuid4()),
            "quote_id": quote_id,
            "sender_id": user["id"],
            "sender_name": user.get("name", ""),
            "sender_role": user["role"],
            "message": data.message.strip(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.quote_messages.insert_one(msg_doc)
        msg_doc.pop("_id", None)

        # Notify the other party
        if user["role"] == "employer":
            recipient_id = quote["actuary_id"]
            notif_msg = f"{user['name']} sent a message about '{quote['plan_name']}'"
        else:
            recipient_id = quote["employer_user_id"]
            notif_msg = f"{user['name']} sent a message about '{quote['plan_name']}'"

        await create_notification(
            db, recipient_id,
            "New Message",
            notif_msg,
            f"/marketplace?quote_id={quote_id}",
            quote_id
        )

        return msg_doc

    # --- Notifications ---

    @parent_router.get("/notifications")
    async def get_notifications(user=Depends(get_current_user)):
        notifs = await db.notifications.find(
            {"user_id": user["id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        unread = sum(1 for n in notifs if not n.get("read"))
        return {"notifications": notifs, "unread_count": unread}

    @parent_router.put("/notifications/{notif_id}/read")
    async def mark_notification_read(notif_id: str, user=Depends(get_current_user)):
        await db.notifications.update_one(
            {"id": notif_id, "user_id": user["id"]},
            {"$set": {"read": True}}
        )
        return {"message": "Marked as read"}

    @parent_router.put("/notifications/read-all")
    async def mark_all_notifications_read(user=Depends(get_current_user)):
        await db.notifications.update_many(
            {"user_id": user["id"], "read": False},
            {"$set": {"read": True}}
        )
        return {"message": "All marked as read"}
