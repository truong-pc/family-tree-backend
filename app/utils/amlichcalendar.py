# ===================================================================
# Module amlichcalendar.py
#
# Module lịch âm – dương Việt Nam được tự code lại cho dự án, không
# phụ thuộc thư viện ngoài.
#
# Cấu trúc class (Date, SolarAndLunar, CanChi, TotXau, TietKhi, VanSu)
# được port lại từ thư viện vncalendar (tác giả Hoàng Đức Tùng), có
# sửa bug ở SolarAndLunar.getLeapMonthOffset (vncalendar gốc so sánh
# sector 0..11 với khoảng 0..360 nên luôn trả về 1 và không phát hiện
# được tháng nhuận).
#
# Phần adapter Solar / Lunar / LunarYear ở cuối file mô phỏng API của
# thư viện lunar-python, có hàm getLeapMonth tính chính xác tháng
# nhuận của một năm âm lịch.
#
# Thuật toán chuyển đổi giữa dương lịch và âm lịch tham khảo từ
# bài viết của Hồ Ngọc Đức:
# https://lyso.vn/co-ban/thuat-toan-tinh-am-lich-ho-ngoc-duc-t2093/
#
# Quy ước:
# - Mọi hàm tham số ngày đều theo thứ tự (year, month, day) – giống
#   datetime.date của Python.
# - Chuỗi trả về (can chi, tiết khí, hoàng đạo, ...) giữ tiếng Việt.
# - Comment / docstring viết bằng tiếng Việt.
# ===================================================================

from datetime import date, datetime, timedelta
import math


class Date:
    """Tiện ích về ngày dương lịch (Gregorian)."""

    @staticmethod
    def convertDate2jdn(y, m, d):
        """Đổi ngày dương lịch sang Julian Day Number (JDN)."""
        a = (14 - m) // 12
        y2 = y + 4800 - a
        m2 = m + 12 * a - 3
        return d + (153 * m2 + 2) // 5 + 365 * y2 + y2 // 4 - y2 // 100 + y2 // 400 - 32045

    @staticmethod
    def convertjdn2Date(j):
        """Đổi JDN ngược lại thành (year, month, day)."""
        a = j + 32044
        b = (4 * a + 3) // 146097
        c = a - (146097 * b) // 4
        d = (4 * c + 3) // 1461
        e = c - (1461 * d) // 4
        m = (5 * e + 2) // 153
        da = e - (153 * m + 2) // 5 + 1
        mo = m + 3 - 12 * (m // 10)
        ye = 100 * b + d - 4800 + m // 10
        return ye, mo, da

    @staticmethod
    def dayWeek(y, m, d):
        """Tên thứ trong tuần (Thứ hai, Thứ ba, ...) bằng tiếng Việt."""
        a = ['Thứ bảy', 'Chủ nhật', 'Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu']
        if m == 1:
            m = 13
            y -= 1
        elif m == 2:
            m = 14
            y -= 1
        # Công thức Zeller
        h = (d + math.floor(13 * (m + 1) / 5) + y + math.floor(y / 4)
             - math.floor(y / 100) + math.floor(y / 400)) % 7
        return a[h]


class SolarAndLunar:
    """Chuyển đổi dương ↔ âm theo thuật toán Hồ Ngọc Đức."""

    @staticmethod
    def getNewMoonDay(k, timeZone=7.0):
        """JDN của lần Sóc thứ k tính từ 1900-01-01."""
        T = k / 1236.85
        T2 = T * T
        T3 = T2 * T
        dr = math.pi / 180
        Jd1 = 2415020.75933 + 29.53058868 * k + 0.0001178 * T2 - 0.000000155 * T3
        Jd1 = Jd1 + 0.00033 * math.sin((166.56 + 132.87 * T - 0.009173 * T2) * dr)
        M = 359.2242 + 29.10535608 * k - 0.0000333 * T2 - 0.00000347 * T3
        Mpr = 306.0253 + 385.81691806 * k + 0.0107306 * T2 + 0.00001236 * T3
        F = 21.2964 + 390.67050646 * k - 0.0016528 * T2 - 0.00000239 * T3
        C1 = (0.1734 - 0.000393 * T) * math.sin(M * dr) + 0.0021 * math.sin(2 * dr * M)
        C1 = C1 - 0.4068 * math.sin(Mpr * dr) + 0.0161 * math.sin(dr * 2 * Mpr)
        C1 = C1 - 0.0004 * math.sin(dr * 3 * Mpr)
        C1 = C1 + 0.0104 * math.sin(dr * 2 * F) - 0.0051 * math.sin(dr * (M + Mpr))
        C1 = C1 - 0.0074 * math.sin(dr * (M - Mpr)) + 0.0004 * math.sin(dr * (2 * F + M))
        C1 = C1 - 0.0004 * math.sin(dr * (2 * F - M)) - 0.0006 * math.sin(dr * (2 * F + Mpr))
        C1 = C1 + 0.0010 * math.sin(dr * (2 * F - Mpr)) + 0.0005 * math.sin(dr * (2 * Mpr + M))
        if T < -11:
            deltat = 0.001 + 0.000839 * T + 0.0002261 * T2 - 0.00000845 * T3 - 0.000000081 * T * T3
        else:
            deltat = -0.000278 + 0.000265 * T + 0.000262 * T2
        JdNew = Jd1 + C1 - deltat
        return math.floor(JdNew + 0.5 + timeZone / 24)

    @staticmethod
    def getSunLongitude(jdn, timeZone=7.0):
        """Vị trí Mặt Trời tại JDN, trả về cung 0..11 (mỗi cung 30°)."""
        T = (jdn - 2451545.5 - timeZone / 24) / 36525
        T2 = T * T
        dr = math.pi / 180
        M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T * T2
        L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
        DL = (1.914600 - 0.004817 * T - 0.000014 * T2) * math.sin(dr * M)
        DL = DL + (0.019993 - 0.000101 * T) * math.sin(dr * 2 * M) + 0.000290 * math.sin(dr * 3 * M)
        L = L0 + DL
        L = L * dr
        L = L - math.pi * 2 * (math.floor(L / (math.pi * 2)))
        return math.floor(L / math.pi * 6)

    @staticmethod
    def getLunarMonth11(yy, timeZone=7.0):
        """JDN của ngày mùng 1 tháng 11 âm lịch trong năm dương lịch yy
        (tháng chứa Đông chí)."""
        off = Date.convertDate2jdn(yy, 12, 31) - 2415021
        k = math.floor(off / 29.530588853)
        nm = SolarAndLunar.getNewMoonDay(k, timeZone)
        sunLong = SolarAndLunar.getSunLongitude(nm, timeZone)
        if sunLong >= 9:
            nm = SolarAndLunar.getNewMoonDay(k - 1, timeZone)
        return nm

    @staticmethod
    def getLeapMonthOffset(a11, timeZone=7.0):
        """Độ lệch (1..13) từ tháng 11 a11 tới tháng nhuận trong chu kỳ.

        Sửa lại so với vncalendar gốc (so sánh sector 0..11 với 0..360
        nên luôn ra 1). Theo thuật toán Hồ Ngọc Đức: tháng âm không
        chứa trung khí (Zhongqi) là tháng nhuận. Vì getSunLongitude
        trả về cung 30° (0..11), nếu sun-sector tại đầu tháng i và đầu
        tháng i+1 trùng nhau thì không có biên giới 30° nào bị vượt
        qua trong tháng i ⇒ tháng i là tháng nhuận.
        """
        k = int((a11 - 2415021.076998695) / 29.530588853 + 0.5)
        for i in range(1, 14):
            ms_i = SolarAndLunar.getNewMoonDay(k + i, timeZone)
            ms_next = SolarAndLunar.getNewMoonDay(k + i + 1, timeZone)
            s1 = SolarAndLunar.getSunLongitude(ms_i, timeZone)
            s2 = SolarAndLunar.getSunLongitude(ms_next, timeZone)
            if s1 == s2:
                return i
        return 13

    @staticmethod
    def convertSolar2Lunar(yy, mm, dd, timeZone=7.0):
        """Đổi (yy, mm, dd) dương lịch sang (year, month, day, isLeap) âm lịch."""
        dayNumber = Date.convertDate2jdn(yy, mm, dd)
        k = math.floor((dayNumber - 2415021.076998695) / 29.530588853)
        monthStart = SolarAndLunar.getNewMoonDay(k + 1, timeZone)
        if monthStart > dayNumber:
            monthStart = SolarAndLunar.getNewMoonDay(k, timeZone)
        a11 = SolarAndLunar.getLunarMonth11(yy, timeZone)
        b11 = a11
        if a11 >= monthStart:
            lunarYear = yy
            a11 = SolarAndLunar.getLunarMonth11(yy - 1, timeZone)
        else:
            lunarYear = yy + 1
            b11 = SolarAndLunar.getLunarMonth11(yy + 1, timeZone)
        lunarDay = dayNumber - monthStart + 1
        diff = math.floor((monthStart - a11) / 29)
        lunarLeap = 0
        lunarMonth = diff + 11
        if b11 - a11 > 365:
            leapMonthDiff = SolarAndLunar.getLeapMonthOffset(a11, timeZone)
            if diff >= leapMonthDiff:
                lunarMonth = diff + 10
                if diff == leapMonthDiff:
                    lunarLeap = 1
        if lunarMonth > 12:
            lunarMonth = lunarMonth - 12
        if lunarMonth >= 11 and diff < 4:
            lunarYear -= 1
        return lunarYear, lunarMonth, lunarDay, lunarLeap

    @staticmethod
    def convertLunar2Solar(lunarYear, lunarMonth, lunarDay, lunarLeap, timeZone=7.0):
        """Đổi ngày âm sang dương, trả về (year, month, day).
        Trả về (0, 0, 0) nếu ngày âm không hợp lệ."""
        if lunarMonth < 11:
            a11 = SolarAndLunar.getLunarMonth11(lunarYear - 1, timeZone)
            b11 = SolarAndLunar.getLunarMonth11(lunarYear, timeZone)
        else:
            a11 = SolarAndLunar.getLunarMonth11(lunarYear, timeZone)
            b11 = SolarAndLunar.getLunarMonth11(lunarYear + 1, timeZone)
        off = lunarMonth - 11
        if off < 0:
            off += 12
        if b11 - a11 > 365:
            leapOff = SolarAndLunar.getLeapMonthOffset(a11, timeZone)
            leapMonth = leapOff - 2
            if leapMonth < 0:
                leapMonth += 12
            if lunarLeap != 0 and lunarMonth != leapMonth:
                return (0, 0, 0)
            elif lunarLeap != 0 or off >= leapOff:
                off += 1
        k = int(0.5 + (a11 - 2415021.076998695) / 29.530588853)
        monthStart = SolarAndLunar.getNewMoonDay(k + off, timeZone)
        return Date.convertjdn2Date(monthStart + lunarDay - 1)


# ---------------------------------------------------------------------------
# CAN CHI – Thập can / Thập nhị chi cho năm, tháng, ngày
# ---------------------------------------------------------------------------
class CanChi:
    """Tính can chi (Thập can – Địa chi) cho năm, tháng, ngày."""

    @staticmethod
    def nam(y):
        """Can chi của năm âm lịch y, ví dụ 2026 -> 'Bính Ngọ'."""
        can = ['Giáp', 'Ất', 'Bính', 'Đinh', 'Mậu', 'Kỷ', 'Canh', 'Tân', 'Nhâm', 'Qúy']
        chi = ['Tý', 'Sửu', 'Dần', 'Mão', 'Thìn', 'Tị', 'Ngọ', 'Mùi', 'Thân', 'Dậu', 'Tuất', 'Hợi']
        c1 = can[int(str(y + 6)[-1])]
        c2 = chi[(y + 8) % 12]
        return c1 + ' ' + c2

    @staticmethod
    def thang(y, m):
        """Can chi của tháng m âm lịch trong năm âm lịch y."""
        can = ['Giáp', 'Ất', 'Bính', 'Đinh', 'Mậu', 'Kỷ', 'Canh', 'Tân', 'Nhâm', 'Qúy']
        chi = ['Tý', 'Sửu', 'Dần', 'Mão', 'Thìn', 'Tị', 'Ngọ', 'Mùi', 'Thân', 'Dậu', 'Tuất', 'Hợi']
        # Tháng giêng bắt đầu từ chi Dần
        chin = chi[2::] + chi[:2]
        # Quy tắc Ngũ Hổ Độn để xác định can tháng giêng theo can năm
        start_can = {
            'Giáp': 'Bính', 'Kỷ': 'Bính',
            'Ất': 'Mậu',   'Canh': 'Mậu',
            'Bính': 'Canh', 'Tân': 'Canh',
            'Đinh': 'Nhâm', 'Nhâm': 'Nhâm',
            'Mậu': 'Giáp', 'Qúy': 'Giáp'
        }
        yrc1 = can[(y - 4) % 10]
        c0 = can.index(start_can[yrc1])
        moc1 = can[(c0 + m - 1) % 10]
        moc2 = chin[m - 1]
        return moc1 + ' ' + moc2

    @staticmethod
    def ngay(y, m, d):
        """Can chi của ngày dương lịch (y, m, d)."""
        can = ['Giáp', 'Ất', 'Bính', 'Đinh', 'Mậu', 'Kỷ', 'Canh', 'Tân', 'Nhâm', 'Qúy']
        chi = ['Tý', 'Sửu', 'Dần', 'Mão', 'Thìn', 'Tị', 'Ngọ', 'Mùi', 'Thân', 'Dậu', 'Tuất', 'Hợi']
        jdn = Date.convertDate2jdn(y, m, d)
        c1 = can[(jdn + 9) % 10]
        c2 = chi[(jdn + 1) % 12]
        return c1 + ' ' + c2


# ---------------------------------------------------------------------------
# TỐT XẤU – ngày Hoàng Đạo / Hắc Đạo, sao tốt – xấu, giờ Hoàng Đạo
# ---------------------------------------------------------------------------
class TotXau:
    """Các phép tính ngày / giờ tốt – xấu trong lịch âm."""

    @staticmethod
    def getHoangHacDao(chiDay, lunarMonth):
        """Tên sao + loại (Hoàng Đạo / Hắc Đạo) cho chi ngày + tháng âm."""
        TRUC_BANG = {
            "Thanh Long": {(1, 7): "Tý", (2, 8): "Dần", (3, 9): "Thìn", (4, 10): "Ngọ", (5, 11): "Thân", (6, 12): "Tuất"},
            "Minh Đường": {(1, 7): "Sửu", (2, 8): "Mão", (3, 9): "Tị", (4, 10): "Mùi", (5, 11): "Dậu", (6, 12): "Hợi"},
            "Thiên Hình": {(1, 7): "Dần", (2, 8): "Thìn", (3, 9): "Ngọ", (4, 10): "Thân", (5, 11): "Tuất", (6, 12): "Tý"},
            "Chu Tước":   {(1, 7): "Mão", (2, 8): "Tị", (3, 9): "Mùi", (4, 10): "Dậu", (5, 11): "Hợi", (6, 12): "Sửu"},
            "Kim Quỹ":    {(1, 7): "Thìn", (2, 8): "Ngọ", (3, 9): "Thân", (4, 10): "Tuất", (5, 11): "Tý", (6, 12): "Dần"},
            "Kim Đường":  {(1, 7): "Tị", (2, 8): "Mùi", (3, 9): "Dậu", (4, 10): "Hợi", (5, 11): "Sửu", (6, 12): "Mão"},
            "Bạch Hổ":    {(1, 7): "Ngọ", (2, 8): "Thân", (3, 9): "Tuất", (4, 10): "Tý", (5, 11): "Dần", (6, 12): "Thìn"},
            "Ngọc Đường": {(1, 7): "Mùi", (2, 8): "Dậu", (3, 9): "Hợi", (4, 10): "Sửu", (5, 11): "Mão", (6, 12): "Tị"},
            "Thiên Lao":  {(1, 7): "Thân", (2, 8): "Tuất", (3, 9): "Tý", (4, 10): "Dần", (5, 11): "Thìn", (6, 12): "Ngọ"},
            "Huyền Vũ":   {(1, 7): "Dậu", (2, 8): "Hợi", (3, 9): "Sửu", (4, 10): "Mão", (5, 11): "Tị", (6, 12): "Mùi"},
            "Tư Mệnh":    {(1, 7): "Tuất", (2, 8): "Tý", (3, 9): "Dần", (4, 10): "Thìn", (5, 11): "Ngọ", (6, 12): "Thân"},
            "Câu Trận":   {(1, 7): "Hợi", (2, 8): "Sửu", (3, 9): "Mão", (4, 10): "Tị", (5, 11): "Mùi", (6, 12): "Dậu"}
        }
        HOANG_DAO = {"Thanh Long", "Minh Đường", "Kim Quỹ", "Kim Đường", "Ngọc Đường", "Tư Mệnh"}
        for ten, bang in TRUC_BANG.items():
            for thang, chi in bang.items():
                if lunarMonth in thang and chiDay == chi:
                    loai = "Hoàng Đạo" if ten in HOANG_DAO else "Hắc Đạo"
                    return ten, loai
        return None, None

    @staticmethod
    def isTamNuong(yl, ml, dl):
        """Kiểm tra ngày âm là Tam Nương (3, 7, 13, 18, 22, 27)."""
        return dl in [3, 7, 13, 18, 22, 27]

    @staticmethod
    def isNguyetPha(yl, ml, dl):
        """Kiểm tra ngày âm có phải Nguyệt Phá."""
        # yl % 19 trong các giá trị này là gợi ý năm có thể có tháng nhuận
        isLeap = 1 if yl % 19 in [0, 3, 6, 9, 11, 14, 17] else 0
        ys, ms, ds = SolarAndLunar.convertLunar2Solar(yl, ml, dl, isLeap)
        nguyetPha = {
            1: 'Thân', 2: 'Dậu', 3: 'Tuất',
            4: 'Hợi', 5: 'Tý', 6: 'Sửu',
            7: 'Dần', 8: 'Mão', 9: 'Thìn',
            10: 'Tị', 11: 'Ngọ', 12: 'Mùi'
        }
        return CanChi.ngay(ys, ms, ds).split()[1] == nguyetPha[ml]

    @staticmethod
    def isSatChu(yl, ml, dl):
        """Kiểm tra ngày Sát Chủ."""
        isLeap = 1 if yl % 19 in [0, 3, 6, 9, 11, 14, 17] else 0
        ys, ms, ds = SolarAndLunar.convertLunar2Solar(yl, ml, dl, isLeap)
        satChu = {
            1: 'Tý', 2: 'Sửu', 3: 'Sửu',
            4: 'Tuất', 5: 'Thìn', 6: 'Thìn',
            7: 'Sửu', 8: 'Thìn', 9: 'Sửu',
            10: 'Thìn', 11: 'Mùi', 12: 'Thìn'
        }
        return CanChi.ngay(ys, ms, ds).split()[1] == satChu[ml]

    @staticmethod
    def isThoTu(yl, ml, dl):
        """Kiểm tra ngày Thọ Tử."""
        isLeap = 1 if yl % 19 in [0, 3, 6, 9, 11, 14, 17] else 0
        ys, ms, ds = SolarAndLunar.convertLunar2Solar(yl, ml, dl, isLeap)
        thoTu = {
            1: 'Tuất', 2: 'Thân', 3: 'Hợi',
            4: 'Tị', 5: 'Tý', 6: 'Ngọ',
            7: 'Sửu', 8: 'Mùi', 9: 'Dần',
            10: 'Thân', 11: 'Mão', 12: 'Dậu'
        }
        return CanChi.ngay(ys, ms, ds).split()[1] == thoTu[ml]

    @staticmethod
    def isVangVong(yl, ml, dl):
        """Kiểm tra ngày Vãng Vong."""
        isLeap = 1 if yl % 19 in [0, 3, 6, 9, 11, 14, 17] else 0
        ys, ms, ds = SolarAndLunar.convertLunar2Solar(yl, ml, dl, isLeap)
        vangVong = {
            1: 'Dần', 2: 'Tị', 3: 'Thân',
            4: 'Hợi', 5: 'Mão', 6: 'Ngọ',
            7: 'Dậu', 8: 'Tý', 9: 'Thìn',
            10: 'Mùi', 11: 'Tuất', 12: 'Sửu'
        }
        return CanChi.ngay(ys, ms, ds).split()[1] == vangVong[ml]

    @staticmethod
    def isNguyetKy(yl, ml, dl):
        """Kiểm tra ngày Nguyệt Kỵ (5, 14, 23)."""
        return dl in [5, 14, 23]

    @staticmethod
    def isDaiBai(yl, ml, dl):
        """Kiểm tra ngày Đại Bại theo can năm + can chi ngày."""
        try:
            isLeap = 1 if yl % 19 in [0, 3, 6, 9, 11, 14, 17] else 0
            ys, ms, ds = SolarAndLunar.convertLunar2Solar(yl, ml, dl, isLeap)
            canchi = CanChi.ngay(ys, ms, ds)
            if CanChi.nam(yl).split()[0] in ['Giáp', 'Kỷ']:
                dbgk = {3: 'Mậu Tuất', 7: 'Qúy Hợi', 10: 'Bính Thân', 11: 'Đinh Hợi'}
                return canchi == dbgk[ml]
            elif CanChi.nam(yl).split()[0] in ['Ất', 'Canh']:
                dbac = {4: 'Nhâm Thân', 9: 'Ất Tị'}
                return canchi == dbac[ml]
            elif CanChi.nam(yl).split()[0] in ['Bính', 'Tân']:
                dbbt = {3: 'Tân Tị', 9: 'Canh Thìn'}
                return canchi == dbbt[ml]
            elif CanChi.nam(yl).split()[0] in ['Mậu', 'Qúy']:
                return canchi == 'Kỷ Sửu'
            return False
        except KeyError:
            return False

    @staticmethod
    def getGioHoangDao(yl, ml, dl):
        """Tuple các chi giờ Hoàng Đạo trong ngày âm yl/ml/dl."""
        isLeap = 1 if yl % 19 in [0, 3, 6, 9, 11, 14, 17] else 0
        ys, ms, ds = SolarAndLunar.convertLunar2Solar(yl, ml, dl, isLeap)
        chi = CanChi.ngay(ys, ms, ds).split()[1]
        gioHoangDao = {
            ('Dần', 'Thân'):  ('Tý', 'Sửu', 'Thìn', 'Tị', 'Mùi', 'Tuất'),
            ('Mão', 'Dậu'):   ('Tý', 'Dần', 'Mão', 'Ngọ', 'Mùi', 'Dậu'),
            ('Thìn', 'Tuất'): ('Dần', 'Thìn', 'Tị', 'Thân', 'Dậu', 'Hợi'),
            ('Tị', 'Hợi'):    ('Sửu', 'Thìn', 'Ngọ', 'Mùi', 'Tuất', 'Hợi'),
            ('Tý', 'Ngọ'):    ('Tý', 'Sửu', 'Mão', 'Ngọ', 'Thân', 'Dậu'),
            ('Sửu', 'Mùi'):   ('Dần', 'Mão', 'Tị', 'Thân', 'Tuất', 'Hợi')
        }
        for k, v in gioHoangDao.items():
            if chi in k:
                return v

    @staticmethod
    def getXung(y, m, d):
        """Danh sách 5 can chi xung khắc với ngày dương (y, m, d)."""
        cch = CanChi.ngay(y, m, d)
        XUNG = {
            "Giáp Tý":   ["Giáp Tý", "Giáp Ngọ", "Canh Tý", "Canh Ngọ", "Mậu Ngọ"],
            "Ất Sửu":    ["Ất Sửu", "Ất Mùi", "Tân Sửu", "Tân Mùi", "Kỷ Mùi"],
            "Bính Dần":  ["Bính Dần", "Bính Thân", "Nhâm Dần", "Nhâm Thân", "Giáp Thân"],
            "Đinh Mão":  ["Đinh Mão", "Đinh Dậu", "Qúy Mão", "Qúy Dậu", "Ất Dậu"],
            "Mậu Thìn":  ["Mậu Thìn", "Mậu Tuất", "Giáp Thìn", "Giáp Tuất", "Canh Tuất"],
            "Kỷ Tị":     ["Kỷ Tị", "Kỷ Hợi", "Ất Tị", "Ất Hợi", "Tân Hợi"],
            "Canh Ngọ":  ["Canh Ngọ", "Canh Tý", "Bính Ngọ", "Bính Tý", "Nhâm Tý"],
            "Tân Mùi":   ["Tân Mùi", "Tân Sửu", "Đinh Mùi", "Đinh Sửu", "Qúy Sửu"],
            "Nhâm Thân": ["Nhâm Thân", "Nhâm Dần", "Mậu Thân", "Mậu Dần", "Bính Dần"],
            "Qúy Dậu":   ["Qúy Dậu", "Qúy Mão", "Kỷ Dậu", "Kỷ Mão", "Đinh Mão"],
            "Giáp Tuất": ["Giáp Tuất", "Giáp Thìn", "Canh Tuất", "Canh Thìn", "Nhâm Thìn"],
            "Ất Hợi":    ["Ất Hợi", "Ất Tị", "Tân Hợi", "Tân Tị", "Qúy Tị"],
            "Bính Tý":   ["Bính Tý", "Bính Ngọ", "Nhâm Tý", "Nhâm Ngọ", "Canh Ngọ"],
            "Đinh Sửu":  ["Đinh Sửu", "Đinh Mùi", "Qúy Sửu", "Qúy Mùi", "Tân Mùi"],
            "Mậu Dần":   ["Mậu Dần", "Mậu Thân", "Giáp Dần", "Giáp Thân", "Canh Thân"],
            "Kỷ Mão":    ["Kỷ Mão", "Kỷ Dậu", "Ất Mão", "Ất Dậu", "Tân Dậu"],
            "Canh Thìn": ["Canh Thìn", "Canh Tuất", "Bính Thìn", "Bính Tuất", "Giáp Tuất"],
            "Tân Tị":    ["Tân Tị", "Tân Hợi", "Đinh Tị", "Đinh Hợi", "Ất Hợi"],
            "Nhâm Ngọ":  ["Nhâm Ngọ", "Nhâm Tý", "Mậu Ngọ", "Mậu Tý", "Giáp Tý"],
            "Qúy Mùi":   ["Qúy Mùi", "Qúy Sửu", "Kỷ Mùi", "Kỷ Sửu", "Ất Sửu"],
            "Giáp Thân": ["Giáp Thân", "Giáp Dần", "Canh Thân", "Canh Dần", "Mậu Dần"],
            "Ất Dậu":    ["Ất Dậu", "Ất Mão", "Tân Dậu", "Tân Mão", "Kỷ Mão"],
            "Bính Tuất": ["Bính Tuất", "Bính Thìn", "Nhâm Tuất", "Nhâm Thìn", "Mậu Thìn"],
            "Đinh Hợi":  ["Đinh Hợi", "Đinh Tị", "Qúy Hợi", "Qúy Tị", "Kỷ Tị"],
            "Mậu Tý":    ["Mậu Tý", "Mậu Ngọ", "Giáp Tý", "Giáp Ngọ", "Bính Ngọ"],
            "Kỷ Sửu":    ["Kỷ Sửu", "Kỷ Mùi", "Ất Sửu", "Ất Mùi", "Đinh Mùi"],
            "Canh Dần":  ["Canh Dần", "Canh Thân", "Bính Dần", "Bính Thân", "Nhâm Thân"],
            "Tân Mão":   ["Tân Mão", "Tân Dậu", "Đinh Mão", "Đinh Dậu", "Qúy Dậu"],
            "Nhâm Thìn": ["Nhâm Thìn", "Nhâm Tuất", "Mậu Thìn", "Mậu Tuất", "Bính Tuất"],
            "Qúy Tị":    ["Qúy Tị", "Qúy Hợi", "Kỷ Tị", "Kỷ Hợi", "Đinh Hợi"],
            "Giáp Ngọ":  ["Giáp Ngọ", "Giáp Tý", "Canh Tý", "Canh Ngọ", "Mậu Tý"],
            "Ất Mùi":    ["Ất Mùi", "Ất Sửu", "Tân Sửu", "Tân Mùi", "Kỷ Sửu"],
            "Bính Thân": ["Bính Thân", "Bính Dần", "Nhâm Dần", "Nhâm Thân", "Giáp Dần"],
            "Đinh Dậu":  ["Đinh Dậu", "Đinh Mão", "Qúy Mão", "Qúy Dậu", "Ất Mão"],
            "Mậu Tuất":  ["Mậu Tuất", "Mậu Thìn", "Giáp Thìn", "Giáp Tuất", "Canh Thìn"],
            "Kỷ Hợi":    ["Kỷ Hợi", "Kỷ Tị", "Ất Tị", "Ất Hợi", "Tân Tị"],
            "Canh Tý":   ["Canh Tý", "Canh Ngọ", "Bính Ngọ", "Bính Tý", "Nhâm Ngọ"],
            "Tân Sửu":   ["Tân Sửu", "Tân Mùi", "Đinh Mùi", "Đinh Sửu", "Qúy Mùi"],
            "Nhâm Dần":  ["Nhâm Dần", "Nhâm Thân", "Mậu Thân", "Mậu Dần", "Bính Thân"],
            "Qúy Mão":   ["Qúy Mão", "Qúy Dậu", "Kỷ Dậu", "Kỷ Mão", "Đinh Dậu"],
            "Giáp Thìn": ["Giáp Thìn", "Giáp Tuất", "Canh Thìn", "Canh Tuất", "Nhâm Tuất"],
            "Ất Tị":     ["Ất Tị", "Ất Hợi", "Tân Tị", "Tân Hợi", "Qúy Hợi"],
            "Bính Ngọ":  ["Bính Ngọ", "Bính Tý", "Nhâm Ngọ", "Nhâm Tý", "Canh Tý"],
            "Đinh Mùi":  ["Đinh Mùi", "Đinh Sửu", "Qúy Mùi", "Qúy Sửu", "Tân Sửu"],
            "Mậu Thân":  ["Mậu Thân", "Mậu Dần", "Giáp Thân", "Giáp Dần", "Canh Dần"],
            "Kỷ Dậu":    ["Kỷ Dậu", "Kỷ Mão", "Ất Dậu", "Ất Mão", "Tân Mão"],
            "Canh Tuất": ["Canh Tuất", "Canh Thìn", "Bính Tuất", "Bính Thìn", "Giáp Thìn"],
            "Tân Hợi":   ["Tân Hợi", "Tân Tị", "Đinh Hợi", "Đinh Tị", "Ất Tị"],
            "Nhâm Tý":   ["Nhâm Tý", "Nhâm Ngọ", "Mậu Tý", "Mậu Ngọ", "Giáp Ngọ"],
            "Qúy Sửu":   ["Qúy Sửu", "Qúy Mùi", "Kỷ Sửu", "Kỷ Mùi", "Ất Mùi"],
            "Giáp Dần":  ["Giáp Dần", "Giáp Thân", "Canh Dần", "Canh Thân", "Mậu Thân"],
            "Ất Mão":    ["Ất Mão", "Ất Dậu", "Tân Mão", "Tân Dậu", "Kỷ Dậu"],
            "Bính Thìn": ["Bính Thìn", "Bính Tuất", "Nhâm Thìn", "Nhâm Tuất", "Mậu Tuất"],
            "Đinh Tị":   ["Đinh Tị", "Đinh Hợi", "Qúy Tị", "Qúy Hợi", "Kỷ Hợi"],
            "Mậu Ngọ":   ["Mậu Ngọ", "Mậu Tý", "Giáp Ngọ", "Giáp Tý", "Bính Tý"],
            "Kỷ Mùi":    ["Kỷ Mùi", "Kỷ Sửu", "Ất Mùi", "Ất Sửu", "Đinh Sửu"],
            "Canh Thân": ["Canh Thân", "Canh Dần", "Bính Thân", "Bính Dần", "Nhâm Dần"],
            "Tân Dậu":   ["Tân Dậu", "Tân Mão", "Đinh Dậu", "Đinh Mão", "Qúy Mão"],
            "Nhâm Tuất": ["Nhâm Tuất", "Nhâm Thìn", "Mậu Tuất", "Mậu Thìn", "Bính Thìn"],
            "Qúy Hợi":   ["Qúy Hợi", "Qúy Tị", "Kỷ Hợi", "Kỷ Tị", "Đinh Tị"]
        }
        return XUNG.get(cch, [])

    @staticmethod
    def quyHoi(h):
        """Khung giờ 24h (giờ bắt đầu, giờ kết thúc) cho chi giờ h."""
        quyHoi = {
            'Tý': (23, 1), 'Sửu': (1, 3), 'Dần': (3, 5),
            'Mão': (5, 7), 'Thìn': (7, 9), 'Tị': (9, 11),
            'Ngọ': (11, 13), 'Mùi': (13, 15), 'Thân': (15, 17),
            'Dậu': (17, 19), 'Tuất': (19, 21), 'Hợi': (21, 23)
        }
        return quyHoi.get(h, None)

    @staticmethod
    def gioAm(h):
        """Chuyển giờ 24h (0..23) sang chi giờ âm lịch."""
        if not 0 <= h <= 23:
            return None
        a = {
            'Tý': (23, 1), 'Sửu': (1, 3), 'Dần': (3, 5),
            'Mão': (5, 7), 'Thìn': (7, 9), 'Tị': (9, 11),
            'Ngọ': (11, 13), 'Mùi': (13, 15), 'Thân': (15, 17),
            'Dậu': (17, 19), 'Tuất': (19, 21), 'Hợi': (21, 23)
        }
        for b, c in a.items():
            if c[0] < c[1] and c[0] <= h < c[1]:
                return b
            if c[0] > c[1] and (h >= c[0] or h < c[1]):
                return b


# ---------------------------------------------------------------------------
# TIẾT KHÍ – 24 tiết khí trong năm
# ---------------------------------------------------------------------------
class TietKhi:
    """Tính 24 tiết khí trong năm dựa trên kinh độ Mặt Trời."""

    TERMS = {
        'Lập Xuân': 315, 'Vũ Thủy': 330, 'Kinh Trập': 345,
        'Xuân Phân': 0, 'Thanh Minh': 15, 'Cốc Vũ': 30,
        'Lập Hạ': 45, 'Tiểu Mãn': 60, 'Mang Chủng': 75,
        'Hạ Chí': 90, 'Tiểu Thử': 105, 'Đại Thử': 120,
        'Lập Thu': 135, 'Xử Thử': 150, 'Bạch Lộ': 165,
        'Thu Phân': 180, 'Hàn Lộ': 195, 'Sương Giáng': 210,
        'Lập Đông': 225, 'Tiểu Tuyết': 240, 'Đại Tuyết': 255,
        'Đông Chí': 270, 'Tiểu Hàn': 285, 'Đại Hàn': 300
    }

    TERMS_LIST = [
        ('Xuân Phân', 0), ('Thanh Minh', 15), ('Cốc Vũ', 30),
        ('Lập Hạ', 45), ('Tiểu Mãn', 60), ('Mang Chủng', 75),
        ('Hạ Chí', 90), ('Tiểu Thử', 105), ('Đại Thử', 120),
        ('Lập Thu', 135), ('Xử Thử', 150), ('Bạch Lộ', 165),
        ('Thu Phân', 180), ('Hàn Lộ', 195), ('Sương Giáng', 210),
        ('Lập Đông', 225), ('Tiểu Tuyết', 240), ('Đại Tuyết', 255),
        ('Đông Chí', 270), ('Tiểu Hàn', 285), ('Đại Hàn', 300),
        ('Lập Xuân', 315), ('Vũ Thủy', 330), ('Kinh Trập', 345)
    ]

    @staticmethod
    def jdate(y, m, d, h, mn, s, timeZone=7.0):
        """JDN dạng phân số ứng với (y, m, d, h, mn, s)."""
        jdn = Date.convertDate2jdn(y, m, d)
        return (jdn + (h - 12) / 24 + mn / 1440 + s / 86400) - timeZone / 24

    @staticmethod
    def getSunLongitude(jd):
        """Kinh độ Mặt Trời thực (độ, 0..360) tại Julian Date jd."""
        T = (jd - 2451545) / 36525
        T2 = T * T
        T3 = T2 * T
        L0 = 280.46645 + 36000.76983 * T + 0.0003032 * T2
        M = 357.52910 + 35999.05030 * T - 0.0001559 * T2 - 0.00000048 * T3
        Mr = math.radians(M)
        C = (1.914600 - 0.004817 * T - 0.000014 * T2) * math.sin(Mr)
        C += (0.01993 - 0.000101 * T) * math.sin(2 * Mr)
        C += 0.000290 * math.sin(3 * Mr)
        theta = L0 + C
        omega = math.radians(125.04 - 1934.136 * T)
        lam = theta - 0.00569 - 0.00478 * math.sin(omega)
        lam = lam - 360 * math.floor(lam / 360)
        return lam

    @staticmethod
    def getDay(year, targetLong):
        """Ngày trong năm khi kinh độ Mặt Trời đạt targetLong (độ)."""
        # Chia 4 đoạn để bắt đầu tìm gần điểm rơi của tiết khí
        if targetLong >= 315 or targetLong < 45:
            start = datetime(year, 1, 1)
        elif targetLong < 135:
            start = datetime(year, 4, 1)
        elif targetLong < 225:
            start = datetime(year, 7, 1)
        else:
            start = datetime(year, 10, 1)

        for i in range(120):
            curr = start + timedelta(days=i)
            nxt = curr + timedelta(days=1)

            jd1 = TietKhi.jdate(curr.year, curr.month, curr.day, 0, 0, 0)
            jd2 = TietKhi.jdate(nxt.year, nxt.month, nxt.day, 0, 0, 0)

            sl1 = TietKhi.getSunLongitude(jd1)
            sl2 = TietKhi.getSunLongitude(jd2)

            if sl1 <= targetLong <= sl2 or (sl1 > sl2 and (targetLong >= sl1 or targetLong <= sl2)):
                return curr

        return None

    @staticmethod
    def getExactTime(day, targetLong):
        """Tìm chính xác thời điểm (Julian Date) trong ngày khi MT đạt targetLong."""
        js = TietKhi.jdate(day.year, day.month, day.day, 0, 0, 0)
        je = TietKhi.jdate(day.year, day.month, day.day, 23, 59, 59)

        def normalize(angle):
            return angle % 360

        def isBetween(start, end, target):
            start = normalize(start)
            end = normalize(end)
            target = normalize(target)
            if start <= end:
                return start <= target <= end
            else:
                return target >= start or target <= end

        # Tìm nhị phân tới khi sai số < 0.001 độ
        for _ in range(100):
            jm = (js + je) / 2

            sls = TietKhi.getSunLongitude(js)
            slm = TietKhi.getSunLongitude(jm)

            if abs(slm - targetLong) < 0.001 or abs((slm - targetLong + 360) % 360) < 0.001:
                return jm

            if isBetween(sls, slm, targetLong):
                je = jm
            else:
                js = jm

        return (js + je) / 2

    @staticmethod
    def getTermDate(termName, year):
        """Datetime (giờ Việt Nam) bắt đầu của một tiết khí trong năm."""
        if termName not in TietKhi.TERMS:
            return None

        targetLong = TietKhi.TERMS[termName]
        day = TietKhi.getDay(year, targetLong)

        if not day:
            return None

        jdExact = TietKhi.getExactTime(day, targetLong)
        # Đổi sang giờ UTC+7
        jdUtc = jdExact + 7 / 24

        jdn = int(jdUtc + 0.5)
        fraction = (jdUtc + 0.5) - jdn

        y, m, d = Date.convertjdn2Date(jdn)

        hours = fraction * 24
        h = int(hours)
        minutes = (hours - h) * 60
        mn = int(minutes)
        return datetime(y, m, d, h, mn)

    @staticmethod
    def getTerm(y, m, d):
        """Tên tiết khí mà ngày dương lịch (y, m, d) thuộc về."""
        jd = TietKhi.jdate(y, m, d, 23, 59, 59)
        sl = TietKhi.getSunLongitude(jd)

        for i in range(len(TietKhi.TERMS_LIST)):
            name, long = TietKhi.TERMS_LIST[i]
            nextLong = TietKhi.TERMS_LIST[(i + 1) % len(TietKhi.TERMS_LIST)][1]

            if long < nextLong:
                if long <= sl < nextLong:
                    return name
            else:
                # Đoạn giáp giữa Kinh Trập và Xuân Phân
                if sl >= long or sl < nextLong:
                    return name
        return None


# ---------------------------------------------------------------------------
# VẠN SỰ – tổng hợp thông tin lịch âm – dương cho 1 ngày
# ---------------------------------------------------------------------------
class VanSu:
    """Lớp tổng hợp thông tin Vạn Sự cho một ngày."""

    @staticmethod
    def getSao(y, m, d):
        """Tên sao Nhị Thập Bát Tú ứng với ngày dương (y, m, d)."""
        saos = [
            "Giác", "Cang", "Đê", "Phòng", "Tâm", "Vĩ", "Cơ",
            "Đẩu", "Ngưu", "Nữ", "Hư", "Nguy", "Thất", "Bích",
            "Khuê", "Lâu", "Vị", "Mão", "Tất", "Chủy", "Sâm",
            "Tỉnh", "Quỷ", "Liễu", "Tinh", "Trương", "Dực", "Chẩn"
        ]
        return saos[(Date.convertDate2jdn(y, m, d) + 11) % 28]

    @staticmethod
    def getHanh(cch):
        """Hành Ngũ Hành ứng với can chi cch (vd: 'Giáp Tý' -> 'Kim')."""
        if cch in ['Giáp Tý', 'Ất Sửu', 'Nhâm Thân', 'Qúy Dậu', 'Canh Thìn', 'Tân Tị',
                   'Giáp Ngọ', 'Ất Mùi', 'Nhâm Dần', 'Qúy Mão', 'Canh Tuất', 'Tân Hợi']:
            return 'Kim'
        elif cch in ['Bính Dần', 'Đinh Mão', 'Giáp Tuất', 'Ất Hợi', 'Mậu Tý', 'Ký Sửu',
                     'Bính Thân', 'Đinh Dậu', 'Giáp Thìn', 'Ất Tị', 'Mậu Ngọ', 'Kỷ Mùi']:
            return 'Hỏa'
        elif cch in ['Mậu Thìn', 'Kỷ Tị', 'Nhâm Ngọ', 'Qúy Mùi', 'Canh Dần', 'Tân Mão',
                     'Mậu Tuất', 'Kỷ Hợi', 'Nhâm Tý', 'Qủy Sửu', 'Canh Thân', 'Tân Dậu']:
            return 'Mộc'
        elif cch in ['Canh Ngọ', 'Tân Mùi', 'Mậu Dần', 'Kỷ Mão', 'Bính Tuất', 'Đinh Hợi',
                     'Canh Tý', 'Tân Sửu', 'Mậu Thân', 'Kỷ Dậu', 'Bính Thìn', 'Đinh Tị']:
            return 'Thổ'
        elif cch in ['Bính Tý', 'Đinh Sửu', 'Giáp Thân', 'Ất Dậu', 'Nhâm Thìn', 'Qúy Tị',
                     'Bính Ngọ', 'Đinh Mùi', 'Giáp Dần', 'Ất Mão', 'Nhâm Tuất', 'Qúy Hợi']:
            return 'Thủy'

    @staticmethod
    def get28_Hanh(y, m, d):
        """Hành + sao cho ngày dương lịch (y, m, d)."""
        a = CanChi.ngay(y, m, d)
        return {
            'hành': VanSu.getHanh(a),
            'sao': VanSu.getSao(y, m, d),
        }

    @staticmethod
    def getInfo(y, m, d, SorL='s'):
        """Chuỗi tổng hợp thông tin Vạn Sự cho 1 ngày.

        SorL = 's' nếu (y, m, d) là dương lịch, 'l' nếu là âm lịch.
        """
        if SorL == 's':
            thu = Date.dayWeek(y, m, d)
            yl, ml, dl, isLeap = SolarAndLunar.convertSolar2Lunar(y, m, d)
            ccng = CanChi.ngay(y, m, d)
            canng = ccng.split()[1]
            ccth = CanChi.thang(yl, ml)
            ccnm = CanChi.nam(yl)
            hanh = VanSu.get28_Hanh(y, m, d)['hành']
            sao = VanSu.get28_Hanh(y, m, d)['sao']
            hodhad = TotXau.getHoangHacDao(canng, ml)
            tamnuong = TotXau.isTamNuong(yl, ml, dl)
            nguyetpha = TotXau.isNguyetPha(yl, ml, dl)
            satchu = TotXau.isSatChu(yl, ml, dl)
            thotu = TotXau.isThoTu(yl, ml, dl)
            vangvong = TotXau.isVangVong(yl, ml, dl)
            nguyetky = TotXau.isNguyetKy(yl, ml, dl)
            daibai = TotXau.isDaiBai(yl, ml, dl)
            ghd = TotXau.getGioHoangDao(yl, ml, dl)
            tx = TotXau.getXung(y, m, d)
            tiet = TietKhi.getTerm(y, m, d)
            # Ghép giờ Hoàng Đạo kèm khung giờ 24h
            gd = []
            for i in range(len(ghd)):
                sth = TotXau.quyHoi(ghd[i])
                gd.append(ghd[i] + f' ({sth[0]}h - {sth[1]}h)')

            labels = [
                ('Tam Nương', tamnuong),
                ('Nguyệt Phá', nguyetpha),
                ('Sát Chủ', satchu),
                ('Thọ Tử', thotu),
                ('Vãng Vong', vangvong),
                ('Nguyệt Kỵ', nguyetky),
                ('Đại Bại', daibai),
            ]
            a = ' - '.join(name for name, ok in labels if ok)
            # Gắn hậu tố '(tháng nhuận)' nếu ngày âm rơi vào tháng nhuận
            leap_mark = ' (tháng nhuận)' if isLeap else ''
            inf = (
                f'{d}/{m}/{y}\t{thu.upper()}\tNgày {dl}/{ml}/{yl} ÂL{leap_mark}\n'
                f'Ngày {ccng} - Tháng {ccth} - Năm {ccnm}\n'
                f'Hành {hanh} - Sao {sao}\n'
                f'{" ".join(hodhad)}\n'
                f'{a}\n'
                f'- Giờ tốt: {", ".join(gd)}\n'
                f'- Tuổi xung: {", ".join(tx)}\n'
            )
            td = TietKhi.getTermDate(tiet, y)
            if td and td.day == d and td.month == m:
                gio = TotXau.gioAm(td.hour)
                return inf + f'- BẮT ĐẦU TIẾT: {tiet} lúc {td.hour:02}h{td.minute:02} (giờ {gio})'
            else:
                return inf + f'- Thuộc tiết {tiet}.'

        elif SorL == 'l':
            yl, ml, dl = y, m, d
            isLeap = 1 if yl % 19 in [0, 3, 6, 9, 11, 14, 17] else 0
            ys, ms, ds = SolarAndLunar.convertLunar2Solar(yl, ml, dl, isLeap)
            thu = Date.dayWeek(ys, ms, ds)
            ccng = CanChi.ngay(ys, ms, ds)
            ccth = CanChi.thang(yl, ml)
            ccnm = CanChi.nam(yl)
            canng = ccng.split()[1]
            hanh = VanSu.get28_Hanh(ys, ms, ds)['hành']
            sao = VanSu.get28_Hanh(ys, ms, ds)['sao']
            hodhad = TotXau.getHoangHacDao(canng, ml)
            tamnuong = TotXau.isTamNuong(yl, ml, dl)
            nguyetpha = TotXau.isNguyetPha(yl, ml, dl)
            satchu = TotXau.isSatChu(yl, ml, dl)
            thotu = TotXau.isThoTu(yl, ml, dl)
            vangvong = TotXau.isVangVong(yl, ml, dl)
            nguyetky = TotXau.isNguyetKy(yl, ml, dl)
            daibai = TotXau.isDaiBai(yl, ml, dl)
            ghd = TotXau.getGioHoangDao(yl, ml, dl)
            tx = TotXau.getXung(ys, ms, ds)
            tiet = TietKhi.getTerm(ys, ms, ds)
            gd = []
            for i in range(len(ghd)):
                sth = TotXau.quyHoi(ghd[i])
                gd.append(ghd[i] + f' ({sth[0]}h - {sth[1]}h)')

            labels = [
                ('Tam Nương', tamnuong),
                ('Nguyệt Phá', nguyetpha),
                ('Sát Chủ', satchu),
                ('Thọ Tử', thotu),
                ('Vãng Vong', vangvong),
                ('Nguyệt Kỵ', nguyetky),
                ('Đại Bại', daibai),
            ]
            a = ' - '.join(name for name, ok in labels if ok)
            # Gắn hậu tố '(tháng nhuận)' nếu ngày âm rơi vào tháng nhuận
            leap_mark = ' (tháng nhuận)' if isLeap else ''
            inf = (
                f'{ds}/{ms}/{ys}\t{thu.upper()}\tNgày {dl}/{ml}/{yl} ÂL{leap_mark}\n'
                f'Ngày {ccng} - Tháng {ccth} - Năm {ccnm}\n'
                f'Hành {hanh} - Sao {sao}\n'
                f'{" ".join(hodhad)}\n'
                f'{a}\n'
                f'- Giờ tốt: {", ".join(gd)}\n'
                f'- Tuổi xung: {", ".join(tx)}\n'
            )
            td = TietKhi.getTermDate(tiet, ys)
            if td and td.day == ds and td.month == ms:
                gio = TotXau.gioAm(td.hour)
                return inf + f'- BẮT ĐẦU TIẾT: {tiet} lúc {td.hour:02}h{td.minute:02} (giờ {gio})'
            else:
                return inf + f'- Thuộc tiết {tiet}.'


# ===========================================================================
# ADAPTER – API tương thích với thư viện lunar-python
#
# Cung cấp 3 lớp Solar, Lunar, LunarYear mô phỏng cách lunar-python được dùng
# trong dự án (Solar.fromYmd, Lunar.fromYmd, LunarYear.fromYear.getLeapMonth).
# Quy ước:
# - Lunar.getMonth() trả về giá trị âm (vd: -6) nếu là tháng nhuận, dương nếu
#   không nhuận – giống lunar-python.
# - Lunar.fromYmd(year, signed_month, day): signed_month < 0 nghĩa là tháng nhuận.
# ===========================================================================


def _leap_month_from_offset(leap_off: int) -> int:
    """Đổi offset tháng nhuận (1..13) thành số tháng âm lịch (1..12).

    Tại offset i thì tháng (không nhuận) sẽ là (i + 10) mod 12 + 1
    (do offset 0 là tháng 11). Tháng nhuận lặp lại tháng ngay trước nó.
    """
    return (leap_off + 9) % 12 + 1


class LunarYear:
    """Đại diện 1 năm âm lịch, có hàm getLeapMonth() như lunar-python."""

    def __init__(self, lunar_year: int):
        self._year = lunar_year

    @staticmethod
    def fromYear(lunar_year: int) -> "LunarYear":
        """Khởi tạo LunarYear từ số năm âm lịch."""
        return LunarYear(lunar_year)

    def getYear(self) -> int:
        return self._year

    def getLeapMonth(self) -> int:
        """Số tháng nhuận của năm âm lịch, 0 nếu năm không có tháng nhuận."""
        y = self._year

        # Khoảng 1: tháng 11(Y-1) -> tháng 11(Y), chứa tháng 12(Y-1) và 1..10(Y).
        a11_a = SolarAndLunar.getLunarMonth11(y - 1)
        b11_a = SolarAndLunar.getLunarMonth11(y)
        if b11_a - a11_a > 365:
            leap_off = SolarAndLunar.getLeapMonthOffset(a11_a)
            m = _leap_month_from_offset(leap_off)
            # Hiếm: nhuận 11/12 trong khoảng này thực ra thuộc năm Y-1.
            if m not in (11, 12):
                return m

        # Khoảng 2: tháng 11(Y) -> tháng 11(Y+1). Chỉ nhuận 11/12 thuộc năm Y.
        a11_b = SolarAndLunar.getLunarMonth11(y)
        b11_b = SolarAndLunar.getLunarMonth11(y + 1)
        if b11_b - a11_b > 365:
            leap_off = SolarAndLunar.getLeapMonthOffset(a11_b)
            m = _leap_month_from_offset(leap_off)
            if m in (11, 12):
                return m

        return 0


class Lunar:
    """Đại diện 1 ngày âm lịch, tương thích lunar-python."""

    def __init__(self, year: int, month: int, day: int, is_leap: bool = False):
        # month luôn dương (1..12). is_leap = True nếu là tháng nhuận.
        self._year = year
        self._month = month
        self._day = day
        self._is_leap = is_leap

    @staticmethod
    def fromYmd(year: int, signed_month: int, day: int) -> "Lunar":
        """Khởi tạo từ (year, signed_month, day).

        Quy ước signed_month < 0 nghĩa là tháng nhuận (giống lunar-python).
        """
        is_leap = signed_month < 0
        month = abs(signed_month)
        if not (1 <= month <= 12):
            raise ValueError(f"Invalid lunar month: {signed_month}")
        if not (1 <= day <= 30):
            raise ValueError(f"Invalid lunar day: {day}")
        # Kiểm tra tháng nhuận hợp lệ với năm
        if is_leap:
            leap = LunarYear.fromYear(year).getLeapMonth()
            if leap != month:
                raise ValueError(
                    f"wrong lunar year {year} month {month} leap"
                )
        return Lunar(year, month, day, is_leap)

    def getYear(self) -> int:
        return self._year

    def getMonth(self) -> int:
        """Tháng âm. Trả về số âm nếu là tháng nhuận (giống lunar-python)."""
        return -self._month if self._is_leap else self._month

    def getDay(self) -> int:
        return self._day

    def isLeap(self) -> bool:
        return self._is_leap

    def getSolar(self) -> "Solar":
        """Đổi ngày âm hiện tại sang đối tượng Solar dương lịch."""
        ys, ms, ds = SolarAndLunar.convertLunar2Solar(
            self._year, self._month, self._day, 1 if self._is_leap else 0
        )
        if (ys, ms, ds) == (0, 0, 0):
            raise ValueError(
                f"Invalid lunar date: {self._year}/"
                f"{'-' if self._is_leap else ''}{self._month}/{self._day}"
            )
        return Solar(ys, ms, ds)


class Solar:
    """Đại diện 1 ngày dương lịch, tương thích lunar-python."""

    def __init__(self, year: int, month: int, day: int):
        self._year = year
        self._month = month
        self._day = day

    @staticmethod
    def fromYmd(year: int, month: int, day: int) -> "Solar":
        """Khởi tạo từ (year, month, day) dương lịch."""
        # Kiểm tra hợp lệ thông qua datetime.date để bắt mọi ngoại lệ.
        date(year, month, day)
        return Solar(year, month, day)

    def getYear(self) -> int:
        return self._year

    def getMonth(self) -> int:
        return self._month

    def getDay(self) -> int:
        return self._day

    def getLunar(self) -> Lunar:
        """Đổi ngày dương hiện tại sang đối tượng Lunar âm lịch."""
        yl, ml, dl, leap = SolarAndLunar.convertSolar2Lunar(
            self._year, self._month, self._day
        )
        return Lunar(yl, ml, dl, is_leap=bool(leap))
