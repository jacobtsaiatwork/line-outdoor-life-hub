# -*- coding: utf-8 -*-
"""
🔗 外出生活三合一超級選單 - 核心跨模組意圖路由器 (Hub Router)
負責：
1. 三合一自然語言意圖辨識 (`classify_intent`)：
   - 抽美食 / 依剩餘熱量推薦 (`food_draw`)
   - 找洗手間 / 廁所分類過濾 (`toilet_search`)
   - 熱量儀表板 / 喝水打卡 / 清空紀錄 / TDEE 設定 (`calorie_dashboard`, `water_log`, `clear_records`, `tdee_setup`)
   - 食物文字 AI 熱量與營養素估算 (`calorie_estimate`)
   - 歡迎與使用說明 (`help`)
2. Postback 跨模組連動閉環處理 (`handle_postback_action`)：
   - `action=eat_this`：從美食推薦卡一鍵寫入今日飲食紀錄，並回傳最新今日熱量儀表板
   - `action=draw_food`：查詢今日剩餘熱量額度，智慧抽取不爆卡美食
   - `action=switch_gps_mode&target=food|toilet`：讀取資料庫記憶之最新 GPS 座標，免重傳定位直接切換找附近美食或附近洗手間！
3. GPS Location 訊息處理 (`handle_location_event`)：
   - 自動儲存使用者最新經緯度至資料庫，並依當前模式回傳美食或洗手間輪播卡片
"""
import re
import urllib.parse
from typing import Dict, Any, Optional, Tuple

import database as db
from food_module import draw_smart_food, search_food_by_keyword, get_nearby_restaurants
from calorie_module import parse_tdee_command, calorie_ai_service
from toilet_module import find_nearby_toilets
from flex_builder import (
    build_smart_food_flex,
    build_food_analysis_flex,
    build_daily_dashboard_flex,
    build_nearby_food_carousel,
    build_nearby_toilet_carousel,
    build_hub_welcome_flex,
)


def classify_intent(text: str) -> Tuple[str, Dict[str, Any]]:
    """
    解析使用者輸入文字，精準歸類至三合一超級選單對應模組意圖
    回傳 (intent_name, metadata)
    """
    clean = text.strip()
    lower = clean.lower()

    # 1. 說明 / 歡迎指引
    if lower in ["說明", "使用說明", "功能", "help", "幫助", "功能說明", "選單", "三合一", "hi", "hello", "你好", "您好"]:
        return ("help", {})

    # 2. 今日熱量儀表板
    if clean in ["今日飲食", "今日熱量", "今天吃多少", "儀表板", "熱量儀表板", "查看紀錄", "今日紀錄", "剩餘熱量"]:
        return ("calorie_dashboard", {})

    # 3. 喝水打卡
    if "喝水" in clean:
        m = re.search(r"\d+", clean)
        ml = int(m.group(0)) if m else 300
        return ("water_log", {"amount_ml": ml})

    # 4. 清空今日紀錄
    if clean in ["清空今日紀錄", "重置今日", "清空紀錄"]:
        return ("clear_records", {})

    # 5. TDEE / 瘦身計劃設定
    if any(k in lower for k in ["瘦身計劃", "瘦身計畫", "tdee", "個人檔案"]):
        return ("tdee_setup", {"raw_text": clean})

    # 6. 洗手間 / 廁所急救搜尋
    toilet_keywords = ["廁所", "洗手間", "化妝室", "尿急", "便所", "公廁", "無障礙洗手間", "尿布檯", "找廁所", "附近洗手間"]
    if any(k in clean for k in toilet_keywords):
        filter_type = None
        if "無障礙" in clean or "輪椅" in clean:
            filter_type = "wheelchair"
        elif "尿布" in clean or "親子" in clean:
            filter_type = "diaper"
        elif "24" in clean or "半夜" in clean:
            filter_type = "24h"
        elif "加油站" in clean or "中油" in clean:
            filter_type = "gas_station"
        elif "麥當勞" in clean or "速食" in clean:
            filter_type = "fastfood"
        return ("toilet_search", {"filter_type": filter_type})

    # 7. 美食盲盒抽籤（含「依剩餘熱量抽美食」、「吃什麼」、「隨便」）
    food_draw_triggers = [
        "吃什麼", "隨便", "抽美食", "美食盲盒", "依剩餘熱量抽美食",
        "幫我依今日剩餘熱量抽不爆卡美食", "換一個", "再抽一次", "推薦美食", "今天吃什麼", "午餐吃什麼", "晚餐吃什麼"
    ]
    if any(k in clean for k in food_draw_triggers):
        strict = "剩餘熱量" in clean or "不爆卡" in clean or "低卡" in clean
        return ("food_draw", {"strict": strict})

    # 8. 用記憶定位找附近美食
    if clean in ["附近美食", "周邊餐廳", "附近餐廳", "找附近美食"]:
        return ("nearby_food", {})

    # 9. 預設歸類為：自然語言飲食熱量估算（例如「一碗滷肉飯加燙青菜」）
    return ("calorie_estimate", {"query": clean})


def route_text_message(user_id: str, text: str) -> Dict[str, Any]:
    """
    處理文字訊息並回傳結構化回應資料：
    {
        "intent": str,
        "text_message": Optional[str],
        "flex_alt_text": Optional[str],
        "flex_contents": Optional[Dict[str, Any]],
        "data": Dict[str, Any]
    }
    """
    intent, meta = classify_intent(text)
    cal_info = db.get_remaining_calories(user_id)
    remaining_cal = cal_info["remaining_calories"]
    loc_info = db.get_user_location(user_id)
    u_lat = loc_info["lat"] if loc_info else None
    u_lng = loc_info["lng"] if loc_info else None

    if intent == "help":
        flex = build_hub_welcome_flex(remaining_calories=remaining_cal)
        return {
            "intent": intent,
            "text_message": None,
            "flex_alt_text": "🧭 外出生活三合一超級選單指南",
            "flex_contents": flex,
            "data": cal_info
        }

    if intent == "calorie_dashboard":
        profile = db.get_user_profile(user_id)
        summary = db.get_today_summary(user_id)
        flex = build_daily_dashboard_flex(profile, summary)
        return {
            "intent": intent,
            "text_message": None,
            "flex_alt_text": "📊 今日熱量與營養儀表板",
            "flex_contents": flex,
            "data": summary
        }

    if intent == "water_log":
        ml = meta.get("amount_ml", 300)
        total_water = db.add_water(user_id, ml)
        return {
            "intent": intent,
            "text_message": f"💧 喝水打卡成功！本次補充 +{ml}ml，今日累計飲水：{total_water} / 2000 ml 💦",
            "flex_alt_text": None,
            "flex_contents": None,
            "data": {"added_ml": ml, "total_water_ml": total_water}
        }

    if intent == "clear_records":
        db.clear_today_records(user_id)
        return {
            "intent": intent,
            "text_message": "🗑️ 今日飲食與喝水紀錄已清空重置！隨時可以重新開始記錄喔 🥗",
            "flex_alt_text": None,
            "flex_contents": None,
            "data": {}
        }

    if intent == "tdee_setup":
        parsed = parse_tdee_command(meta["raw_text"])
        if not parsed:
            return {
                "intent": intent,
                "text_message": (
                    "📋 【設定個人 TDEE 與每日熱量目標】\n"
                    "請輸入格式：「瘦身計劃 性別 身高 體重 年齡 活動量」\n"
                    "👉 範例：「瘦身計劃 男 175 72 28 中度」或「瘦身計劃 女 160 52 26 輕度」"
                ),
                "flex_alt_text": None,
                "flex_contents": None,
                "data": {}
            }
        db.save_user_profile(
            user_id=user_id,
            gender=parsed["gender"],
            height=parsed["height"],
            weight=parsed["weight"],
            age=parsed["age"],
            activity=parsed["activity"],
            bmr=parsed["bmr"],
            tdee=parsed["tdee"],
            target_calories=parsed["target_calories"]
        )
        profile = db.get_user_profile(user_id)
        summary = db.get_today_summary(user_id)
        flex = build_daily_dashboard_flex(profile, summary)
        msg = (
            f"🎉 個人 TDEE 檔案設定完成！\n"
            f"🔥 基礎代謝 (BMR)：{parsed['bmr']} kcal｜每日總消耗 (TDEE)：{parsed['tdee']} kcal\n"
            f"🎯 每日目標攝取：{parsed['target_calories']} kcal (已自動連動至美食抽籤額度！)"
        )
        return {
            "intent": intent,
            "text_message": msg,
            "flex_alt_text": "📊 個人熱量目標與今日儀表板",
            "flex_contents": flex,
            "data": parsed
        }

    if intent == "food_draw":
        db.set_user_gps_mode(user_id, "food")
        food = draw_smart_food(
            remaining_calories=remaining_cal,
            strict_calorie_filter=meta.get("strict", False)
        )
        flex = build_smart_food_flex(food, remaining_calories=remaining_cal, user_lat=u_lat, user_lng=u_lng)
        status_note = (
            f"🥗 已根據您今日剩餘熱量額度 ({remaining_cal} kcal)，為您智慧抽出不爆卡美食：【{food['name']} ({food['calories']} kcal)】！"
            if food.get("calorie_matched")
            else f"🎲 為您抽出人氣料理：【{food['name']} ({food['calories']} kcal)】（今日剩餘額度：{remaining_cal} kcal）"
        )
        return {
            "intent": intent,
            "text_message": status_note,
            "flex_alt_text": f"🍽️ 智慧美食推薦：{food['name']} ({food['calories']} kcal)",
            "flex_contents": flex,
            "data": food
        }

    if intent == "nearby_food":
        db.set_user_gps_mode(user_id, "food")
        lat = u_lat if u_lat is not None else 25.0330
        lng = u_lng if u_lng is not None else 121.5654
        restaurants = get_nearby_restaurants(lat, lng)
        carousel = build_nearby_food_carousel(restaurants, lat, lng, remaining_calories=remaining_cal)
        prefix = "📍 使用您記憶中的最新 GPS 定位" if loc_info else "📍 預設示範座標（傳送位置訊息可定位您身邊）"
        return {
            "intent": intent,
            "text_message": f"{prefix}，為您推薦周邊人氣餐廳！下方可直接「🔥 一鍵記熱量」或「🔄 改找附近洗手間」：",
            "flex_alt_text": "🍽️ 周邊美食餐廳雷達",
            "flex_contents": carousel,
            "data": {"restaurants": restaurants, "lat": lat, "lng": lng}
        }

    if intent == "toilet_search":
        db.set_user_gps_mode(user_id, "toilet")
        filter_type = meta.get("filter_type")
        lat = u_lat if u_lat is not None else 25.0330
        lng = u_lng if u_lng is not None else 121.5654
        toilets = find_nearby_toilets(lat, lng, filter_type=filter_type)
        carousel = build_nearby_toilet_carousel(toilets, lat, lng)
        prefix = "🚻 使用您記憶中的最新 GPS 座標" if loc_info else "🚻 先為您顯示周邊友善洗手間（點擊下方『📍 傳送我的位置』可精準定位身邊據點）"
        return {
            "intent": intent,
            "text_message": f"{prefix}，已找到 {len(toilets)} 處友善洗手間（含 24H/無障礙/尿布檯標示）！",
            "flex_alt_text": "🚻 附近救急友善洗手間雷達",
            "flex_contents": carousel,
            "data": {"toilets": toilets, "lat": lat, "lng": lng}
        }

    # intent == "calorie_estimate"
    analysis = calorie_ai_service.analyze_food(text=meta["query"])
    flex = build_food_analysis_flex(
        food_name=analysis.get("food_name", meta["query"]),
        calories=int(analysis.get("calories", 500)),
        protein_g=int(analysis.get("protein_g", 20)),
        carbs_g=int(analysis.get("carbs_g", 60)),
        fat_g=int(analysis.get("fat_g", 18)),
        health_rating=analysis.get("health_rating", "AI 營養估算"),
        advice=analysis.get("advice", ""),
        items=analysis.get("items", [])
    )
    return {
        "intent": "calorie_estimate",
        "text_message": None,
        "flex_alt_text": f"🔥 AI 熱量估算：{analysis.get('food_name', meta['query'])} ({analysis.get('calories', 500)} kcal)",
        "flex_contents": flex,
        "data": analysis
    }


def handle_postback_action(user_id: str, postback_data: str) -> Dict[str, Any]:
    """
    處理 LINE Postback 事件，實踐三大跨模組無縫閉環：
    1. `action=eat_this&food_name=...&calories=...&protein=...&carbs=...&fat=...`
       -> 抽中美食一鍵記入今日熱量，立即回傳更新後的今日熱量儀表板！
    2. `action=draw_food&exclude=...&strict=...`
       -> 依今日剩餘熱量額度再抽一個不重複美食！
    3. `action=switch_gps_mode&target=toilet|food`
       -> 免重傳 GPS，直接讀取資料庫記憶座標在「附近美食」與「附近洗手間」間秒速切換！
    """
    params = dict(urllib.parse.parse_qsl(postback_data))
    action = params.get("action", "")

    if action == "eat_this":
        food_name = urllib.parse.unquote(params.get("food_name", "精選餐點"))
        calories = int(params.get("calories", 500))
        protein_g = int(params.get("protein", 25))
        carbs_g = int(params.get("carbs", 60))
        fat_g = int(params.get("fat", 18))

        db.add_meal_record(
            user_id=user_id,
            meal_name=food_name,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            meal_type="三合一美食連動"
        )
        profile = db.get_user_profile(user_id)
        summary = db.get_today_summary(user_id)
        flex = build_daily_dashboard_flex(profile, summary)
        remaining = summary["remaining_calories"]

        return {
            "action": "eat_this",
            "text_message": (
                f"✅ 已一鍵記入今日飲食：【{food_name}】(+{calories} kcal｜蛋白質 {protein_g}g)\n"
                f"📊 今日已攝取 {summary['total_calories']} kcal，剩餘可用額度：{remaining} kcal！"
            ),
            "flex_alt_text": "📊 更新後今日熱量儀表板",
            "flex_contents": flex,
            "data": summary
        }

    if action == "draw_food":
        exclude_name = urllib.parse.unquote(params.get("exclude", "")) or None
        strict = params.get("strict") == "1"
        cal_info = db.get_remaining_calories(user_id)
        remaining_cal = cal_info["remaining_calories"]
        loc_info = db.get_user_location(user_id)
        u_lat = loc_info["lat"] if loc_info else None
        u_lng = loc_info["lng"] if loc_info else None

        food = draw_smart_food(
            remaining_calories=remaining_cal,
            exclude_name=exclude_name,
            strict_calorie_filter=strict
        )
        flex = build_smart_food_flex(food, remaining_calories=remaining_cal, user_lat=u_lat, user_lng=u_lng)
        return {
            "action": "draw_food",
            "text_message": f"🥗 根據您今日剩餘額度 ({remaining_cal} kcal)，為您推薦：【{food['name']} ({food['calories']} kcal)】！",
            "flex_alt_text": f"🍽️ 智慧美食推薦：{food['name']}",
            "flex_contents": flex,
            "data": food
        }

    if action == "switch_gps_mode":
        target = params.get("target", "toilet")
        db.set_user_gps_mode(user_id, target)
        loc_info = db.get_user_location(user_id)
        lat = loc_info["lat"] if loc_info else 25.0330
        lng = loc_info["lng"] if loc_info else 121.5654
        has_saved_gps = loc_info is not None

        if target == "toilet":
            toilets = find_nearby_toilets(lat, lng)
            carousel = build_nearby_toilet_carousel(toilets, lat, lng)
            msg = (
                f"🔄 已直接套用您記憶中的 GPS 座標 ({lat:.4f}, {lng:.4f})，免重傳位置！為您列出附近 {len(toilets)} 處友善洗手間："
                if has_saved_gps
                else "🚻 為您開啟救急友善洗手間雷達！（點擊下方『📍 傳送我的位置』可自動記憶您的座標）"
            )
            return {
                "action": "switch_gps_mode",
                "target": "toilet",
                "text_message": msg,
                "flex_alt_text": "🚻 附近友善洗手間雷達",
                "flex_contents": carousel,
                "data": {"toilets": toilets, "lat": lat, "lng": lng, "reused_gps": has_saved_gps}
            }
        else:
            cal_info = db.get_remaining_calories(user_id)
            restaurants = get_nearby_restaurants(lat, lng)
            carousel = build_nearby_food_carousel(restaurants, lat, lng, remaining_calories=cal_info["remaining_calories"])
            msg = (
                f"🔄 已直接套用您記憶中的 GPS 座標 ({lat:.4f}, {lng:.4f})，免重傳位置！為您列出附近人氣餐廳："
                if has_saved_gps
                else "🍽️ 為您開啟周邊美食雷達！（點擊下方『📍 傳送我的位置』可自動記憶您的座標）"
            )
            return {
                "action": "switch_gps_mode",
                "target": "food",
                "text_message": msg,
                "flex_alt_text": "🍽️ 附近美食餐廳雷達",
                "flex_contents": carousel,
                "data": {"restaurants": restaurants, "lat": lat, "lng": lng, "reused_gps": has_saved_gps}
            }

    return route_text_message(user_id, "功能說明")


def handle_location_event(
    user_id: str,
    lat: float,
    lng: float,
    address: str = "",
    override_mode: Optional[str] = None
) -> Dict[str, Any]:
    """
    【連動 3：GPS 定位一次傳送，雙模組智慧共用】
    當使用者傳送 LINE Location Message 時：
    1. 自動將最新經緯度寫入資料庫 `users` 表記憶
    2. 依據使用者當前 `gps_mode` ('food' 或 'toilet') 回傳周邊餐廳或友善洗手間輪播卡片
    3. 卡片底部提供一鍵切換另一模組按鈕，完全不需再次傳送位置！
    """
    profile = db.get_user_profile(user_id)
    current_mode = override_mode or (profile.get("gps_mode") if profile else "food") or "food"
    db.save_user_location(user_id, lat, lng, address=address, gps_mode=current_mode)

    if current_mode == "toilet":
        toilets = find_nearby_toilets(lat, lng)
        carousel = build_nearby_toilet_carousel(toilets, lat, lng)
        return {
            "mode": "toilet",
            "text_message": f"📍 已記憶您的位置 ({address or '當前座標'})！為您找到附近 {len(toilets)} 處友善洗手間（點卡片下方可免重傳定位改找附近美食）：",
            "flex_alt_text": "🚻 附近救急友善洗手間雷達",
            "flex_contents": carousel,
            "data": {"toilets": toilets, "lat": lat, "lng": lng}
        }
    else:
        cal_info = db.get_remaining_calories(user_id)
        restaurants = get_nearby_restaurants(lat, lng)
        carousel = build_nearby_food_carousel(restaurants, lat, lng, remaining_calories=cal_info["remaining_calories"])
        return {
            "mode": "food",
            "text_message": f"📍 已記憶您的位置 ({address or '當前座標'})！為您推薦周邊餐廳（點卡片下方可一鍵記熱量，或免重傳定位改找附近洗手間）：",
            "flex_alt_text": "🍽️ 附近美食餐廳雷達",
            "flex_contents": carousel,
            "data": {"restaurants": restaurants, "lat": lat, "lng": lng}
        }
