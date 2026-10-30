# -*- coding: utf-8 -*-
"""
🧪 外出生活三合一超級選單 LINE Bot (Outdoor Life 3-in-1 Super Hub) 完整單元與整合測試套件
測試涵蓋：
1. 三合一自然語言意圖路由 (`classify_intent` & `route_text_message`)
2. 【連動 1】依今日剩餘熱量額度智慧篩選不爆卡美食 (`draw_smart_food` & `get_remaining_calories`)
3. 【連動 2】抽中美食後「🔥 一鍵記入今日熱量 (`action=eat_this`)」閉環與儀表板即時更新
4. 【連動 3】GPS 座標記憶與「🔄 用同一個定位改找附近美食 / 附近洗手間 (`action=switch_gps_mode`)」雙向無縫切換
5. 自然語言複合餐點熱量估算（如「一碗滷肉飯加燙青菜」）与 TDEE 個人檔案設定
6. LINE 多頁籤圖文選單 (`setup_rich_menu.py`) Rich Menu Alias 配置與 Pillow 圖片自動繪製
7. Flex Message 結構驗證與 FastAPI Webhook / REST API 端點驗證
"""
import os
import unittest
from fastapi.testclient import TestClient

# 使用獨立測試 SQLite 資料庫，避免影響正式資料
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_outdoor_hub.db")
os.environ["OUTDOOR_HUB_DB_PATH"] = TEST_DB_PATH
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

import database as db
from food_module import draw_smart_food, get_nearby_restaurants
from calorie_module import calculate_bmr_tdee, parse_tdee_command, calorie_ai_service
from toilet_module import find_nearby_toilets
from hub_router import classify_intent, route_text_message, handle_postback_action, handle_location_event
from setup_rich_menu import (
    ALIAS_FOOD,
    ALIAS_CALORIE,
    ALIAS_TOILET,
    build_all_rich_menu_payloads,
    generate_rich_menu_images,
)
from main import app


class TestOutdoorLifeHub(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
        db.init_db()
        self.client = TestClient(app)
        self.user_id = "test_user_001"

    def tearDown(self):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except Exception:
                pass

    def test_01_intent_classification(self):
        """測試三合一自然語言意圖路由精準度"""
        self.assertEqual(classify_intent("吃什麼")[0], "food_draw")
        self.assertEqual(classify_intent("隨便")[0], "food_draw")
        self.assertEqual(classify_intent("🥗 依剩餘熱量抽美食")[0], "food_draw")
        self.assertEqual(classify_intent("今日熱量")[0], "calorie_dashboard")
        self.assertEqual(classify_intent("喝水 500")[0], "water_log")
        self.assertEqual(classify_intent("瘦身計劃 男 175 70 28 中度")[0], "tdee_setup")
        self.assertEqual(classify_intent("附近哪裡有廁所")[0], "toilet_search")
        self.assertEqual(classify_intent("找無障礙洗手間")[0], "toilet_search")
        self.assertEqual(classify_intent("一碗滷肉飯加燙青菜")[0], "calorie_estimate")
        self.assertEqual(classify_intent("功能說明")[0], "help")

    def test_02_smart_food_filtering_by_remaining_calories(self):
        """測試【連動 1：從熱量剩餘額度智慧抽美食】"""
        # 設定使用者今日目標 2000 kcal，已攝取 1350 kcal -> 剩餘 650 kcal
        db.save_user_profile(self.user_id, "男", 175, 70, 28, "輕度", 1650, 2260, 2000)
        db.add_meal_record(self.user_id, "早午餐拼盤", 1350, 45, 120, 50)

        cal_info = db.get_remaining_calories(self.user_id)
        self.assertEqual(cal_info["target_calories"], 2000)
        self.assertEqual(cal_info["consumed_calories"], 1350)
        self.assertEqual(cal_info["remaining_calories"], 650)

        # 執行智慧抽籤 10 次，每次抽出的料理熱量都必須 <= 650 kcal (不爆卡！)
        for _ in range(10):
            food = draw_smart_food(remaining_calories=cal_info["remaining_calories"], strict_calorie_filter=True)
            self.assertLessEqual(food["calories"], 650)
            self.assertTrue(food["calorie_matched"])

    def test_03_eat_this_one_click_calorie_logging_loop(self):
        """測試【連動 2：抽中美食後一鍵記入今日熱量閉環 (`action=eat_this`)】"""
        # 1. 先抽美食
        draw_res = route_text_message(self.user_id, "🥗 依剩餘熱量抽美食")
        self.assertEqual(draw_res["intent"], "food_draw")
        bubble = draw_res["flex_contents"]
        self.assertEqual(bubble["type"], "bubble")

        # 驗證卡片底部包含三顆跨模組連動按鈕：一鍵記熱量、再抽一次、找附近洗手間
        footer_str = str(bubble["footer"])
        self.assertIn("action=eat_this", footer_str)
        self.assertIn("action=draw_food", footer_str)
        self.assertIn("action=switch_gps_mode&target=toilet", footer_str)

        # 2. 模擬點擊「🔥 就決定吃這個！一鍵記入今日熱量」Postback
        postback_data = "action=eat_this&food_name=舒肥嫩雞胸健康水煮餐&calories=420&protein=38&carbs=45&fat=9"
        pb_res = handle_postback_action(self.user_id, postback_data)
        self.assertEqual(pb_res["action"], "eat_this")
        self.assertEqual(pb_res["data"]["total_calories"], 420)
        self.assertEqual(pb_res["data"]["total_protein"], 38)
        self.assertEqual(pb_res["data"]["remaining_calories"], 2000 - 420)
        self.assertIn("舒肥嫩雞胸健康水煮餐", str(pb_res["flex_contents"]))

    def test_04_gps_memory_and_dual_module_switching(self):
        """測試【連動 3：GPS 定位一次傳送，美食/洗手間雙模組智慧共用與免重傳切換】"""
        lat, lng = 25.0339, 121.5645
        # 1. 使用者傳送一次 LINE Location 訊息（預設美食模式）
        loc_res = handle_location_event(self.user_id, lat, lng, address="台北市信義區台北101", override_mode="food")
        self.assertEqual(loc_res["mode"], "food")
        self.assertEqual(loc_res["flex_contents"]["type"], "carousel")
        self.assertIn("action=switch_gps_mode&target=toilet", str(loc_res["flex_contents"]))

        # 確認資料庫已自動記憶最新 GPS 座標
        saved_loc = db.get_user_location(self.user_id)
        self.assertIsNotNone(saved_loc)
        self.assertAlmostEqual(saved_loc["lat"], lat, places=4)
        self.assertAlmostEqual(saved_loc["lng"], lng, places=4)

        # 2. 點擊「🔄 用同一個定位改找附近洗手間」Postback（不需重傳座標）
        sw_toilet = handle_postback_action(self.user_id, "action=switch_gps_mode&target=toilet")
        self.assertEqual(sw_toilet["target"], "toilet")
        self.assertTrue(sw_toilet["data"]["reused_gps"])
        self.assertGreaterEqual(len(sw_toilet["data"]["toilets"]), 3)
        self.assertIn("action=switch_gps_mode&target=food", str(sw_toilet["flex_contents"]))

        # 3. 再點擊「🔄 用同一個定位改找附近美食」切回餐廳雷達
        sw_food = handle_postback_action(self.user_id, "action=switch_gps_mode&target=food")
        self.assertEqual(sw_food["target"], "food")
        self.assertTrue(sw_food["data"]["reused_gps"])
        self.assertGreaterEqual(len(sw_food["data"]["restaurants"]), 3)

    def test_05_natural_language_calorie_and_tdee(self):
        """測試自然語言飲食熱量估算與 TDEE 個人檔案設定"""
        res = route_text_message(self.user_id, "一碗滷肉飯加燙青菜")
        self.assertEqual(res["intent"], "calorie_estimate")
        # 滷肉飯 (450) + 燙青菜 (90) = 540 kcal
        self.assertEqual(res["data"]["calories"], 540)

        tdee_res = route_text_message(self.user_id, "瘦身計劃 女 162 54 26 輕度")
        self.assertEqual(tdee_res["intent"], "tdee_setup")
        self.assertIn("target_calories", tdee_res["data"])

    def test_06_rich_menu_alias_and_image_generation(self):
        """測試三頁籤 Rich Menu Alias 架構與 Pillow 圖檔生成"""
        payloads = build_all_rich_menu_payloads()
        self.assertIn(ALIAS_FOOD, payloads)
        self.assertIn(ALIAS_CALORIE, payloads)
        self.assertIn(ALIAS_TOILET, payloads)

        for alias_key, p in payloads.items():
            self.assertEqual(p["size"]["width"], 2500)
            self.assertEqual(p["size"]["height"], 1686)
            # 前 3 個熱區必須是 richmenuswitch 頂部頁籤切換動作
            switch_actions = [a for a in p["areas"] if a["action"]["type"] == "richmenuswitch"]
            self.assertEqual(len(switch_actions), 3)

        img_paths = generate_rich_menu_images()
        for alias_key, path in img_paths.items():
            self.assertTrue(os.path.exists(path), f"Missing generated image: {path}")
            self.assertGreater(os.path.getsize(path), 10000)

    def test_07_fastapi_endpoints(self):
        """測試 FastAPI 健康檢查、Rich Menu 配置與模擬端點"""
        r_health = self.client.get("/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.json()["status"], "ok")

        r_rm = self.client.get("/api/rich-menu-config")
        self.assertEqual(r_rm.status_code, 200)
        self.assertEqual(len(r_rm.json()["aliases"]), 3)

        r_sim = self.client.post("/api/simulate/text", json={"user_id": self.user_id, "text": "吃什麼"})
        self.assertEqual(r_sim.status_code, 200)
        self.assertEqual(r_sim.json()["intent"], "food_draw")

        r_webhook = self.client.post("/callback", content="{}")
        self.assertEqual(r_webhook.status_code, 200)

    def test_08_bill_split_and_dining_poll(self):
        """測試外出 AA 制快速分帳與多人聚餐 3 選 1 投票閉環"""
        # 1. 快速分帳
        split_res = route_text_message(self.user_id, "分帳 1200 4人 10%")
        self.assertEqual(split_res["intent"], "bill_split")
        self.assertEqual(split_res["data"]["total"], 1200.0)
        self.assertEqual(split_res["data"]["heads"], 4)
        self.assertIn("💳", split_res["text_message"])
        self.assertIn("每人應付", str(split_res["flex_contents"]))

        # 2. 發起聚餐 3 選 1 投票
        poll_res = route_text_message(self.user_id, "吃什麼投票")
        self.assertEqual(poll_res["intent"], "food_poll")
        poll_id = poll_res["data"]["poll_id"]
        self.assertEqual(len(poll_res["data"]["options"]), 3)

        # 3. 投給第 1 個選項
        vote_pb = f"action=vote_poll&poll_id={poll_id}&idx=0"
        vote_res = handle_postback_action(self.user_id, vote_pb)
        self.assertEqual(vote_res["action"], "vote_poll")
        self.assertEqual(vote_res["data"]["votes"][self.user_id], 0)

        # 4. 查看即時開票
        view_pb = f"action=view_poll&poll_id={poll_id}"
        view_res = handle_postback_action(self.user_id, view_pb)
        self.assertEqual(view_res["action"], "view_poll")
        self.assertEqual(len(view_res["data"]["votes"]), 1)

    def test_09_moenv_public_toilet_and_weather(self):
        """測試環境部列管特優公廁資料庫整合與天氣防護建議"""
        from weather_module import get_outdoor_weather
        from toilet_module import find_nearby_toilets, haversine_distance

        # 1. 測試台北車站座標 (25.0463, 121.5175)，應命中環境部特優公廁
        toilets = find_nearby_toilets(25.0463, 121.5175, radius_meters=1500)
        self.assertGreaterEqual(len(toilets), 1)
        first_t = toilets[0]
        self.assertTrue(any("特優" in tag for tag in first_t.get("tags", [])))

        # 2. 測試天氣防護模組
        weather = get_outdoor_weather(25.0463, 121.5175)
        self.assertIn("temperature", weather)
        self.assertIn("condition", weather)
        self.assertIn("advisory", weather)

        # 3. 測試位置事件是否包含天氣提醒
        loc_res = handle_location_event(self.user_id, 25.0463, 121.5175, "台北車站")
        self.assertIn("weather", loc_res["data"])
        self.assertIn(weather["condition"], loc_res["text_message"])

    def test_10_liff_endpoints_and_audio_nutrition(self):
        """測試 LIFF 網頁端點、REST API 與語音多模態分析"""
        # 1. LIFF 頁面載入
        r_dash = self.client.get("/liff/dashboard")
        self.assertEqual(r_dash.status_code, 200)
        self.assertIn("Chart.js", r_dash.text)

        r_map = self.client.get("/liff/map")
        self.assertEqual(r_map.status_code, 200)
        self.assertIn("Leaflet", r_map.text)

        # 2. LIFF Profile API
        r_prof = self.client.get(f"/api/liff/profile?user_id={self.user_id}")
        self.assertEqual(r_prof.status_code, 200)
        self.assertIn("target_calories", r_prof.json())

        # 3. LIFF Records API
        r_rec = self.client.get(f"/api/liff/records?user_id={self.user_id}")
        self.assertEqual(r_rec.status_code, 200)
        self.assertEqual(len(r_rec.json()["history"]), 7)

        # 4. LIFF Nearby Map Points API
        r_nearby = self.client.get("/api/liff/nearby?lat=25.0463&lng=121.5175")
        self.assertEqual(r_nearby.status_code, 200)
        self.assertGreater(len(r_nearby.json()["items"]), 5)

        # 5. 語音營養辨識分析回退
        audio_res = calorie_ai_service.analyze_audio(audio_bytes=b"fake_audio_bytes")
        self.assertTrue(audio_res["is_food"])
        self.assertIn("calories", audio_res)
        self.assertGreater(audio_res["calories"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

