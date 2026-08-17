"""API v1 package router."""

from fastapi import APIRouter
from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.batches import router as batches_router
from app.api.v1.courses import router as courses_router
from app.api.v1.health import router as health_router
from app.api.v1.public import router as public_router
from app.api.v1.statement_imports import router as statement_imports_router

v1_router = APIRouter()
v1_router.include_router(health_router, tags=["Health"])
v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
v1_router.include_router(courses_router, prefix="/admin/courses", tags=["Admin Courses"])
v1_router.include_router(batches_router, prefix="/admin/batches", tags=["Admin Batches"])
v1_router.include_router(statement_imports_router, prefix="/admin/statement-imports", tags=["Admin Statement Imports"])
v1_router.include_router(public_router, prefix="/public", tags=["Public Registration"])

