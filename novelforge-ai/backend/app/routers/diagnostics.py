import datetime
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services.diagnostics_service import run_diagnostics

router = APIRouter()


@router.get("/diagnostics")
async def diagnostics(db: Session = Depends(get_db)):
    return await run_diagnostics(db)
