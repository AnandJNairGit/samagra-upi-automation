"""Protected admin endpoints demonstrating authorization middleware."""

from fastapi import APIRouter
from app.auth.dependencies import require_admin
from app.models.admin_user import AdminUser
from app.schemas.auth import AdminHealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=AdminHealthResponse,
    summary="Protected Admin Health Verification",
)
async def admin_health(
    current_admin: AdminUser = require_admin,
):
    """Protected health endpoint to verify admin authorization middleware."""
    return AdminHealthResponse(
        status="ok",
        authenticated=True,
        admin_email=current_admin.email,
        admin_public_id=current_admin.public_id,
    )
