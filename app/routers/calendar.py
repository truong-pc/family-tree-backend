from datetime import date
from fastapi import APIRouter, HTTPException
from app.utils.amlichcalendar import VanSu
from app.utils.lunar_converter import parse_van_su_info

router = APIRouter(prefix="/api/v1/calendar", tags=["Calendar"])


@router.get("/today")
async def get_today_info():
    today = date.today()
    try:
        raw = VanSu.getInfo(today.year, today.month, today.day, "s")
        info = parse_van_su_info(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý lịch: {e}")
    return info
