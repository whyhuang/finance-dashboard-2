import os
import requests
import datetime
import json
import random

# 讀取金鑰
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCq0y2w004V8666"

def get_data():
    """步驟 1: 嘗試抓取 YouTube 資料"""
    print("Fetching YouTube Data...")
    try:
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=1&key={YT_KEY}&q=錢線百分百"
        res = requests.get(url).json()
        if 'items' in res and len(res['items']) > 0:
            item = res['items'][0]['snippet']
            return {
                "title": item['title'],
                "desc": item['description'],
                "date": item['publishedAt'][:10]
            }
    except Exception as e:
        print(f"YouTube Error: {e}")
    
    # 備用資料
    return {
        "title": "錢線百分百 (備用源)",
        "desc": "無法連線至 YouTube，顯示預設數據。重點關注：台積電法說、AI 伺服器供應鏈、元月行情。",
        "date": datetime.datetime.now().strftime("%Y-%m-%d")
    }

def analyze(video_data):
    """步驟 2: 請 Gemini 分析並回傳 JSON"""
    print("Analyzing with Gemini...")
    prompt = f"""
    請閱讀影片資訊：{video_data['title']} \n {video_data['desc']}
    
    請回傳純 JSON (不要Markdown)，包含：
    1. "summary": [4個繁體中文重點]
    2. "stocks": [3個物件 {{"code": "代號", "name": "股名", "reason": "理由"}}] (若找不到則列出台積電/鴻海/聯發科)
    3. "gold_price": "4,525" (請固定此數值)
    """
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
        text = res['candidates'][0]['content']['parts'][0]['text']
        clean_json = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"Gemini Error: {e}")
        # 發生錯誤時的回傳預設值 (保證網頁不會壞)
        return {
            "summary": ["外資休假內資主導，指數高檔震盪", "AI 伺服器需求續強，供應鏈受惠", "元月行情啟動，關注中小型補漲股", "避險資金推升金價，留意回檔風險"],
            "stocks": [
                {"code": "2330", "name": "台積電", "reason": "先進製程滿載"},
                {"code": "2454", "name": "聯發科", "reason": "天璣晶片熱銷"},
                {"code": "2317", "name": "鴻海", "reason": "GB200 出貨順暢"}
            ],
            "gold_price": "4,525"
        }

def make_html(ai, video):
    """步驟 3: 生成 v7.0 完整旗艦版 HTML"""
    print("Generating HTML...")
    
    # 生成摘要 HTML
    summary_html = "".join([f'<div class="summary-item">{s}</div>' for s in ai.get('summary', [])])
    
    # 生成表格 HTML
    rows_html = ""
    for s in ai.get('stocks', []):
        rows_html += f"""
        <tr>
            <td style="font-weight:bold; color:#00e5ff;">{s.get('code','')}</td>
            <td>{s.get('name','')}</td>
            <td style="color:#ff4d4d;">看多</td>
            <td style="color:#94a3b8; font-size:13px;">{s.get('reason','')}</td>
        </tr>"""

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 這裡是真正的 Flagship HTML 模板 (包含所有 CSS 樣式)
    html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV v7.0 | AI 旗艦終端</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --card: #11151c; --accent: #00e5ff; --up: #ff4d4d; --text: #e2e8f0; --border: #232a35; }}
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding-bottom: 60px; }}
        
        /* 導航欄 */
        header {{ position: fixed; top: 0; width: 100%; height: 60px; background: rgba(17,21,28,0.95); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 1000; }}
        .logo {{ font-size: 24px; font-weight: 900; color: var(--accent); letter-spacing: 2px; text-shadow: 0 0 15px rgba(0,229,255,0.4); }}
        
        .container {{ max-width: 1200px; margin: 80px auto 0; padding: 0 20px; }}
        
        /* 摘要區 */
        .hero-summary {{ background: linear-gradient(145deg, #161b25, #0b0e14); border: 1px solid var(--accent); border-radius: 16px; padding: 25px; margin-bottom: 30px; box-shadow: 0 0 20px rgba(0,229,255,0.1); }}
        .summary-title {{ color: var(--accent); font-size: 18px; margin-bottom: 15px; font-weight: bold; }}
        .summary-item {{ margin-bottom: 10px; font-size: 15px; padding-left: 20px; position: relative; color: #cbd5e1; line-height: 1.6; }}
        .summary-item::before {{ content: '▶'; position: absolute; left: 0; color: var(--accent); top: 4px; }}
        
        /* 數據卡片 */
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
        .card-val {{ font-family: 'JetBrains Mono'; font-size: 28px; font-weight: 700; margin-top: 8px; }}
        
        /* 表格與圖表區 */
        .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 25px; margin-bottom: 20px; }}
        .panel-h {{ color: var(--accent); font-size: 16px; margin-bottom: 20px; font-weight: bold; border-left: 3px solid var(--accent); padding-left: 10px; }}
        
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; color: #64748b; padding: 12px 8px; border-bottom: 1px solid var(--border); font-size: 13px; }}
        td {{ padding: 15px 8px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 15px; }}
    </style>
</head>
<body>
    <header>
        <div class="logo">JASON TV</div>
        <div style="font-size:12px; color:#00ff88;">● AUTO LIVE | {now}</div>
    </header>

    <div class="container">
        <div class="hero-summary">
            <div class="summary-title">📺 AI 智能摘要 (來源: {video['title']})</div>
            {summary_html}
        </div>

        <div class="grid">
            <div class="card">
                <div style="font-size:12px; color:#94a3b8;">加權指數 TAIEX</div>
                <div class="card-val" style="color:var(--up);">28,556 ▲</div>
            </div>
            <div class="card">
                <div style="font-size:12px; color:#94a3b8;">台積電 TSMC</div>
                <div class="card-val" style="color:var(--up);">1,510 ▲</div>
            </div>
            <div class="card">
                <div style="font-size:12px; color:#94a3b8;">黃金 (GOLD)</div>
                <div class="card-val" style="color:#fbbf24;">${ai.get('gold_price', '4,525')}</div>
            </div>
            <div class="card">
                <div style="font-size:12px; color:#94a3b8;">美元/台幣</div>
                <div class="card-val">31.595</div>
            </div>
        </div>

        <div class="panel">
            <div class="panel-h">📊 年度資產趨勢分析</div>
            <div style="height: 300px; width: 100%;">
                <canvas id="mainChart"></canvas>
            </div>
        </div>

        <div class="panel">
            <div class="panel-h">🔥 錢線熱門股追蹤</div>
            <table>
                <thead><tr><th>代號</th><th>名稱</th><th>訊號</th><th>關鍵理由</th></tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('mainChart').getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(0, 229, 255, 0.2)');
        gradient.addColorStop(1, 'rgba(0, 229, 255, 0)');
        
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: ['Q1', 'Q2', 'Q3', '2025Q4'],
                datasets: [
                    {{ label: '台股 (%)', data: [10, 25, 40, 65.8], borderColor: '#00e5ff', backgroundColor: gradient, fill: true, tension: 0.4 }},
                    {{ label: '黃金 (%)', data: [15, 35, 55, 72], borderColor: '#fbbf24', borderDash: [5,5], tension: 0.4 }}
                ]
            }},
            options: {{ maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }}, scales: {{ y: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}, x: {{ ticks: {{ color: '#64748b' }}, grid: {{ display: false }} }} }} }}
        }});
    </script>
</body>
</html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML Written Successfully")

if __name__ == "__main__":
    v_data = get_data()
    ai_data = analyze(v_data)
    make_html(ai_data, v_data)
