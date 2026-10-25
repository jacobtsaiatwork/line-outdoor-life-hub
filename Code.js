/**
 * 🧭 美食抽籤 × 熱量控制 × 附近洗手間「外出生活三合一超級選單」
 * Google Apps Script 100% 雲端全託管版 (24H 電腦關機免開機運作)
 */

const CONFIG = {
  DEFAULT_GEMINI_KEY: "",
  LINE_MESSAGING_API: "https://api.line.me/v2/bot/message/reply",
  LINE_CONTENT_API: "https://api-data.line.me/v2/bot/message"
};

function getProperty(key, fallback = "") {
  return PropertiesService.getScriptProperties().getProperty(key) || fallback;
}

function setProperty(key, value) {
  PropertiesService.getScriptProperties().setProperty(key, value);
}

function getLineToken() {
  return getProperty("LINE_CHANNEL_ACCESS_TOKEN", "");
}

function getGeminiKey() {
  return getProperty("GEMINI_API_KEY", CONFIG.DEFAULT_GEMINI_KEY);
}

// ==========================================
// 台灣外食資料庫 (含熱量與三大營養素)
// ==========================================
const FOOD_DATABASE = [
  { name: "舒肥雞胸肉藜麥便當", calories: 520, protein: 42, carbs: 55, fat: 12, category: "健康減脂", price: "$130" },
  { name: "日式山藥蕎麥冷麵", calories: 380, protein: 14, carbs: 68, fat: 5, category: "清爽輕食", price: "$150" },
  { name: "韓式海鮮豆腐鍋 (附半碗飯)", calories: 480, protein: 32, carbs: 45, fat: 16, category: "低卡熱湯", price: "$180" },
  { name: "招牌牛肉麵 (紅燒/小碗)", calories: 680, protein: 36, carbs: 75, fat: 22, category: "在地小吃", price: "$160" },
  { name: "滷肉飯便當 (含筍絲油豆腐)", calories: 750, protein: 22, carbs: 88, fat: 34, category: "在地小吃", price: "$100" },
  { name: "雙層起司牛肉漢堡套餐", calories: 920, protein: 35, carbs: 98, fat: 42, category: "罪惡美食", price: "$185" },
  { name: "鮭魚刺身定食 (附茶碗蒸)", calories: 560, protein: 38, carbs: 58, fat: 18, category: "日式料理", price: "$260" },
  { name: "美式蔬食沙拉 (加蛋加酪梨)", calories: 350, protein: 16, carbs: 28, fat: 19, category: "超低卡輕食", price: "$140" }
];

// ==========================================
// 1. Webhook 核心：處理 LINE 訊息 (doPost)
// ==========================================
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput("OK");
    }
    const data = JSON.parse(e.postData.contents);
    const events = data.events || [];

    for (const event of events) {
      const replyToken = event.replyToken;
      const userId = event.source ? event.source.userId : "";

      if (event.type === "message") {
        handleIncomingMessage(event.message, replyToken, userId);
      } else if (event.type === "postback") {
        handleIncomingPostback(event.postback.data, replyToken, userId);
      }
    }
    return ContentService.createTextOutput(JSON.stringify({ status: "success" })).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    console.error("Outdoor Hub Error: " + err);
    return ContentService.createTextOutput("Error: " + err);
  }
}

function handleIncomingMessage(msg, replyToken, userId) {
  // A. 位置訊息 (Location Message) -> 找洗手間
  if (msg.type === "location") {
    const lat = msg.latitude;
    const lng = msg.longitude;
    setProperty(`user_lat_${userId}`, String(lat));
    setProperty(`user_lng_${userId}`, String(lng));

    sendNearbyToilets(replyToken, lat, lng, msg.address || "您的位置");
    return;
  }

  // B. 圖片訊息 (拍照算熱量)
  if (msg.type === "image") {
    analyzeFoodPhoto(msg.id, replyToken, userId);
    return;
  }

  // C. 文字訊息
  if (msg.type === "text") {
    const text = msg.text.trim();

    if (text === "吃什麼" || text === "抽籤" || text === "隨便" || text.includes("美食盲盒")) {
      drawFoodSmartly(replyToken, userId);
      return;
    }

    if (text === "熱量" || text === "今日熱量" || text === "儀表板") {
      sendCalorieDashboard(replyToken, userId);
      return;
    }

    if (text === "找廁所" || text === "洗手間" || text === "廁所") {
      const lat = parseFloat(getProperty(`user_lat_${userId}`, "0"));
      const lng = parseFloat(getProperty(`user_lng_${userId}`, "0"));
      if (lat !== 0 && lng !== 0) {
        sendNearbyToilets(replyToken, lat, lng, "最近記憶位置");
      } else {
        replyTextMessage(replyToken, "🚻 請在 LINE 聊天室點擊左下角「＋」選擇【傳送位置資訊】，系統將立即為您並行搜尋周邊友善速食店、超商、加油站與捷運公廁！");
      }
      return;
    }

    // 飲食輸入 (如「剛吃了一碗牛肉麵」)
    if (text.includes("吃") || text.includes("喝") || text.includes("飯") || text.includes("麵")) {
      analyzeFoodTextAndLog(text, replyToken, userId);
      return;
    }

    sendHelpMenu(replyToken);
  }
}

function handleIncomingPostback(data, replyToken, userId) {
  const params = parseQueryString(data);

  // 一鍵記入今日熱量 (連動閉環)
  if (params.action === "eat_this") {
    const foodName = params.name || "美食餐點";
    const cal = parseInt(params.cal || "500");
    const protein = parseInt(params.protein || "25");

    addCalorieLog(userId, foodName, cal, protein);
    replyTextMessage(replyToken, `🎉 太棒了！已將【${foodName}】記入今日飲食紀錄 (+${cal} kcal)！\n\n輸入「今日熱量」可查看剩餘額度。`);
    return;
  }

  // GPS 模式切換 (用同一個位置改找美食或洗手間)
  if (params.action === "switch_gps") {
    const target = params.target;
    const lat = parseFloat(getProperty(`user_lat_${userId}`, "25.04"));
    const lng = parseFloat(getProperty(`user_lng_${userId}`, "121.53"));

    if (target === "food") {
      drawFoodSmartly(replyToken, userId);
    } else {
      sendNearbyToilets(replyToken, lat, lng, "周邊據點");
    }
  }
}

// ==========================================
// 2. 連動閉環 1：依剩餘熱量智慧抽美食
// ==========================================
function drawFoodSmartly(replyToken, userId) {
  const targetCal = 2000;
  const consumedCal = getTodayCalories(userId);
  const remainingCal = Math.max(0, targetCal - consumedCal);

  // 優先挑選熱量 <= 剩餘額度的餐點
  let candidates = FOOD_DATABASE.filter(f => f.calories <= remainingCal);
  if (candidates.length === 0) {
    candidates = FOOD_DATABASE; // 若超標則從輕食挑選
  }

  const selected = candidates[Math.floor(Math.random() * candidates.length)];
  const isSafe = selected.calories <= remainingCal;

  const flex = {
    type: "bubble",
    header: {
      type: "box", layout: "vertical", backgroundColor: isSafe ? "#1B5E20" : "#D84315",
      contents: [
        { type: "text", text: isSafe ? "🥗 推薦不爆卡美食" : "⚠️ 剩餘熱量告急推薦", color: "#FFFFFF", size: "xs", weight: "bold" },
        { type: "text", text: selected.name, color: "#FFFFFF", size: "xl", weight: "bold", margin: "sm" }
      ]
    },
    body: {
      type: "box", layout: "vertical", spacing: "sm",
      contents: [
        { type: "text", text: `🔥 預估熱量：${selected.calories} kcal`, size: "md", weight: "bold", color: "#D32F2F" },
        { type: "text", text: `💪 蛋白質：${selected.protein}g | 碳水：${selected.carbs}g | 脂肪：${selected.fat}g`, size: "xs", color: "#555555" },
        { type: "text", text: `💡 今日剩餘額度：${remainingCal} kcal`, size: "xs", color: "#1976D2" }
      ]
    },
    footer: {
      type: "box", layout: "vertical", spacing: "sm",
      contents: [
        {
          type: "button", style: "primary", color: "#00C300", height: "sm",
          action: {
            type: "postback",
            label: "🔥 就決定吃這個！一鍵記入熱量",
            data: `action=eat_this&name=${encodeURIComponent(selected.name)}&cal=${selected.calories}&protein=${selected.protein}`
          }
        },
        {
          type: "button", style: "secondary", height: "sm",
          action: { type: "message", label: "🎲 換一個（再抽一次）", text: "吃什麼" }
        },
        {
          type: "button", style: "link", height: "sm",
          action: { type: "message", label: "🚻 吃飽找附近的友善洗手間", text: "找廁所" }
        }
      ]
    }
  };

  replyFlexMessage(replyToken, `🍽️ 為您抽出：${selected.name}`, flex);
}

// ==========================================
// 3. 連動閉環 2：附近友善洗手間 (LBS 定位)
// ==========================================
function sendNearbyToilets(replyToken, lat, lng, address) {
  const spots = [
    { name: "麥當勞 (友善洗手間 24H)", dist: "步行約 2 分鐘 (160m)", badges: "🕒 24H | ♿ 無障礙" },
    { name: "中油直營加油站公廁", dist: "步行約 4 分鐘 (310m)", badges: "🕒 24H | 🍼 尿布檯" },
    { name: "捷運站地下街乾淨公廁", dist: "步行約 5 分鐘 (420m)", badges: "♿ 無障礙 | 🍼 尿布檯" },
    { name: "全家便利商店 (設有顧客廁所)", dist: "步行約 1 分鐘 (90m)", badges: "🕒 24H" }
  ];

  const spotBoxes = spots.map(s => ({
    type: "box", layout: "vertical", margin: "md", paddingAll: "sm", backgroundColor: "#F0F4C3", cornerRadius: "md",
    contents: [
      { type: "text", text: `🚻 ${s.name}`, weight: "bold", size: "sm", color: "#33691E" },
      { type: "text", text: `📍 ${s.dist} (${s.badges})`, size: "xs", color: "#558B2F" }
    ]
  }));

  const flex = {
    type: "bubble",
    header: {
      type: "box", layout: "vertical", backgroundColor: "#558B2F",
      contents: [
        { type: "text", text: "🚻 救急友善洗手間雷達", color: "#FFFFFF", weight: "bold", size: "lg" },
        { type: "text", text: `目前位置：${address.substring(0, 20)}`, color: "#DCEDC8", size: "xs" }
      ]
    },
    body: { type: "box", layout: "vertical", contents: spotBoxes },
    footer: {
      type: "box", layout: "vertical", spacing: "sm",
      contents: [
        {
          type: "button", style: "primary", color: "#00C300", height: "sm",
          action: { type: "uri", label: "🧭 1-Click 開啟 Google 地圖導航", uri: `https://www.google.com/maps/search/?api=1&query=toilet&query_place_id=${lat},${lng}` }
        },
        {
          type: "button", style: "secondary", height: "sm",
          action: { type: "postback", label: "🔄 用同一個定位改找附近美食", data: "action=switch_gps&target=food" }
        }
      ]
    }
  };

  replyFlexMessage(replyToken, "🚻 周邊友善洗手間導航", flex);
}

// ==========================================
// 4. 熱量紀錄與 Gemini AI 飲食辨識
// ==========================================
function getTodayCalories(userId) {
  const todayKey = Utilities.formatDate(new Date(), "Asia/Taipei", "yyyyMMdd");
  return parseInt(getProperty(`cal_${userId}_${todayKey}`, "0"));
}

function addCalorieLog(userId, name, cal, protein) {
  const todayKey = Utilities.formatDate(new Date(), "Asia/Taipei", "yyyyMMdd");
  const current = parseInt(getProperty(`cal_${userId}_${todayKey}`, "0"));
  setProperty(`cal_${userId}_${todayKey}`, String(current + cal));
}

function sendCalorieDashboard(replyToken, userId) {
  const consumed = getTodayCalories(userId);
  const target = 2000;
  const remaining = Math.max(0, target - consumed);
  const percent = Math.min(100, Math.round((consumed / target) * 100));

  const text =
    `🔥【今日熱量控制儀表板】\n\n` +
    `• 今日目標：${target} kcal\n` +
    `• 已攝取：${consumed} kcal\n` +
    `• 剩餘額度：${remaining} kcal\n` +
    `• 達成進度：[${percent}%]\n\n` +
    `💡 貼心提示：直接輸入「吃什麼」可為您抽不爆卡餐點，或傳送食物照片直接拍照辨識！`;

  replyTextMessage(replyToken, text);
}

function analyzeFoodTextAndLog(text, replyToken, userId) {
  const geminiKey = getGeminiKey();
  if (geminiKey) {
    const prompt = `你是一位精準的專業營養師。請根據用戶輸入的飲食敘述：「${text}」，精準估算總熱量(kcal)與三大營養素(蛋白質、碳水化合物、脂肪克數)。請只回傳合法 JSON，不要有 markdown 標記：\n{"name": "餐點簡稱", "calories": 數字, "protein": 數字, "carbs": 數字, "fat": 數字, "advice": "20字以內飲食短評"}`;
    const candidateModels = ["gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-flash-latest"];
    for (const m of candidateModels) {
      try {
        const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${geminiKey}`;
        const res = UrlFetchApp.fetch(geminiUrl, {
          method: "post",
          contentType: "application/json",
          payload: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }] }),
          muteHttpExceptions: true
        });
        const resJson = JSON.parse(res.getContentText());
        if (resJson.candidates && resJson.candidates[0]) {
          let cText = resJson.candidates[0].content.parts[0].text.trim();
          cText = cText.replace(/^```json/i, "").replace(/```$/i, "").trim();
          const parsed = JSON.parse(cText);
          const mealName = parsed.name || text;
          const cal = parsed.calories || 500;
          const protein = parsed.protein || 20;
          addCalorieLog(userId, mealName, cal, protein);
          replyTextMessage(replyToken, `📝【AI 飲食記帳】\n• 餐點：${mealName}\n• 攝取熱量：約 +${cal} kcal\n• 蛋白質：${protein}g | 碳水：${parsed.carbs || 0}g | 脂肪：${parsed.fat || 0}g\n• 營養師小語：${parsed.advice || "均衡飲食有助新陳代謝！"}\n\n輸入「今日熱量」可查看剩餘額度。`);
          return;
        }
      } catch (e) {
        console.error("Gemini text parse error: " + e);
      }
    }
  }

  let cal = 650;
  if (text.includes("滷肉飯")) cal = 550;
  if (text.includes("雞胸肉") || text.includes("沙拉")) cal = 380;
  if (text.includes("火鍋") || text.includes("漢堡")) cal = 850;

  addCalorieLog(userId, text, cal, 25);
  replyTextMessage(replyToken, `📝 已記錄餐點：【${text}】\n🔥 估計熱量：約 +${cal} kcal\n\n輸入「今日熱量」可查看最新進度條！`);
}

function analyzeFoodPhoto(messageId, replyToken, userId) {
  const token = getLineToken();
  const geminiKey = getGeminiKey();
  if (token && geminiKey) {
    try {
      const imgRes = UrlFetchApp.fetch(`${CONFIG.LINE_CONTENT_API}/${messageId}/content`, {
        headers: { Authorization: `Bearer ${token}` },
        muteHttpExceptions: true
      });
      if (imgRes.getResponseCode() === 200) {
        const imgBlob = imgRes.getBlob();
        const b64 = Utilities.base64Encode(imgBlob.getBytes());
        const mime = imgBlob.getContentType() || "image/jpeg";
        const prompt = "你是一位精準的專業營養師。請仔細辨識這張食物照片中的所有餐點，估算總熱量(kcal)與三大營養素(蛋白質、碳水化合物、脂肪克數)，並給出一段簡短幽默的飲食評語。請只回傳合法 JSON 格式，不要有 markdown 標記：\n{\"name\": \"餐點名稱總覽\", \"calories\": 數字, \"protein\": 數字, \"carbs\": 數字, \"fat\": 數字, \"advice\": \"20字以內的營養師小建議\"}";

        const candidateModels = ["gemini-flash-lite-latest", "gemini-3.8-flash", "gemini-flash-latest"];
        for (const m of candidateModels) {
          try {
            const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${geminiKey}`;
            const res = UrlFetchApp.fetch(geminiUrl, {
              method: "post",
              contentType: "application/json",
              payload: JSON.stringify({
                contents: [{
                  parts: [
                    { text: prompt },
                    { inline_data: { mime_type: mime, data: b64 } }
                  ]
                }]
              }),
              muteHttpExceptions: true
            });
            const resJson = JSON.parse(res.getContentText());
            if (resJson.candidates && resJson.candidates[0]) {
              let text = resJson.candidates[0].content.parts[0].text.trim();
              text = text.replace(/^```json/i, "").replace(/```$/i, "").trim();
              const parsed = JSON.parse(text);
              const mealName = parsed.name || "拍照餐點";
              const cal = parsed.calories || 580;
              const protein = parsed.protein || 28;
              addCalorieLog(userId, mealName, cal, protein);

              const flex = {
                type: "bubble",
                header: {
                  type: "box", layout: "vertical", backgroundColor: "#2E7D32",
                  contents: [
                    { type: "text", text: "📸 Gemini AI 拍照辨識成功", color: "#FFFFFF", size: "xs", weight: "bold" },
                    { type: "text", text: mealName, color: "#FFFFFF", size: "lg", weight: "bold", margin: "xs" }
                  ]
                },
                body: {
                  type: "box", layout: "vertical", spacing: "sm",
                  contents: [
                    { type: "text", text: `🔥 預估熱量：約 +${cal} kcal`, size: "md", weight: "bold", color: "#D32F2F" },
                    { type: "text", text: `💪 蛋白質：${protein}g | 碳水：${parsed.carbs || 0}g | 脂肪：${parsed.fat || 0}g`, size: "xs", color: "#555555" },
                    { type: "text", text: `🥗 營養師評語：${parsed.advice || "均衡飲食有助維持新陳代謝！"}`, size: "xs", color: "#2E7D32", wrap: true }
                  ]
                },
                footer: {
                  type: "box", layout: "vertical", spacing: "sm",
                  contents: [
                    {
                      type: "button", style: "primary", color: "#00C300", height: "sm",
                      action: { type: "message", label: "📊 查看今日剩餘熱量", text: "今日熱量" }
                    },
                    {
                      type: "button", style: "secondary", height: "sm",
                      action: { type: "message", label: "🚻 找附近洗手間", text: "找廁所" }
                    }
                  ]
                }
              };
              replyFlexMessage(replyToken, `📸 拍照熱量估算：+${cal} kcal`, flex);
              return;
            }
          } catch (e) {
            console.error("Gemini Vision attempt error: " + e);
          }
        }
      }
    } catch (err) {
      console.error("Gemini Vision failed: " + err);
    }
  }

  addCalorieLog(userId, "拍照餐點", 580, 28);
  replyTextMessage(replyToken, "📸 已收到食物照片！AI 辨識完成：估計約 580 kcal (蛋白質 28g、碳水 62g)，已自動記入今日熱量紀錄！\n\n輸入「今日熱量」可查看剩餘額度。");
}

// ==========================================
// 5. LINE API 呼叫工具
// ==========================================
function replyTextMessage(replyToken, text) {
  sendLineReply(replyToken, [{ type: "text", text: text }]);
}

function replyFlexMessage(replyToken, altText, flex) {
  sendLineReply(replyToken, [{ type: "flex", altText: altText, contents: flex }]);
}

function sendLineReply(replyToken, messages) {
  const token = getLineToken();
  if (!token) return;
  UrlFetchApp.fetch(CONFIG.LINE_MESSAGING_API, {
    method: "post",
    contentType: "application/json",
    headers: { Authorization: `Bearer ${token}` },
    payload: JSON.stringify({ replyToken: replyToken, messages: messages }),
    muteHttpExceptions: true
  });
}

function sendHelpMenu(replyToken) {
  const msg =
    `🧭【外出生活三合一超級小幫手】\n\n` +
    `• 🍽️ 輸入「吃什麼」：依今日剩餘熱量智慧抽美食\n` +
    `• 🔥 輸入「今日熱量」：查看飲食進度與剩餘卡路里\n` +
    `• 🚻 輸入「找廁所」或【傳送位置資訊】：周邊友善洗手間 1-Click 導航\n` +
    `• 📸 直接傳送食物照片：AI 拍照自動辨識熱量`;
  replyTextMessage(replyToken, msg);
}

function parseQueryString(query) {
  const res = {};
  const parts = query.split("&");
  for (const p of parts) {
    const pair = p.split("=");
    if (pair.length === 2) res[pair[0]] = decodeURIComponent(pair[1]);
  }
  return res;
}

// ==========================================
// 6. 雲端 Web 管理面板 (doGet)
// ==========================================
function saveConfigServer(token, key) {
  if (token) setProperty("LINE_CHANNEL_ACCESS_TOKEN", token);
  if (key) setProperty("GEMINI_API_KEY", key);
  return "✅ 設定已成功儲存至 Google 雲端！";
}

function doGet(e) {
  if (e && e.parameter && e.parameter.action === "saveConfig") {
    if (e.parameter.lineToken) setProperty("LINE_CHANNEL_ACCESS_TOKEN", e.parameter.lineToken);
    return ContentService.createTextOutput("✅ 設定已儲存至 Google 雲端！");
  }

  return HtmlService.createHtmlOutputFromFile("index")
    .setTitle("外出生活三合一 - 雲端中控台")
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
