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


@router.get("/info")
async def get_date_info(day: int, month: int, year: int):
    # try:
    #     target = date(year, month, day)
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=f"Ngày dương lịch không hợp lệ: {e}")
    try:
        raw = VanSu.getInfo(year, month, day, "s")
        info = parse_van_su_info(raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý lịch: {e}")
    return info
