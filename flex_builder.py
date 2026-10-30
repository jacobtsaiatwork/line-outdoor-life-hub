# -*- coding: utf-8 -*-
"""
🎨 外出生活三合一超級選單 (Outdoor Life 3-in-1 Super Hub) Flex Message 卡片庫
包含：
1. 【連動 1 & 2】智慧美食盲盒推薦卡片 (`build_smart_food_flex`)：
   - 顯示預估熱量、三大營養素 (蛋白質/碳水/脂肪)、今日剩餘熱量比對狀態、價格區間與 Google Maps 導航
   - 底部配置三顆跨模組連動按鈕：
     * 🔥 就決定吃這個！一鍵記入今日熱量 (`action=eat_this&food_name=...&calories=...&protein=...&carbs=...&fat=...`)
     * 🎲 換一個（再抽一次） (`action=draw_food&exclude=...`)
     * 🚻 找附近的友善洗手間 (`action=find_toilet_from_food`)
2. AI 拍照 / 自然語言飲食熱量分析卡片 (`build_food_analysis_flex`)
3. 今日熱量與飲水儀表板卡片 (`build_daily_dashboard_flex`)：含「🥗 依剩餘熱量抽美食」連動按鈕
4. 【連動 3】周邊美食輪播卡片 (`build_nearby_food_carousel`)：底部含「🔄 用同一個定位改找附近洗手間」
5. 【連動 3】周邊救急友善洗手間輪播卡片 (`build_nearby_toilet_carousel`)：底部含「🔄 用同一個定位改找附近美食」
6. 三合一超級選單歡迎指引卡片 (`build_hub_welcome_flex`)
"""
import urllib.parse
from typing import Dict, Any, List, Optional


def build_smart_food_flex(
    food: Dict[str, Any],
    remaining_calories: Optional[int] = None,
    user_lat: Optional[float] = None,
    user_lng: Optional[float] = None
) -> Dict[str, Any]:
    """
    建立「美食盲盒 × 熱量管家 × 友善洗手間」三合一連動推薦卡片
    """
    food_name = food.get("name", "精選推薦料理")
    category = food.get("category", "人氣美食")
    emoji = food.get("emoji", "🍽️")
    calories = int(food.get("calories", 550))
    protein_g = int(food.get("protein_g", 25))
    carbs_g = int(food.get("carbs_g", 60))
    fat_g = int(food.get("fat_g", 18))
    price_level = food.get("price_level", "平價飽足 ($150-$280)")
    reason = food.get("reason", "美味營養兼具的推薦餐點！")
    recommended_dishes = food.get("recommended_dishes", food_name)
    image_url = food.get("image_url", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=700")

    # 計算與今日剩餘熱量額度的關係
    if remaining_calories is not None:
        if calories <= remaining_calories:
            after_eat = remaining_calories - calories
            budget_badge = f"✅ 符合今日剩餘額度 (吃完還剩 {after_eat} kcal)"
            budget_bg = "#ECFDF5"
            budget_color = "#059669"
        else:
            over_cal = calories - remaining_calories
            budget_badge = f"⚠️ 提醒：微超標 +{over_cal} kcal (剩餘額度 {remaining_calories} kcal)"
            budget_bg = "#FEF2F2"
            budget_color = "#DC2626"
    else:
        budget_badge = f"🔥 智慧熱量標示：{calories} kcal"
        budget_bg = "#FFF7ED"
        budget_color = "#EA580C"

    if user_lat is not None and user_lng is not None:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(food_name)}&center={user_lat},{user_lng}"
    else:
        maps_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(food_name + ' 餐廳')}"

    eat_postback = (
        f"action=eat_this"
        f"&food_name={urllib.parse.quote(food_name[:28])}"
        f"&calories={calories}"
        f"&protein={protein_g}"
        f"&carbs={carbs_g}"
        f"&fat={fat_g}"
    )
    reroll_postback = f"action=draw_food&exclude={urllib.parse.quote(food_name[:28])}"

    return {
        "type": "bubble",
        "size": "mega",
        "hero": {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "20:12",
            "aspectMode": "cover",
            "action": {
                "type": "uri",
                "label": "開啟地圖搜尋",
                "uri": maps_url
            }
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"🏷️ {category}",
                            "size": "xxs",
                            "weight": "bold",
                            "color": "#EA580C",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": f"🔥 約 {calories} kcal",
                            "size": "xs",
                            "weight": "bold",
                            "color": "#DC2626",
                            "align": "end",
                            "flex": 1
                        }
                    ]
                },
                {
                    "type": "text",
                    "text": f"{emoji} {food_name}",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#0F172A",
                    "wrap": True
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": budget_bg,
                    "cornerRadius": "6px",
                    "paddingAll": "8px",
                    "margin": "xs",
                    "contents": [
                        {
                            "type": "text",
                            "text": budget_badge,
                            "size": "xxs",
                            "weight": "bold",
                            "color": budget_color,
                            "wrap": True
                        }
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "margin": "sm",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "backgroundColor": "#EFF6FF",
                            "paddingAll": "6px",
                            "cornerRadius": "6px",
                            "contents": [
                                {"type": "text", "text": "蛋白質", "size": "xxs", "color": "#2563EB", "align": "center"},
                                {"type": "text", "text": f"{protein_g}g", "size": "xs", "weight": "bold", "color": "#1D4ED8", "align": "center"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "backgroundColor": "#FEF3C7",
                            "paddingAll": "6px",
                            "cornerRadius": "6px",
                            "contents": [
                                {"type": "text", "text": "碳水", "size": "xxs", "color": "#D97706", "align": "center"},
                                {"type": "text", "text": f"{carbs_g}g", "size": "xs", "weight": "bold", "color": "#B45309", "align": "center"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "backgroundColor": "#FEE2E2",
                            "paddingAll": "6px",
                            "cornerRadius": "6px",
                            "contents": [
                                {"type": "text", "text": "脂肪", "size": "xxs", "color": "#DC2626", "align": "center"},
                                {"type": "text", "text": f"{fat_g}g", "size": "xs", "weight": "bold", "color": "#B91C1C", "align": "center"}
                            ]
                        }
                    ]
                },
                {
                    "type": "text",
                    "text": reason,
                    "size": "xs",
                    "color": "#475569",
                    "wrap": True,
                    "margin": "xs"
                },
                {"type": "separator", "margin": "sm"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "margin": "xs",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "💰 價格區間", "size": "xxs", "color": "#94A3B8", "flex": 2},
                                {"type": "text", "text": price_level, "size": "xxs", "color": "#334155", "weight": "bold", "flex": 4}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": "✨ 推薦必點", "size": "xxs", "color": "#94A3B8", "flex": 2},
                                {"type": "text", "text": recommended_dishes, "size": "xxs", "color": "#334155", "wrap": True, "flex": 4}
                            ]
                        }
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "14px",
            "backgroundColor": "#F8FAFC",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#10B981",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🔥 就決定吃這個！一鍵記入今日熱量",
                        "data": eat_postback,
                        "displayText": f"🔥 就決定吃「{food_name}」！幫我一鍵記入今日熱量 (+{calories} kcal)"
                    }
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "🎲 換一個（再抽一次）",
                                "data": reroll_postback,
                                "displayText": "🎲 換一個（再抽一次）！"
                            },
                            "flex": 1
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "action": {
                                "type": "uri",
                                "label": "🗺️ 搜尋附近店家",
                                "uri": maps_url
                            },
                            "flex": 1
                        }
                    ]
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🚻 找附近的友善洗手間",
                        "data": "action=switch_gps_mode&target=toilet",
                        "displayText": "🚻 幫我找附近的友善洗手間！"
                    }
                }
            ]
        }
    }


def build_food_analysis_flex(
    food_name: str,
    calories: int,
    protein_g: int,
    carbs_g: int,
    fat_g: int,
    health_rating: str = "均衡推薦",
    advice: str = "",
    items: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """建立 AI 拍照 / 自然語言食物熱量分析卡片（支援一鍵記入今日熱量）"""
    eat_postback = (
        f"action=eat_this"
        f"&food_name={urllib.parse.quote(food_name[:28])}"
        f"&calories={calories}"
        f"&protein={protein_g}"
        f"&carbs={carbs_g}"
        f"&fat={fat_g}"
    )

    item_boxes = []
    if items:
        for it in items[:4]:
            item_boxes.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": f"• {it.get('name', '餐點細項')}", "size": "xs", "color": "#64748B", "flex": 3},
                    {"type": "text", "text": f"{it.get('cal', 0)} kcal", "size": "xs", "color": "#334155", "align": "end", "flex": 1}
                ]
            })

    body_contents: List[Dict[str, Any]] = [
        {
            "type": "text",
            "text": "三大巨量營養素估算",
            "weight": "bold",
            "size": "xs",
            "color": "#475569"
        },
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#EFF6FF",
                    "paddingAll": "10px",
                    "cornerRadius": "8px",
                    "contents": [
                        {"type": "text", "text": "蛋白質", "size": "xxs", "color": "#3B82F6", "align": "center"},
                        {"type": "text", "text": f"{protein_g}g", "size": "sm", "weight": "bold", "color": "#1D4ED8", "align": "center"}
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#FEF3C7",
                    "paddingAll": "10px",
                    "cornerRadius": "8px",
                    "contents": [
                        {"type": "text", "text": "碳水化合物", "size": "xxs", "color": "#D97706", "align": "center"},
                        {"type": "text", "text": f"{carbs_g}g", "size": "sm", "weight": "bold", "color": "#B45309", "align": "center"}
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#FEE2E2",
                    "paddingAll": "10px",
                    "cornerRadius": "8px",
                    "contents": [
                        {"type": "text", "text": "脂肪", "size": "xxs", "color": "#EF4444", "align": "center"},
                        {"type": "text", "text": f"{fat_g}g", "size": "sm", "weight": "bold", "color": "#B91C1C", "align": "center"}
                    ]
                }
            ]
        }
    ]

    if item_boxes:
        body_contents.append({"type": "separator", "margin": "md"})
        body_contents.append({
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "margin": "sm",
            "contents": item_boxes
        })

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F172A",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "📸 AI 飲食熱量管家", "weight": "bold", "size": "sm", "color": "#38BDF8"},
                        {"type": "text", "text": health_rating, "size": "xxs", "color": "#10B981", "align": "end", "weight": "bold"}
                    ]
                },
                {
                    "type": "text",
                    "text": food_name,
                    "weight": "bold",
                    "size": "xl",
                    "color": "#F8FAFC",
                    "margin": "sm",
                    "wrap": True
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "margin": "sm",
                    "contents": [
                        {"type": "text", "text": "預估總熱量", "size": "xs", "color": "#94A3B8"},
                        {"type": "text", "text": f" {calories} ", "size": "xxl", "weight": "bold", "color": "#F43F5E", "flex": 0},
                        {"type": "text", "text": "kcal", "size": "sm", "color": "#F43F5E", "weight": "bold"}
                    ]
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#FFFFFF",
            "paddingAll": "18px",
            "spacing": "md",
            "contents": body_contents
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "backgroundColor": "#F8FAFC",
            "paddingAll": "14px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#10B981",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": f"🔥 一鍵記入今日熱量 (+{calories} kcal)",
                        "data": eat_postback,
                        "displayText": f"🔥 記入今日熱量：{food_name} (+{calories} kcal)"
                    }
                },
                {
                    "type": "text",
                    "text": f"💡 營養師建議：{advice if advice else '多吃原型食物、少喝含糖飲料能讓減脂更順利！'}",
                    "size": "xxs",
                    "color": "#64748B",
                    "wrap": True
                }
            ]
        }
    }


def build_daily_dashboard_flex(user_profile: Optional[Dict[str, Any]], today_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    建立今日飲食熱量儀表板卡片
    底部直接串接「🥗 依剩餘熱量抽下一餐美食」與「🚻 找附近友善洗手間」！
    """
    target = int(user_profile.get("target_calories", 2000)) if user_profile else int(today_summary.get("target_calories", 2000))
    consumed = int(today_summary.get("total_calories", 0))
    remaining = target - consumed
    water_ml = int(today_summary.get("water_ml", 0))
    meal_count = int(today_summary.get("meal_count", 0))
    total_p = int(today_summary.get("total_protein", 0))
    total_c = int(today_summary.get("total_carbs", 0))
    total_f = int(today_summary.get("total_fat", 0))

    status_color = "#10B981" if remaining >= 0 else "#EF4444"

    meals_boxes = []
    meals = today_summary.get("meals", [])
    if meals:
        for m in meals[-6:]:
            meals_boxes.append({
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": f"• {m.get('time_str', '今日')} {m['meal_name']}", "size": "xs", "color": "#334155", "flex": 3, "wrap": True},
                    {"type": "text", "text": f"+{m['calories']} kcal", "size": "xs", "weight": "bold", "color": "#F43F5E", "align": "end", "flex": 1}
                ]
            })
    else:
        meals_boxes.append({
            "type": "text",
            "text": "今天還沒有任何餐點紀錄喔！點下方「🥗 依剩餘熱量抽美食」或直接傳餐點照片開始記帳吧！",
            "size": "xs",
            "color": "#94A3B8",
            "wrap": True
        })

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F172A",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "text",
                    "text": "📊 今日熱量與營養儀表板",
                    "weight": "bold",
                    "size": "md",
                    "color": "#38BDF8"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "今日目標", "size": "xxs", "color": "#94A3B8"},
                                {"type": "text", "text": f"{target}", "size": "lg", "weight": "bold", "color": "#FFFFFF"},
                                {"type": "text", "text": "kcal", "size": "xxs", "color": "#94A3B8"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "已攝取", "size": "xxs", "color": "#94A3B8"},
                                {"type": "text", "text": f"{consumed}", "size": "lg", "weight": "bold", "color": "#F59E0B"},
                                {"type": "text", "text": "kcal", "size": "xxs", "color": "#94A3B8"}
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "flex": 1,
                            "contents": [
                                {"type": "text", "text": "剩餘額度", "size": "xxs", "color": "#94A3B8"},
                                {"type": "text", "text": f"{remaining}", "size": "lg", "weight": "bold", "color": status_color},
                                {"type": "text", "text": "kcal", "size": "xxs", "color": "#94A3B8"}
                            ]
                        }
                    ]
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "18px",
            "spacing": "sm",
            "backgroundColor": "#FFFFFF",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": f"🥩 蛋白質 {total_p}g", "size": "xxs", "color": "#2563EB", "weight": "bold"},
                        {"type": "text", "text": f"🍚 碳水 {total_c}g", "size": "xxs", "color": "#D97706", "weight": "bold", "align": "center"},
                        {"type": "text", "text": f"🥑 脂肪 {total_f}g", "size": "xxs", "color": "#DC2626", "weight": "bold", "align": "end"}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "xs",
                    "contents": [
                        {"type": "text", "text": "💧 今日飲水進度", "size": "xs", "weight": "bold", "color": "#0284C7"},
                        {"type": "text", "text": f"{water_ml} / 2000 ml", "size": "xs", "weight": "bold", "color": "#0369A1", "align": "end"}
                    ]
                },
                {"type": "separator", "margin": "sm"},
                {
                    "type": "text",
                    "text": f"🍱 今日已記帳餐點 ({meal_count} 餐)",
                    "size": "xs",
                    "weight": "bold",
                    "color": "#475569",
                    "margin": "xs"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": meals_boxes
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "backgroundColor": "#F8FAFC",
            "paddingAll": "14px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#EA580C",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": f"🥗 依剩餘 {max(0, remaining)} kcal 抽不爆卡美食",
                        "data": "action=draw_food&strict=1",
                        "displayText": "🥗 幫我依今日剩餘熱量抽不爆卡美食！"
                    }
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "action": {
                                "type": "message",
                                "label": "💧 喝水 +300ml",
                                "text": "喝水 300"
                            },
                            "flex": 1
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "height": "sm",
                            "action": {
                                "type": "postback",
                                "label": "🚻 找順路洗手間",
                                "data": "action=switch_gps_mode&target=toilet",
                                "displayText": "🚻 幫我找附近的友善洗手間！"
                            },
                            "flex": 1
                        }
                    ]
                }
            ]
        }
    }


def build_nearby_food_carousel(
    restaurants: List[Dict[str, Any]],
    user_lat: float,
    user_lng: float,
    remaining_calories: int = 2000
) -> Dict[str, Any]:
    """
    【連動 3：GPS 定位一次傳送，雙模組智慧共用 - 周邊美食輪播卡片】
    每張餐廳卡片皆可「🔥 一鍵記熱量」，且輪播附帶「🔄 用同一個定位改找附近洗手間」切換卡！
    """
    bubbles = []
    for r in restaurants[:5]:
        name = r.get("name", "推薦餐廳")
        rating = r.get("rating", 4.5)
        dist_str = r.get("distance_str", "附近商圈")
        cat = r.get("category", "人氣美食")
        cal = int(r.get("estimated_calories", 550))
        p = int(r.get("protein_g", 28))
        c = int(r.get("carbs_g", 60))
        f = int(r.get("fat_g", 18))
        image_url = r.get("image_url", "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=700")
        maps_url = r.get("maps_url", f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name)}")

        eat_postback = (
            f"action=eat_this"
            f"&food_name={urllib.parse.quote(name[:28])}"
            f"&calories={cal}"
            f"&protein={p}"
            f"&carbs={c}"
            f"&fat={f}"
        )

        bubbles.append({
            "type": "bubble",
            "size": "kilo",
            "hero": {
                "type": "image",
                "url": image_url,
                "size": "full",
                "aspectRatio": "16:9",
                "aspectMode": "cover",
                "action": {"type": "uri", "label": "開啟導航", "uri": maps_url}
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": name, "weight": "bold", "size": "md", "wrap": True, "maxLines": 2},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": f"⭐ {rating:.1f}", "size": "xs", "color": "#F59E0B", "weight": "bold", "flex": 2},
                            {"type": "text", "text": f"🔥 約 {cal} kcal", "size": "xs", "color": "#DC2626", "weight": "bold", "align": "end", "flex": 3}
                        ]
                    },
                    {"type": "text", "text": f"🚶 {dist_str}", "size": "xxs", "color": "#059669", "weight": "bold"},
                    {"type": "text", "text": f"🏷️ {cat}｜P:{p}g C:{c}g F:{f}g", "size": "xxs", "color": "#64748B"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "paddingAll": "12px",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#10B981",
                        "height": "sm",
                        "action": {
                            "type": "postback",
                            "label": f"🔥 吃這家！記熱量 (+{cal}卡)",
                            "data": eat_postback,
                            "displayText": f"🔥 決定吃「{name}」！一鍵記入今日熱量 (+{cal} kcal)"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "🗺️ Google 地圖導航",
                            "uri": maps_url
                        }
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "postback",
                            "label": "🔄 用同一個定位改找附近洗手間",
                            "data": "action=switch_gps_mode&target=toilet",
                            "displayText": "🔄 用同一個定位改找附近洗手間！"
                        }
                    }
                ]
            }
        })

    # 最後一張：跨模組 GPS 共享切換卡片
    bubbles.append({
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0284C7",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": "🧭 跨模組 GPS 座標智慧共用", "color": "#FFFFFF", "weight": "bold", "size": "sm"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": f"📍 已記憶您的定位 ({user_lat:.4f}, {user_lng:.4f})", "size": "xs", "weight": "bold", "color": "#0F172A"},
                {"type": "text", "text": f"🥗 今日剩餘熱量額度：{remaining_calories} kcal\n無需重複傳送定位，一鍵切換搜尋附近救急友善洗手間！", "size": "xs", "color": "#475569", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🔄 用同一個定位改找附近洗手間",
                        "data": "action=switch_gps_mode&target=toilet",
                        "displayText": "🔄 用同一個定位改找附近洗手間！"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🥗 依剩餘熱量抽美食盲盒",
                        "data": "action=draw_food&strict=1",
                        "displayText": "🥗 依剩餘熱量抽美食盲盒！"
                    }
                }
            ]
        }
    })

    return {"type": "carousel", "contents": bubbles}


def build_nearby_toilet_carousel(
    toilets: List[Dict[str, Any]],
    user_lat: float,
    user_lng: float
) -> Dict[str, Any]:
    """
    【連動 3：GPS 定位一次傳送，雙模組智慧共用 - 周邊救急友善洗手間輪播卡片】
    每張卡片標示 24H / 無障礙 / 尿布檯與步行時間，底部皆可「🔄 用同一個定位改找附近美食」！
    """
    bubbles = []
    for idx, t in enumerate(toilets[:5]):
        name = t.get("name", "友善洗手間")
        dist = int(t.get("distance_meters", 150))
        walk_min = int(t.get("walk_minutes", 2))
        cat_name = t.get("category_name", "🚻 友善洗手間")
        theme_color = t.get("theme_color", "#0284C7")
        tip = t.get("tip", "免消費友善開放借用")
        tags = t.get("tags", ["🕒 24H", "♿ 無障礙"])
        nav_url = t.get("nav_url", "#")

        tag_boxes = []
        for tag in tags:
            tag_boxes.append({
                "type": "box",
                "layout": "baseline",
                "backgroundColor": "#EFF6FF",
                "cornerRadius": "4px",
                "paddingAll": "4px",
                "contents": [
                    {"type": "text", "text": tag, "size": "xxs", "color": "#1D4ED8", "weight": "bold", "flex": 0}
                ]
            })

        bubbles.append({
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": theme_color,
                "paddingAll": "12px",
                "contents": [
                    {"type": "text", "text": f"{cat_name} #{idx + 1}", "color": "#FFFFFF", "weight": "bold", "size": "sm"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "14px",
                "spacing": "xs",
                "contents": [
                    {"type": "text", "text": name, "weight": "bold", "size": "md", "wrap": True, "maxLines": 2},
                    {"type": "text", "text": f"🚶 步行約 {walk_min} 分鐘 (約 {dist}m)", "size": "xs", "color": "#059669", "weight": "bold"},
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "xs",
                        "margin": "xs",
                        "contents": tag_boxes
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#F8FAFC",
                        "cornerRadius": "6px",
                        "paddingAll": "8px",
                        "margin": "xs",
                        "contents": [
                            {"type": "text", "text": f"💡 {tip}", "size": "xxs", "color": "#475569", "wrap": True}
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "paddingAll": "12px",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": theme_color,
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "🗺️ Google 地圖即時導航",
                            "uri": nav_url
                        }
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "postback",
                            "label": "🔄 用同一個定位改找附近美食",
                            "data": "action=switch_gps_mode&target=food",
                            "displayText": "🔄 用同一個定位改找附近美食！"
                        }
                    }
                ]
            }
        })

    # 最後一張：免重傳 GPS 切換找美食卡片
    bubbles.append({
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#EA580C",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": "🍽️ 上完洗手間餓了嗎？", "color": "#FFFFFF", "weight": "bold", "size": "sm"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": f"📍 已記憶您的定位 ({user_lat:.4f}, {user_lng:.4f})", "size": "xs", "weight": "bold", "color": "#0F172A"},
                {"type": "text", "text": "免重新傳送位置訊息！點擊下方按鈕直接用同一個 GPS 座標探索周邊高分餐廳與低卡美食：", "size": "xs", "color": "#475569", "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#EA580C",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🔄 用同一個定位改找附近美食",
                        "data": "action=switch_gps_mode&target=food",
                        "displayText": "🔄 用同一個定位改找附近美食！"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🥗 依剩餘熱量抽美食盲盒",
                        "data": "action=draw_food&strict=1",
                        "displayText": "🥗 依剩餘熱量抽美食盲盒！"
                    }
                }
            ]
        }
    })

    return {"type": "carousel", "contents": bubbles}


def build_hub_welcome_flex(remaining_calories: int = 2000) -> Dict[str, Any]:
    """建立外出生活三合一超級選單 (Outdoor Life 3-in-1 Super Hub) 歡迎總覽卡片"""
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F172A",
            "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": "🧭 外出生活三合一超級選單", "color": "#38BDF8", "weight": "bold", "size": "sm"},
                {"type": "text", "text": "美食抽籤 × 熱量控制 × 附近洗手間", "color": "#FFFFFF", "weight": "bold", "size": "lg", "margin": "xs", "wrap": True},
                {"type": "text", "text": f"🔥 您今日剩餘可用熱量額度：{remaining_calories} kcal", "color": "#10B981", "size": "xs", "margin": "sm", "weight": "bold"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": [
                        {"type": "text", "text": "1️⃣ 【連動 1】依熱量剩餘額度智慧抽美食", "weight": "bold", "size": "xs", "color": "#EA580C"},
                        {"type": "text", "text": "輸入「吃什麼」、「隨便」或點「🥗 依剩餘熱量抽美食」，自動優先推薦不爆卡料理！", "size": "xxs", "color": "#475569", "wrap": True}
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": [
                        {"type": "text", "text": "2️⃣ 【連動 2】抽中美食一鍵記熱量＋找順路廁所", "weight": "bold", "size": "xs", "color": "#10B981"},
                        {"type": "text", "text": "抽中餐點後點「🔥 就決定吃這個！一鍵記入今日熱量」免打字秒入帳；或傳照片/文字由 AI 估算熱量！", "size": "xxs", "color": "#475569", "wrap": True}
                    ]
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": [
                        {"type": "text", "text": "3️⃣ 【連動 3】GPS 定位一次傳送，雙模組智慧共用", "weight": "bold", "size": "xs", "color": "#0284C7"},
                        {"type": "text", "text": "傳送一次位置訊息，即可一鍵在「附近美食餐廳」與「附近救急友善洗手間」之間無縫切換！", "size": "xxs", "color": "#475569", "wrap": True}
                    ]
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "14px",
            "backgroundColor": "#F8FAFC",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#EA580C",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🥗 依剩餘熱量智慧抽美食",
                        "data": "action=draw_food&strict=1",
                        "displayText": "🥗 依剩餘熱量抽美食！"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#10B981",
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "📊 查看今日熱量儀表板",
                        "text": "今日熱量"
                    }
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#0284C7",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🚻 找附近的友善洗手間",
                        "data": "action=switch_gps_mode&target=toilet",
                        "displayText": "🚻 找附近的友善洗手間！"
                    }
                }
            ]
        }
    }


def build_bill_split_flex(
    total_amount: float,
    head_count: int,
    tip_pct: float = 0.0,
    note: str = ""
) -> Dict[str, Any]:
    """
    外出聚餐快速分帳與 AA 制計算機 Flex 卡片
    """
    tip_amount = round(total_amount * (tip_pct / 100.0))
    grand_total = round(total_amount + tip_amount)
    per_person = round(grand_total / max(1, head_count))
    remainder = grand_total - (per_person * head_count)

    tip_text = f"{tip_pct:.0f}% (${tip_amount})" if tip_pct > 0 else "無 / 已內含"
    rem_text = f"（整除差額：首位支付 ${per_person + remainder}）" if remainder != 0 else "（剛好整除）"

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F172A",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "💳 外出聚餐快速 AA 制分帳", "color": "#38BDF8", "weight": "bold", "size": "sm"},
                {
                    "type": "box",
                    "layout": "baseline",
                    "margin": "sm",
                    "contents": [
                        {"type": "text", "text": "每人應付：", "color": "#94A3B8", "size": "md"},
                        {"type": "text", "text": f"${per_person:,}", "color": "#10B981", "weight": "bold", "size": "xxl"}
                    ]
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "消費總額", "size": "xs", "color": "#64748B", "flex": 2},
                        {"type": "text", "text": f"${round(total_amount):,}", "size": "xs", "weight": "bold", "color": "#0F172A", "align": "end", "flex": 3}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "服務費 / 小費", "size": "xs", "color": "#64748B", "flex": 2},
                        {"type": "text", "text": tip_text, "size": "xs", "color": "#64748B", "align": "end", "flex": 3}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "分攤人數", "size": "xs", "color": "#64748B", "flex": 2},
                        {"type": "text", "text": f"{head_count} 人", "size": "xs", "weight": "bold", "color": "#0F172A", "align": "end", "flex": 3}
                    ]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "含費總計", "size": "xs", "color": "#64748B", "flex": 2},
                        {"type": "text", "text": f"${grand_total:,}", "size": "xs", "weight": "bold", "color": "#DC2626", "align": "end", "flex": 3}
                    ]
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "text",
                    "text": f"💡 計算備註：{rem_text}",
                    "size": "xxs",
                    "color": "#64748B",
                    "wrap": True,
                    "margin": "sm"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "paddingAll": "12px",
            "backgroundColor": "#F8FAFC",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🥗 依剩餘熱量抽下頓美食",
                        "data": "action=draw_food&strict=1",
                        "displayText": "🥗 幫我抽下一餐的不爆卡美食！"
                    }
                }
            ]
        }
    }


def build_food_poll_carousel(poll_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    建立「多人聚餐吃什麼？3選1快速投票」輪播卡片
    """
    poll_id = poll_data.get("poll_id", "poll_001")
    title = poll_data.get("title", "聚餐吃什麼？快來投票決定！")
    options = poll_data.get("options", [])
    votes = poll_data.get("votes", {})

    bubbles = []
    for idx, opt in enumerate(options):
        food_name = opt.get("name", f"選項 {idx+1}")
        cat = opt.get("category", "人氣料理")
        cal = opt.get("calories", 550)
        img_url = opt.get("image_url", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=700")

        # 計算當前得票數
        current_votes = sum(1 for v in votes.values() if v == idx)

        vote_postback = f"action=vote_poll&poll_id={poll_id}&idx={idx}"

        bubbles.append({
            "type": "bubble",
            "size": "kilo",
            "hero": {
                "type": "image",
                "url": img_url,
                "size": "full",
                "aspectRatio": "16:9",
                "aspectMode": "cover"
            },
            "header": {
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#EA580C",
                "paddingAll": "10px",
                "contents": [
                    {"type": "text", "text": f"🗳️ 候選 {idx + 1}：{cat}", "color": "#FFFFFF", "weight": "bold", "size": "xs"}
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "paddingAll": "14px",
                "contents": [
                    {"type": "text", "text": food_name, "weight": "bold", "size": "md", "wrap": True},
                    {"type": "text", "text": f"🔥 約 {cal} kcal｜目前得票：{current_votes} 票", "size": "xs", "color": "#DC2626", "weight": "bold"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "12px",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#10B981",
                        "height": "sm",
                        "action": {
                            "type": "postback",
                            "label": f"👍 投這家 ({current_votes}票)",
                            "data": vote_postback,
                            "displayText": f"👍 我投給「{food_name}」一票！"
                        }
                    }
                ]
            }
        })

    # 結果即時檢視卡
    bubbles.append({
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F172A",
            "paddingAll": "12px",
            "contents": [
                {"type": "text", "text": "📊 即時開票結果", "color": "#38BDF8", "weight": "bold", "size": "sm"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "14px",
            "contents": [
                {"type": "text", "text": title, "weight": "bold", "size": "xs", "color": "#0F172A", "wrap": True},
                {"type": "text", "text": f"總投票人數：{len(votes)} 人", "size": "xxs", "color": "#64748B"},
                {"type": "separator", "margin": "sm"}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "🔄 刷新票數統計",
                        "data": f"action=view_poll&poll_id={poll_id}",
                        "displayText": "🔄 刷新目前投票結果！"
                    }
                }
            ]
        }
    })

    return {"type": "carousel", "contents": bubbles}

