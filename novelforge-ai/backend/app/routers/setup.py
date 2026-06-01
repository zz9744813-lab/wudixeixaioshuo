from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.health import router as health_router
from app.schemas.setup import SetupStatusOut
from app.services.setup_service import compute_setup_status

router = APIRouter()


@router.get("/setup/status", response_model=SetupStatusOut)
async def setup_status(db: Session = Depends(get_db)):
    return compute_setup_status(db)
