from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthUser, verify_supabase_jwt
from app.db import get_db
from app.schemas import MeOut, MePatch, SettingsOut
from app.services.job_service import ensure_user

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeOut)
async def get_me(auth: AuthUser = Depends(verify_supabase_jwt), db: AsyncSession = Depends(get_db)) -> MeOut:
    user = await ensure_user(db, auth.id, auth.email)
    await db.commit()
    return MeOut(
        id=user.id,
        email=user.email or auth.email,
        display_name=user.display_name,
        plan=user.plan,
        quota={"limit": user.monthly_quota, "used": user.used_this_month, "reset_at": user.quota_reset_at},
        settings=SettingsOut.model_validate(user.settings, from_attributes=True),
    )


@router.patch("", response_model=MeOut)
async def patch_me(payload: MePatch, auth: AuthUser = Depends(verify_supabase_jwt), db: AsyncSession = Depends(get_db)) -> MeOut:
    user = await ensure_user(db, auth.id, auth.email)
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.settings:
        for key in {"store_raw_text", "notify_on_job_complete", "telemetry_opt_in", "preferred_language"}:
            if key in payload.settings:
                setattr(user.settings, key, payload.settings[key])
    await db.commit()
    return MeOut(
        id=user.id,
        email=user.email or auth.email,
        display_name=user.display_name,
        plan=user.plan,
        quota={"limit": user.monthly_quota, "used": user.used_this_month, "reset_at": user.quota_reset_at},
        settings=SettingsOut.model_validate(user.settings, from_attributes=True),
    )
