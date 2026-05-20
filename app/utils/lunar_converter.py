from datetime import date
from typing import Optional
from app.utils.amlichcalendar import Solar, Lunar, LunarYear


def parse_van_su_info(info_str: str) -> dict:
    """
    Parse the raw string returned by VanSu.getInfo() into a structured dict.

    Expected line layout (8 lines, '\n'-separated):
      0: "7/5/2026\tTHỨ NĂM\tNgày 21/3/2026 ÂL"
      1: "Ngày Tân Tị - Tháng Nhâm Thìn - Năm Bính Ngọ"
      2: "Hành Kim - Sao Đẩu"
      3: "<lục diệu>"
      4: "<bách kỵ>"
      5: "- Giờ tốt: Sửu (1h - 3h), ..."
      6: "- Tuổi xung: Tân Tị, ..."
      7: "- Thuộc tiết Lập Hạ."
    """
    lines = [l.strip() for l in info_str.split("\n")]

    # Line 0 – solar date / weekday / lunar date
    parts0 = lines[0].split("\t")
    sd, sm, sy = (int(x) for x in parts0[0].split("/"))
    weekday = parts0[1].strip()
    # Phát hiện và loại bỏ hậu tố '(tháng nhuận)' trước khi parse ngày âm
    lunar_part = parts0[2]
    lunar_is_leap = "(tháng nhuận)" in lunar_part
    lunar_date_str = (
        lunar_part
        .replace("Ngày", "")
        .replace("ÂL", "")
        .replace("(tháng nhuận)", "")
        .strip()
    )
    ld, lm, ly = (int(x) for x in lunar_date_str.split("/"))

    # Line 1 – can-chi labels
    can_chi = [p.strip() for p in lines[1].split(" - ")]
    day_can_chi = can_chi[0].removeprefix("Ngày").strip()
    month_can_chi = can_chi[1].removeprefix("Tháng").strip()
    year_can_chi = can_chi[2].removeprefix("Năm").strip()

    # Line 2 – hành / sao
    parts2 = [p.strip() for p in lines[2].split(" - ")]
    hanh = parts2[0].removeprefix("Hành").strip()
    sao = parts2[1].removeprefix("Sao").strip()

    # Lines 3 & 4 – lục diệu / bách kỵ
    luc_dieu = lines[3].strip()
    bach_ky = lines[4].strip()

    # Line 5 – giờ tốt
    gio_tot_raw = lines[5].removeprefix("-").strip().removeprefix("Giờ tốt:").strip()
    gio_tot = [g.strip() for g in gio_tot_raw.split(",") if g.strip()]

    # Line 6 – tuổi xung
    tuoi_xung: list[str] = []
    if len(lines) > 6 and lines[6].startswith("-"):
        tuoi_xung_raw = lines[6].removeprefix("-").strip().removeprefix("Tuổi xung:").strip()
        tuoi_xung = [t.strip() for t in tuoi_xung_raw.split(",") if t.strip()]

    # Line 7 – tiết
    tiet = ""
    if len(lines) > 7 and lines[7].startswith("-"):
        tiet = (
            lines[7].removeprefix("-").strip()
            .removeprefix("Thuộc tiết").strip()
            .rstrip(".")
        )

    return {
        "solar": {"day": sd, "month": sm, "year": sy, "weekday": weekday},
        "lunar": {
            "day": ld, "month": lm, "year": ly,
            "isLeap": lunar_is_leap,
            "dayCanChi": day_can_chi,
            "monthCanChi": month_can_chi,
            "yearCanChi": year_can_chi,
        },
        "hanh": hanh,
        "sao": sao,
        "lucDieu": luc_dieu,
        "bachKy": bach_ky,
        "gioTot": gio_tot,
        "tuoiXung": tuoi_xung,
        "tiet": tiet,
    }


def solar_to_lunar(dod: Optional[date]) -> Optional[dict]:
    """
    Convert a solar (Gregorian) date of death to lunar calendar fields.
    Returns dict with lunarDeathDay, lunarDeathMonth, lunarDeathYear, lunarIsLeap
    or None if dod is None.
    """
    if dod is None:
        return None

    lunar = Solar.fromYmd(dod.year, dod.month, dod.day).getLunar()
    return {
        "lunarDeathDay": lunar.getDay(),
        "lunarDeathMonth": abs(lunar.getMonth()),
        "lunarDeathYear": lunar.getYear(),
        "lunarIsLeap": lunar.isLeap(),
    }


def get_leap_month(lunar_year: int) -> int:
    """Return the leap month number for a lunar year, or 0 if none."""
    return LunarYear.fromYear(lunar_year).getLeapMonth()


def lunar_to_solar(year: int, month: int, day: int, is_leap: bool = False) -> date:
    """
    Convert a specific lunar date to a solar (Gregorian) date.

    `is_leap=True` means the date is in the leap month of that lunar year.
    Raises ValueError if the lunar date does not exist (e.g. day out of range,
    or is_leap=True but the year has no matching leap month).
    """
    if is_leap and get_leap_month(year) != month:
        raise ValueError(f"Lunar year {year} has no leap month {month}")
    try:
        solar = Lunar.fromYmd(year, month, day, is_leap).getSolar()
    except Exception as e:
        raise ValueError(str(e)) from e
    return date(solar.getYear(), solar.getMonth(), solar.getDay())
