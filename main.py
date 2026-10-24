# -*- coding: utf-8 -*-
"""
🧭 美食抽籤 × 熱量控制 × 附近洗手間『外出生活三合一超級選單』LINE 官方帳號
(Outdoor Life 3-in-1 Super Hub LINE Bot)
FastAPI 主程式與 LINE Webhook / REST API 整合端點
"""
import os
import json
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# LINE Bot SDK v3
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
    QuickReply,
    QuickReplyItem,
    LocationAction,
    MessageAction,
    PostbackAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    PostbackEvent,
    FollowEvent,
    TextMessageContent,
    LocationMessageContent,
    ImageMessageContent,
)

import database as db
from calorie_module import calorie_ai_service
from flex_builder import build_food_analysis_flex, build_hub_welcome_flex
from hub_router import route_text_message, handle_postback_action, handle_location_event
from setup_rich_menu import build_all_rich_menu_payloads, generate_rich_menu_images

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "").strip()

configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN or "dummy_token")
parser = WebhookParser(LINE_CHANNEL_SECRET or "dummy_secret")

app = FastAPI(
    title="🧭 外出生活三合一超級選單 LINE Bot (美食抽籤 × 熱量控制 × 附近洗手間)",
    version="1.0.0",
    description="深度整合美食盲盒、AI 熱量管家與救急友善洗手間雷達的三合一超級選單 LINE 官方帳號"
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def get_hub_quick_reply() -> QuickReply:
    """提供三合一跨模組快捷按鈕列"""
    return QuickReply(
        items=[
            QuickReplyItem(
                action=PostbackAction(
                    label="🥗 依剩餘熱量抽美食",
                    data="action=draw_food&strict=1",
                    display_text="🥗 幫我依今日剩餘熱量抽不爆卡美食！"
                )
            ),
            QuickReplyItem(action=LocationAction(label="📍 傳送定位(雙模組共用)")),
            QuickReplyItem(action=MessageAction(label="📊 今日熱量儀表板", text="今日熱量")),
            QuickReplyItem(
                action=PostbackAction(
                    label="🚻 找附近友善洗手間",
                    data="action=switch_gps_mode&target=toilet",
                    display_text="🚻 找附近的友善洗手間！"
                )
            ),
            QuickReplyItem(
                action=PostbackAction(
                    label="🍽️ 找附近人氣餐廳",
                    data="action=switch_gps_mode&target=food",
                    display_text="🍽️ 找附近的人氣餐廳！"
                )
            ),
            QuickReplyItem(action=MessageAction(label="💧 喝水 +300ml", text="喝水 300")),
            QuickReplyItem(action=MessageAction(label="🧭 三合一說明", text="功能說明")),
        ]
    )


class TextSimRequest(BaseModel):
    user_id: str = "demo_user"
    text: str


class PostbackSimRequest(BaseModel):
    user_id: str = "demo_user"
    data: str


class LocationSimRequest(BaseModel):
    user_id: str = "demo_user"
    latitude: float = 25.0330
    longitude: float = 121.5654
    address: str = "台北市信義區"
    mode: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def index_page():
    html_file = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>🧭 外出生活三合一超級選單 LINE Bot 運作中</h1>"


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "line-outdoor-life-hub",
        "modules": ["food_lottery", "calorie_manager", "toilet_radar", "rich_menu_alias_tabs"]
    }


@app.get("/api/rich-menu-config")
def api_rich_menu_config():
    """檢視三頁籤 Rich Menu Alias 設定與生成圖檔"""
    images = generate_rich_menu_images()
    payloads = build_all_rich_menu_payloads()
    return {
        "aliases": list(payloads.keys()),
        "images": {k: os.path.basename(v) for k, v in images.items()},
        "payloads": payloads
    }


@app.post("/api/simulate/text")
def api_simulate_text(req: TextSimRequest):
    """Web 互動預覽與自動化測試端點：模擬文字訊息路由"""
    return route_text_message(req.user_id, req.text)


@app.post("/api/simulate/postback")
def api_simulate_postback(req: PostbackSimRequest):
    """Web 互動預覽與自動化測試端點：模擬跨模組 Postback 閉環"""
    return handle_postback_action(req.user_id, req.data)


@app.post("/api/simulate/location")
def api_simulate_location(req: LocationSimRequest):
    """Web 互動預覽與自動化測試端點：模擬傳送 GPS 座標"""
    return handle_location_event(
        user_id=req.user_id,
        lat=req.latitude,
        lng=req.longitude,
        address=req.address,
        override_mode=req.mode
    )


@app.post("/callback")
@app.post("/callback/")
@app.post("/webhook")
async def line_webhook(request: Request):
    """LINE Messaging API Webhook 入口"""
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_str = body.decode("utf-8")

    if not signature:
        return JSONResponse(content={"status": "ok", "message": "Verify check without signature"})

    try:
        events = parser.parse(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if not LINE_CHANNEL_ACCESS_TOKEN:
        return JSONResponse(content={"status": "ok", "message": "Processed in dry-run mode"})

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_blob_api = MessagingApiBlob(api_client)

        for event in events:
            user_id = getattr(event.source, "user_id", "default_user")
            reply_token = getattr(event, "reply_token", None)
            if not reply_token:
                continue

            # 1. 加入好友事件
            if isinstance(event, FollowEvent):
                cal_info = db.get_remaining_calories(user_id)
                flex = build_hub_welcome_flex(remaining_calories=cal_info["remaining_calories"])
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[
                            FlexMessage(
                                alt_text="🧭 歡迎加入外出生活三合一超級選單！",
                                contents=FlexContainer.from_json(json.dumps(flex)),
                                quick_reply=get_hub_quick_reply()
                            )
                        ]
                    )
                )
                continue

            # 2. Postback 跨模組連動事件 (一鍵記熱量 / 再抽一次 / GPS 雙模組切換)
            if isinstance(event, PostbackEvent):
                data_str = event.postback.data or ""
                if data_str.startswith("action=switch_tab"):
                    # RichMenuSwitch 頁籤切換自動處理，若有附帶定位模式則同步更新
                    if "tab=toilet" in data_str:
                        db.set_user_gps_mode(user_id, "toilet")
                    elif "tab=food" in data_str:
                        db.set_user_gps_mode(user_id, "food")
                    continue

                res = handle_postback_action(user_id, data_str)
                reply_msgs = []
                if res.get("text_message"):
                    reply_msgs.append(TextMessage(text=res["text_message"], quick_reply=get_hub_quick_reply()))
                if res.get("flex_contents"):
                    reply_msgs.append(
                        FlexMessage(
                            alt_text=res.get("flex_alt_text", "🧭 外出生活三合一通知"),
                            contents=FlexContainer.from_json(json.dumps(res["flex_contents"])),
                            quick_reply=get_hub_quick_reply()
                        )
                    )
                if reply_msgs:
                    line_bot_api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=reply_msgs[:5]))
                continue

            # 3. 一般訊息事件 (文字 / 定位 / 圖片)
            if isinstance(event, MessageEvent):
                # A. 文字訊息
                if isinstance(event.message, TextMessageContent):
                    res = route_text_message(user_id, event.message.text)
                    reply_msgs = []
                    if res.get("text_message"):
                        reply_msgs.append(TextMessage(text=res["text_message"], quick_reply=get_hub_quick_reply()))
                    if res.get("flex_contents"):
                        reply_msgs.append(
                            FlexMessage(
                                alt_text=res.get("flex_alt_text", "🧭 外出生活三合一卡片"),
                                contents=FlexContainer.from_json(json.dumps(res["flex_contents"])),
                                quick_reply=get_hub_quick_reply()
                            )
                        )
                    if reply_msgs:
                        line_bot_api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=reply_msgs[:5]))

                # B. GPS 位置訊息 (自動記憶座標，雙模組智慧共用)
                elif isinstance(event.message, LocationMessageContent):
                    loc = event.message
                    res = handle_location_event(
                        user_id=user_id,
                        lat=loc.latitude,
                        lng=loc.longitude,
                        address=loc.address or "您傳送的定位"
                    )
                    reply_msgs = []
                    if res.get("text_message"):
                        reply_msgs.append(TextMessage(text=res["text_message"], quick_reply=get_hub_quick_reply()))
                    if res.get("flex_contents"):
                        reply_msgs.append(
                            FlexMessage(
                                alt_text=res.get("flex_alt_text", "📍 周邊探索結果"),
                                contents=FlexContainer.from_json(json.dumps(res["flex_contents"])),
                                quick_reply=get_hub_quick_reply()
                            )
                        )
                    line_bot_api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=reply_msgs[:5]))

                # C. 拍照上傳食物辨識
                elif isinstance(event.message, ImageMessageContent):
                    try:
                        img_bytes = line_bot_blob_api.get_message_content(event.message.id)
                        data = calorie_ai_service.analyze_food(image_bytes=img_bytes)
                    except Exception:
                        data = calorie_ai_service.analyze_food(text="拍照辨識套餐")

                    bubble = build_food_analysis_flex(
                        food_name=data.get("food_name", "📸 拍照辨識餐點"),
                        calories=int(data.get("calories", 560)),
                        protein_g=int(data.get("protein_g", 28)),
                        carbs_g=int(data.get("carbs_g", 64)),
                        fat_g=int(data.get("fat_g", 20)),
                        health_rating=data.get("health_rating", "AI 視覺估算"),
                        advice=data.get("advice", ""),
                        items=data.get("items", [])
                    )
                    line_bot_api.reply_message(
                        ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[
                                FlexMessage(
                                    alt_text=f"📸 餐點熱量分析：{data.get('food_name', '餐點')}",
                                    contents=FlexContainer.from_json(json.dumps(bubble)),
                                    quick_reply=get_hub_quick_reply()
                                )
                            ]
                        )
                    )

    return JSONResponse(content={"status": "ok"})
