# -*- coding: utf-8 -*-
"""
🌤️ 外出天氣與環境防護模組 (Weather & Outdoor Advisory Module)
功能：
1. 依據 GPS 座標取得即時氣溫、降雨機率、紫外線指數 (UV Index) 與天氣狀態
2. 整合免 API Key 之高品質開放氣象服務 (Open-Meteo)，具備高可用度備援
3. 產生外出生活建議（雨天室內推薦、防曬提醒、多喝水警報）
"""
import math
from typing import Dict, Any, Optional
import requests


def get_outdoor_weather(lat: float, lng: float) -> Dict[str, Any]:
    """
    依 GPS 座標查詢即時天氣與降雨機率
    """
    default_weather = {
        "temperature": 26.0,
        "precipitation_probability": 20,
        "uv_index": 5.0,
        "weather_code": 1,
        "condition": "晴時多雲",
        "icon": "🌤️",
        "is_raining": False,
        "advisory": "天氣舒適宜人，適合外出散步與享用美食！"
    }

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat:.4f}&longitude={lng:.4f}&"
            f"current=temperature_2m,precipitation,weather_code&"
            f"hourly=precipitation_probability,uv_index&"
            f"timezone=auto&forecast_days=1"
        )
        resp = requests.get(url, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            curr = data.get("current", {})
            temp = float(curr.get("temperature_2m", 26.0))
            code = int(curr.get("weather_code", 0))

            hourly = data.get("hourly", {})
            pop_list = hourly.get("precipitation_probability", [20])
            uv_list = hourly.get("uv_index", [5.0])

            pop = int(pop_list[0]) if pop_list else 20
            uv = float(uv_list[0]) if uv_list else 5.0

            # 依據 WMO Weather code 解析天氣
            is_raining = False
            condition = "晴朗"
            icon = "☀️"
            advisory = "陽光和煦，是個外出用餐的好天氣！"

            if code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]:
                is_raining = True
                condition = "陰雨連綿"
                icon = "🌧️"
                advisory = "⚠️ 外出降雨機率偏高！已為您優先推薦室內商場、地下街與捷運共構美食與洗手間！"
            elif code in [1, 2, 3]:
                condition = "多雲時晴"
                icon = "⛅"
                if pop >= 50:
                    is_raining = True
                    advisory = "☁️ 天空陰暗有短暫雨風險，外出請攜帶雨具備用。"
                elif uv >= 7.0:
                    advisory = f"☀️ 紫外線指數高達 {uv:.1f}，外出請做好防曬並記得補充水分！"
                else:
                    advisory = "涼爽微風，適合在附近探索新餐廳！"
            elif uv >= 8.0:
                condition = "烈日晴空"
                icon = "☀️"
                advisory = f"🔥 紫外線過量 ({uv:.1f})，建議避開豔陽走騎樓或室內商場，並適時打卡喝水！"

            return {
                "temperature": round(temp, 1),
                "precipitation_probability": max(0, min(100, pop)),
                "uv_index": round(uv, 1),
                "weather_code": code,
                "condition": condition,
                "icon": icon,
                "is_raining": is_raining,
                "advisory": advisory
            }
    except Exception:
        pass

    return default_weather
