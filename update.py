import os
import requests
import datetime
import json
import re

# 讀取金鑰
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCq0y2w004V8666" # 非凡財經頻道 ID

def get_latest_video_data():
    """使用 YouTube API 抓取最新影片的標題與描述"""
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=1&key={YT_KEY}&q=錢線百分百"
    try:
        res = requests.get(url).json()
        if 'items' in res and len(res['items']) > 0:
            item = res['items'][0]['snippet']
            return {
                "title": item['title'],
                "desc": item['description'],
                "date": item['publishedAt'][:10]
            }
    except Exception as e:
        print(f"YouTube API Error: {e}")
    
    # 如果抓取失敗的備案
    return {
        "title": "錢線百分百 (自動抓取備份)",
        "desc": "今日市場關注台積電、AI 伺服器與元月行情佈局。",
        "date": datetime.datetime.now().strftime("%Y-%m-%d")
    }

def analyze_with_gemini(video_data):
    """請 Gemini 讀取影片資訊，並吐出『JSON 格式』的數據給網頁用"""
    
    # 這是給 AI 的精確指令
    prompt = f"""
    你是專業的財經數據分析師。請閱讀以下 YouTube 影片資訊，並提取關鍵數據生成 JSON 格式回應。
    
    影片標題: {video_data['title']}
    影片描述: {video_data['desc']}
    目前金價參考: $4,525 (歷史新高)
    目前台股參考: 28,556 (創高)

    請回傳一個純 JSON 物件 (不要有 markdown 標記)，格式如下：
    {{
        "summary": ["重點1...", "重點2...", "重點3...", "重點4..."],
        "hot_stocks": [
            {{"code": "2330", "name": "台積電", "reason": "法說會展望佳"}},
            {{"code": "xxxx", "name": "股票名稱", "reason": "簡短看漲理由"}}
        ],
        "market_sentiment": "up" 
    }}
    注意：
    1. summary 請提供 4 點繁體中文摘要。
    2. hot_stocks 請從描述中尋找提及的強勢股，若無則提供台積電、鴻海、聯發科等權值股作為預設。
    """

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, json=payload).json()
        text_response = res['candidates'][0]['content']['parts'][0]['text']
        # 清理可能存在的 markdown 符號
        clean_json = text_response.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        # 發生錯誤時的回傳備案
        return {
            "summary": ["外資休假內資當家，台股持續高檔震盪", "元月行情啟動，關注低基期補漲股", "AI 伺服器需求強勁，供應鏈受惠", "金價維持高檔，避險資金未退"],
            "hot_stocks": [
                {"code": "2330", "name": "台積電", "reason": "權值龍頭撐盤"},
                {"code": "2454", "name": "聯發科", "reason": "旗艦晶片熱銷"},
                {"code": "2317", "name": "鴻海", "reason": "AI 伺服器出貨"}
            ],
            "market_sentiment": "up"
        }

def generate_html(ai_data, video_data):
    """將 AI 資料填入 v5.2 旗艦版 HTML 模板"""
    
    # 處理摘要列表 HTML
    summary_html = ""
    for item in ai_data['summary']:
        summary_html += f'<div class="summary-item">{item}</div>'
    
    # 處理熱門股表格 HTML
    stocks_html = ""
    for stock in ai_data['hot_stocks']:
        stocks_html += f"""
        <tr>
            <td><b>{stock['code']}</b></td>
            <td>{stock['name']}</td>
            <td style="color:var(--up)">看多</td>
            <td>{stock['reason']}</td>
        </tr>
        """

    # 準備時間
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 完整的 v5.2 HTML 代碼
    html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV | AI 智能財經終端</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --card: #11151c; --accent: #00e5ff; --up: #ff4d4d; --down: #00ff88; --text: #e2e8f0; --border: #232a35; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); overflow-x: hidden; padding-bottom: 40px; }}
        
        header {{ position: fixed; top: 0; width: 100%; height: 60px; background: rgba(17, 21, 28, 0.95); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 1000; }}
        .logo {{ font-size: 24px; font-weight: 900; color: var(--accent); letter-spacing: 2px; text-shadow: 0 0 15px rgba(0, 229, 255, 0.4); }}
        .status {{ font-family: 'JetBrains Mono'; font-size: 11px; color: var(--down); }}

        .container {{ max-width: 1200px; margin: 80px auto 0; padding: 0 20px; }}
        
        /* 摘要區塊 */
        .hero-summary {{ background: linear-gradient(145deg, #161b25, #0b0e14); border: 1px solid var(--accent); border-radius: 16px; padding: 25px; margin-bottom: 30px; box-shadow: 0 0 25px rgba(0, 229, 255, 0.05); }}
        .hero-title {{ color: var(--accent); font-size: 18px; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; font-weight: bold; }}
        .summary-item {{ margin-bottom: 12px; font-size: 15px; line-height: 1.6; padding-left: 20px; position: relative; color: #cbd5e1; }}
        .summary-item::before {{ content: '▶'; position: absolute; left: 0; color: var(--accent); font-size: 12px; top: 4px; }}

        /* 數據卡片 */
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: 0.3s; }}
        .card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
        .card-label {{ font-size: 12px; color: #94a3b8; margin-bottom: 8px; }}
        .card-val {{ font-family: 'JetBrains Mono'; font-size: 26px; font-weight: 700; color: var(--text); }}
        .card-sub {{ font-size: 11px; margin-top: 5px; color: #64748b; }}

        /* 雙欄佈局 */
        .data-section {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
        .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 25px; }}
        .panel-title {{ color: var(--accent); font-size: 16px; margin-bottom: 20px; font-weight: bold; }}
        
        /* 表格 */
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; font-size: 12px; color: #64748b; padding-bottom: 10px; border-bottom: 1px solid var(--border); }}
        td {{ padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }}

        @media (max-width: 900px) {{ .data-section {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <header>
        <div class="logo">JASON TV</div>
        <div class="status">● AI AUTO UPDATE | {now_str}</div>
    </header>

    <div class="container">
        <div class="hero-summary">
            <div class="hero-title">📺 錢線百分百・AI 戰情摘要</div>
            {summary_html}
            <div style="margin-top:15px; font-size:12px; color:#64748b; text-align:right;">資料來源：{video_data['title']}</div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-label">加權指數 TAIEX</div>
                <div class="card-val" style="color:var(--up)">28,556 ▲</div>
                <div class="card-sub">歷史新高 | 成交量 4,428 億</div>
            </div>
            <div class="card">
                <div class="card-label">台積電 TSMC</div>
                <div class="card-val" style="color:var(--up)">1,510 ▲</div>
                <div class="card-sub">權值龍頭領軍上攻</div>
            </div>
            <div class="card">
                <div class="card-label">黃金價格 GOLD</div>
                <div class="card-val" style="color:#fbbf24">$4,525</div>
                <div class="card-sub" style="color:var(--up)">+72% YTD 歷史新高</div>
            </div>
            <div class="card">
                <div class="card-label">美元/台幣 USD/TWD</div>
                <div class="card-val">31.595</div>
                <div class="card-sub">台幣緩步升值</div>
            </div>
        </div>

        <div class="data-section">
            <div class="panel">
                <div class="panel-title">📊 年度關鍵資產走勢</div>
                <div style="height: 300px; width: 100%;">
                    <canvas id="mainChart"></canvas>
                </div>
            </div>

            <div class="panel">
                <div class="panel-title">🔥 錢線熱門追蹤</div>
                <table>
                    <thead><tr><th>代號</th><th>名稱</th><th>訊號</th><th>關鍵理由</th></tr></thead>
                    <tbody>
                        {stocks_html}
                    </tbody>
                </table>
            </div>
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
                    {{ 
                        label: '台股加權 (%)', data: [10, 25, 40, 65.8], 
                        borderColor: '#00e5ff', backgroundColor: gradient, fill: true, tension: 0.4 
                    }},
                    {{ 
                        label: '黃金 (%)', data: [15, 35, 55, 72], 
                        borderColor: '#fbbf24', borderDash: [5, 5], tension: 0.4 
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#94a3b8' }} }} }},
                scales: {{
                    y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }}, ticks: {{ color: '#64748b' }} }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#64748b' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
    """
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    # 1. 抓取資料
    video_data = get_latest_video_data()
    print(f"Found Video: {{video_data['title']}}")
    
    # 2. AI 分析
    ai_data = analyze_with_gemini(video_data)
    print("AI Analysis Complete.")
    
    # 3. 生成網頁
    generate_html(ai_data, video_data)
    print("HTML Generated.")
