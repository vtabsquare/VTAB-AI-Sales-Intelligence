from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.models.db import get_db
from app.services.sales_manager import policy_for

r = APIRouter(prefix="/api/sales-manager", tags=["sales-manager-guardrails"])


class GuardedPolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool
    auto_initial_outreach: bool = False
    auto_acknowledge: bool = False
    daily_limit: int = Field(default=10, ge=1, le=100)
    batch_size: int = Field(default=10, ge=1, le=50)


def _fields(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


@r.put("/policy")
def configure_guarded_policy(payload: GuardedPolicyInput, db: Session = Depends(get_db)):
    # Initial outreach must always stop for a human approval + explicit send action.
    if payload.auto_initial_outreach:
        raise HTTPException(
            409,
            "Automatic initial outreach is disabled by governance. Approve the exact draft and release it manually from Send Center.",
        )
    # Automatic acknowledgements are also held until live operations are separately approved.
    if payload.auto_acknowledge:
        raise HTTPException(
            409,
            "Automatic reply acknowledgement is disabled by governance. Keep responses under human review.",
        )

    policy = policy_for(db)
    policy.enabled = payload.enabled
    policy.auto_initial_outreach = False
    policy.auto_acknowledge = False
    policy.daily_limit = payload.daily_limit
    policy.batch_size = payload.batch_size
    policy.updated_at = datetime.utcnow()
    db.commit()
    return {
        "policy": _fields(policy),
        "message": "Sales agent policy saved. Human approval and explicit Send Center release remain mandatory.",
    }
