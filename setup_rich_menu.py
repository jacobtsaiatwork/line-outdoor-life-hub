# -*- coding: utf-8 -*-
"""
📱 LINE 多頁籤圖文選單切換系統 (Rich Menu Alias Multi-Tab Switcher)
完整實作 LINE Messaging API 的 Rich Menu Alias (`richmenuswitch` action) 三合一多頁籤切換架構：
- Tab 1 (`richmenu-alias-food`)：🍽️ 美食盲盒與周邊餐廳
- Tab 2 (`richmenu-alias-calorie`)：🔥 AI 熱量管家與營養追蹤
- Tab 3 (`richmenu-alias-toilet`)：🚻 救急友善洗手間雷達

同時支援使用 Pillow 自動繪製 3 張不同主題配色、含頂部頁籤切換列的高質感 2500x1686 圖文選單 PNG 圖檔，
並提供一鍵上傳、建立 Alias 與綁定全體預設選單的自動化部署流程！
"""
import os
from typing import Dict, Any, List, Optional
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()

ALIAS_FOOD = "richmenu-alias-food"
ALIAS_CALORIE = "richmenu-alias-calorie"
ALIAS_TOILET = "richmenu-alias-toilet"

TAB_HEIGHT = 286
GRID_Y1 = 286
GRID_Y2 = 986
GRID_H = 700


def _build_top_tab_areas(active_alias: str) -> List[Dict[str, Any]]:
    """
    建立頂部 3 顆頁籤切換熱區 (2500 x 286)：
    使用 LINE 官方 `richmenuswitch` action 搭配 `richMenuAliasId` 達成毫秒級無縫頁籤切換！
    """
    tabs = [
        {"alias": ALIAS_FOOD, "x": 0, "w": 833, "data": "tab=food"},
        {"alias": ALIAS_CALORIE, "x": 833, "w": 834, "data": "tab=calorie"},
        {"alias": ALIAS_TOILET, "x": 1667, "w": 833, "data": "tab=toilet"},
    ]
    areas = []
    for t in tabs:
        areas.append({
            "bounds": {"x": t["x"], "y": 0, "width": t["w"], "height": TAB_HEIGHT},
            "action": {
                "type": "richmenuswitch",
                "richMenuAliasId": t["alias"],
                "data": f"action=switch_tab&{t['data']}&from={active_alias}"
            }
        })
    return areas


def build_all_rich_menu_payloads() -> Dict[str, Dict[str, Any]]:
    """回傳三大主題頁籤的完整 LINE Rich Menu JSON Payload"""
    food_areas = _build_top_tab_areas(ALIAS_FOOD) + [
        # Row 1
        {
            "bounds": {"x": 0, "y": GRID_Y1, "width": 833, "height": GRID_H},
            "action": {
                "type": "postback",
                "label": "依剩餘熱量抽美食",
                "data": "action=draw_food&strict=1",
                "displayText": "🥗 幫我依今日剩餘熱量抽不爆卡美食！"
            }
        },
        {
            "bounds": {"x": 833, "y": GRID_Y1, "width": 834, "height": GRID_H},
            "action": {
                "type": "postback",
                "label": "隨機美食盲盒",
                "data": "action=draw_food",
                "displayText": "🎲 隨便抽一個人氣美食盲盒！"
            }
        },
        {
            "bounds": {"x": 1667, "y": GRID_Y1, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "傳定位找周邊餐廳",
                "text": "找附近餐廳"
            }
        },
        # Row 2
        {
            "bounds": {"x": 0, "y": GRID_Y2, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "低卡健康輕食",
                "text": "低卡吃什麼"
            }
        },
        {
            "bounds": {"x": 833, "y": GRID_Y2, "width": 834, "height": GRID_H},
            "action": {
                "type": "postback",
                "label": "改找附近洗手間",
                "data": "action=switch_gps_mode&target=toilet",
                "displayText": "🔄 用同一個定位改找附近洗手間！"
            }
        },
        {
            "bounds": {"x": 1667, "y": GRID_Y2, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "三合一功能說明",
                "text": "功能說明"
            }
        }
    ]

    calorie_areas = _build_top_tab_areas(ALIAS_CALORIE) + [
        # Row 1
        {
            "bounds": {"x": 0, "y": GRID_Y1, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "拍照AI算熱量",
                "text": "拍照AI算熱量"
            }
        },
        {
            "bounds": {"x": 833, "y": GRID_Y1, "width": 834, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "今日熱量儀表板",
                "text": "今日熱量"
            }
        },
        {
            "bounds": {"x": 1667, "y": GRID_Y1, "width": 833, "height": GRID_H},
            "action": {
                "type": "postback",
                "label": "剩餘額度配餐",
                "data": "action=draw_food&strict=1",
                "displayText": "🥗 依今日剩餘熱量幫我配餐！"
            }
        },
        # Row 2
        {
            "bounds": {"x": 0, "y": GRID_Y2, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "喝水打卡+300ml",
                "text": "喝水 300"
            }
        },
        {
            "bounds": {"x": 833, "y": GRID_Y2, "width": 834, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "TDEE個人檔案",
                "text": "瘦身計劃"
            }
        },
        {
            "bounds": {"x": 1667, "y": GRID_Y2, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "清空今日紀錄",
                "text": "清空今日紀錄"
            }
        }
    ]

    toilet_areas = _build_top_tab_areas(ALIAS_TOILET) + [
        # Row 1
        {
            "bounds": {"x": 0, "y": GRID_Y1, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "傳定位找最近廁所",
                "text": "找最近廁所"
            }
        },
        {
            "bounds": {"x": 833, "y": GRID_Y1, "width": 834, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "24H超商與加油站",
                "text": "找 24H 廁所"
            }
        },
        {
            "bounds": {"x": 1667, "y": GRID_Y1, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "無障礙友善廁所",
                "text": "找無障礙洗手間"
            }
        },
        # Row 2
        {
            "bounds": {"x": 0, "y": GRID_Y2, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "親子尿布檯據點",
                "text": "找親子尿布檯廁所"
            }
        },
        {
            "bounds": {"x": 833, "y": GRID_Y2, "width": 834, "height": GRID_H},
            "action": {
                "type": "postback",
                "label": "改找附近美食",
                "data": "action=switch_gps_mode&target=food",
                "displayText": "🔄 用同一個定位改找附近美食！"
            }
        },
        {
            "bounds": {"x": 1667, "y": GRID_Y2, "width": 833, "height": GRID_H},
            "action": {
                "type": "message",
                "label": "三合一功能說明",
                "text": "功能說明"
            }
        }
    ]

    return {
        ALIAS_FOOD: {
            "size": {"width": 2500, "height": 1686},
            "selected": True,
            "name": "outdoor_hub_tab_food_v1",
            "chatBarText": "🧭 外出生活選單",
            "areas": food_areas
        },
        ALIAS_CALORIE: {
            "size": {"width": 2500, "height": 1686},
            "selected": True,
            "name": "outdoor_hub_tab_calorie_v1",
            "chatBarText": "🧭 外出生活選單",
            "areas": calorie_areas
        },
        ALIAS_TOILET: {
            "size": {"width": 2500, "height": 1686},
            "selected": True,
            "name": "outdoor_hub_tab_toilet_v1",
            "chatBarText": "🧭 外出生活選單",
            "areas": toilet_areas
        }
    }


def _load_cjk_font(size: int) -> ImageFont.FreeTypeFont:
    """載入支援繁體中文的字型，若無則回退預設字型"""
    font_candidates = [
        r"C:\Windows\Fonts\msjhbd.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\kaiu.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def generate_rich_menu_images(output_dir: Optional[str] = None) -> Dict[str, str]:
    """
    使用 Pillow 自動繪製 3 張 2500x1686 高質感多頁籤圖文選單圖片：
    - `static/richmenu_food.png` (暖橘美食主題)
    - `static/richmenu_calorie.png` (翠綠熱量管家主題)
    - `static/richmenu_toilet.png` (靛藍救急洗手間主題)
    """
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(output_dir, exist_ok=True)

    themes = {
        ALIAS_FOOD: {
            "filename": "richmenu_food.png",
            "active_index": 0,
            "bg_color": (30, 20, 15),
            "accent_color": (234, 88, 12),      # #EA580C
            "card_bg": (55, 35, 25),
            "card_border": (249, 115, 22),
            "cards": [
                ("🥗 依剩餘熱量抽美食", "連動熱量額度不爆卡"),
                ("🎲 隨機美食盲盒", "一鍵終結選擇困難"),
                ("📍 傳定位找周邊餐廳", "Google人氣名店導航"),
                ("🥑 低卡健康輕食", "高蛋白減脂首選"),
                ("🔄 改找附近洗手間", "免重傳GPS一鍵切換"),
                ("🧭 三合一功能說明", "跨模組全流程教學"),
            ]
        },
        ALIAS_CALORIE: {
            "filename": "richmenu_calorie.png",
            "active_index": 1,
            "bg_color": (12, 32, 24),
            "accent_color": (16, 185, 129),     # #10B981
            "card_bg": (20, 52, 40),
            "card_border": (52, 211, 153),
            "cards": [
                ("📸 拍照 AI 算熱量", "Gemini Vision秒速辨識"),
                ("📊 今日熱量儀表板", "掌握攝取與剩餘額度"),
                ("🥗 依剩餘額度配餐", "智慧推薦下一餐"),
                ("💧 喝水打卡 +300ml", "每日2000ml代謝追蹤"),
                ("🎯 TDEE 個人檔案", "BMR與減脂赤字設定"),
                ("🗑️ 清空今日紀錄", "一鍵重置今日飲食"),
            ]
        },
        ALIAS_TOILET: {
            "filename": "richmenu_toilet.png",
            "active_index": 2,
            "bg_color": (15, 23, 42),
            "accent_color": (2, 132, 199),      # #0284C7
            "card_bg": (30, 41, 59),
            "card_border": (56, 189, 248),
            "cards": [
                ("📍 傳定位找最近廁所", "秒搜周邊友善外借據點"),
                ("🏪 24H 超商與加油站", "半夜救急100%開放"),
                ("♿ 無障礙友善洗手間", "圖書館/醫院/捷運公廁"),
                ("🍼 親子尿布檯據點", "百貨商場/文教場館"),
                ("🔄 改找附近美食", "免重傳GPS一鍵切換"),
                ("🧭 三合一功能說明", "跨模組全流程教學"),
            ]
        }
    }

    tab_titles = [
        "🍽️ 美食盲盒與餐廳",
        "🔥 AI 熱量管家",
        "🚻 救急洗手間雷達"
    ]

    font_tab = _load_cjk_font(54)
    font_title = _load_cjk_font(62)
    font_sub = _load_cjk_font(38)

    generated_paths: Dict[str, str] = {}

    for alias_id, cfg in themes.items():
        img = Image.new("RGB", (2500, 1686), cfg["bg_color"])
        draw = ImageDraw.Draw(img)

        # 1. 繪製頂部 3 顆頁籤切換列 (2500 x 286)
        tab_widths = [(0, 833), (833, 1667), (1667, 2500)]
        for idx, (x1, x2) in enumerate(tab_widths):
            is_active = (idx == cfg["active_index"])
            tab_fill = cfg["accent_color"] if is_active else (40, 48, 60)
            draw.rectangle([x1 + 8, 12, x2 - 8, TAB_HEIGHT - 6], fill=tab_fill, outline=(255, 255, 255) if is_active else (90, 100, 120), width=4)
            text = tab_titles[idx]
            cx = (x1 + x2) // 2
            cy = TAB_HEIGHT // 2
            draw.text((cx, cy), text, font=font_tab, fill=(255, 255, 255) if is_active else (190, 200, 215), anchor="mm")

        # 2. 繪製下方 2x3 功能格 (y: 286 ~ 1686)
        col_bounds = [(0, 833), (833, 1667), (1667, 2500)]
        row_bounds = [(GRID_Y1, GRID_Y2), (GRID_Y2, 1686)]

        card_idx = 0
        for r_idx, (y1, y2) in enumerate(row_bounds):
            for c_idx, (x1, x2) in enumerate(col_bounds):
                pad = 22
                bx1, by1, bx2, by2 = x1 + pad, y1 + pad, x2 - pad, y2 - pad
                draw.rounded_rectangle(
                    [bx1, by1, bx2, by2],
                    radius=36,
                    fill=cfg["card_bg"],
                    outline=cfg["card_border"],
                    width=5
                )
                title_text, sub_text = cfg["cards"][card_idx]
                cx = (bx1 + bx2) // 2
                cy = (by1 + by2) // 2
                draw.text((cx, cy - 45), title_text, font=font_title, fill=(255, 255, 255), anchor="mm")
                draw.text((cx, cy + 55), sub_text, font=font_sub, fill=(210, 225, 240), anchor="mm")
                card_idx += 1

        out_path = os.path.join(output_dir, cfg["filename"])
        img.save(out_path, format="PNG")
        generated_paths[alias_id] = out_path

    return generated_paths


def deploy_multi_tab_rich_menus(access_token: Optional[str] = None) -> Dict[str, Any]:
    """
    一鍵自動繪圖、建立 3 張 Rich Menu、上傳 PNG 圖檔、設定 Rich Menu Alias 並將 Tab 1 設為全員預設選單
    """
    token = (access_token or LINE_CHANNEL_ACCESS_TOKEN).strip()
    image_paths = generate_rich_menu_images()
    payloads = build_all_rich_menu_payloads()

    if not token:
        return {
            "status": "local_only",
            "message": "已成功生成 3 張多頁籤 Rich Menu 圖檔與 Payload（未設定 LINE_CHANNEL_ACCESS_TOKEN，略過遠端 API 上傳）",
            "images": image_paths,
            "aliases": list(payloads.keys())
        }

    headers_json = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    headers_png = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/png"
    }

    created_menus: Dict[str, str] = {}

    for alias_id, payload in payloads.items():
        # 1. 建立 Rich Menu
        res = requests.post("https://api.line.me/v2/bot/richmenu", headers=headers_json, json=payload, timeout=10)
        if res.status_code != 200:
            raise RuntimeError(f"建立 Rich Menu ({alias_id}) 失敗: {res.status_code} {res.text}")
        rich_menu_id = res.json()["richMenuId"]
        created_menus[alias_id] = rich_menu_id

        # 2. 上傳對應 PNG 圖檔
        with open(image_paths[alias_id], "rb") as f:
            img_bytes = f.read()
        up_res = requests.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers=headers_png,
            data=img_bytes,
            timeout=20
        )
        if up_res.status_code != 200:
            raise RuntimeError(f"上傳 Rich Menu 圖檔 ({alias_id}) 失敗: {up_res.status_code} {up_res.text}")

        # 3. 建立或更新 Rich Menu Alias
        alias_payload = {"richMenuAliasId": alias_id, "richMenuId": rich_menu_id}
        al_res = requests.post("https://api.line.me/v2/bot/richmenu/alias", headers=headers_json, json=alias_payload, timeout=10)
        if al_res.status_code == 400:
            # 若 Alias 已存在則呼叫更新端點
            requests.post(
                f"https://api.line.me/v2/bot/richmenu/alias/{alias_id}",
                headers=headers_json,
                json={"richMenuId": rich_menu_id},
                timeout=10
            )

    # 4. 將 Tab 1 (美食盲盒) 設為全體預設 Rich Menu
    default_id = created_menus[ALIAS_FOOD]
    requests.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{default_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10
    )

    return {
        "status": "deployed",
        "rich_menus": created_menus,
        "images": image_paths
    }


if __name__ == "__main__":
    result = deploy_multi_tab_rich_menus()
    print(result)
