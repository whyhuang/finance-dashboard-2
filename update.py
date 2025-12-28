import os
import requests
import datetime
import json

# 1. 讀取金鑰
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCq0y2w004V8666"

def get_video_data():
    """抓取 YouTube 資料"""
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=1&key={YT_KEY}&q=錢線百分百"
    try:
        res = requests.get(url).json()
        item = res['items'][0]['snippet']
        return {"title": item['title'], "desc": item['description']}
    except:
        # 若抓取失敗，回傳備用數據
        return {"title": "錢線百分百 (備用源)", "desc": "台積電法說展望佳，AI 伺服器供應鏈續強，關注央行利率政策與元月行情。"}

def get_ai_analysis(video):
    """請 Gemini 分析摘要與個股"""
    prompt = f"請閱讀影片：{video['title']} \n內容：{video['desc']} \n回傳純 JSON (無Markdown)：{{'summary': ['4個重點'], 'stocks': [{{'code':'代號','name':'股名','reason':'原因'}}]}}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
        text = res['candidates'][0]['content']['parts'][0]['text']
        clean_json = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except:
        return {
            "summary": ["外資休假內資主導，指數高檔震盪", "聯準會維持利率不變，市場預期明年降息", "元月行情啟動，鎖定低基期補漲股", "避險資金湧入，金價支撐強勁"],
            "stocks": [{"code": "2330", "name": "台積電", "reason": "先進製程滿載"}]
        }

def save_to_index(ai_data, video):
    """生成 v8.0 擴充版網頁"""
    update_time = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    
    # HTML 內容生成
    s_html = "".join([f'<div style="margin-bottom:8px; position:relative; padding-left:20px;"><span style="position:absolute; left:0; color:#00e5ff;">▶</span>{s}</div>' for s in ai_data.get('summary', [])])
    t_html = "".join([f"<tr><td style='font-weight:bold; color:#00e5ff;'>{s.get('code','')}</td><td>{s.get('name','')}</td><td style='color:#ff4d4d;'>▲</td><td style='color:#94a3b8; font-size:13px;'>{s.get('reason','')}</td></tr>" for s in ai_data.get('stocks', [])])

    html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV v8.0 | 全球財經戰情室</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --accent: #00e5ff; --card: #11151c; --border: #232a35; --up: #ff4d4d; --text: #e2e8f0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding-bottom: 50px; }}
        
        /* 導航 */
        header {{ position: fixed; top: 0; width: 100%; height: 60px; background: rgba(17,21,28,0.95); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 1000; }}
        .logo {{ font-size: 22px; font-weight: 900; color: var(--accent); letter-spacing: 2px; text-shadow: 0 0 10px rgba(0,229,255,0.5); }}
        
        .container {{ max-width: 1200px; margin: 80px auto; padding: 0 20px; }}
        
        /* 摘要區 */
        .hero {{ background: linear-gradient(145deg, #161b25, #0b0e14); border: 1px solid var(--accent); border-radius: 16px; padding: 25px; margin-bottom: 30px; box-shadow: 0 0 20px rgba(0,229,255,0.05); }}
        
        /* 數據網格 (改為自動適應，可容納更多卡片) */
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: 0.3s; }}
        .card:hover {{ border-color: var(--accent); transform: translateY(-3px); }}
        .card-label {{ font-size: 12px; color: #94a3b8; margin-bottom: 5px; }}
        .card-val {{ font-family: 'JetBrains Mono'; font-size: 24px; font-weight: 700; color: var(--text); }}
        
        /* 表格與圖表 */
        .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ text-align: left; color: #64748b; font-size: 12px; border-bottom: 1px solid var(--border); padding: 10px; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }}
    </style>
</head>
<body>
    <header>
        <div class="logo">JASON TV</div>
        <div style="color:#00ff88; font-size:11px;">● LIVE | {update_time}</div>
    </header>

    <div class="container">
        <div class="hero">
            <h2 style="color:var(--accent); margin-bottom:15px; font-size:18px;">📺 AI 戰情摘要 (來源：{video['title']})</h2>
            <div style="line-height:1.6; color:#cbd5e1;">{s_html}</div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-label">加權指數 TAIEX</div><div class="card-val" style="color:var(--up)">28,556 ▲</div></div>
            <div class="card"><div class="card-label">台積電 TSMC</div><div class="card-val" style="color:var(--up)">1,510 ▲</div></div>
            <div class="card"><div class="card-label">黃金價格 GOLD</div><div class="card-val" style="color:#fbbf24">$4,525</div></div>
            <div class="card"><div class="card-label">美元/台幣 USD/TWD</div><div class="card-val">31.595</div></div>
            <div class="card"><div class="card-label">美國聯準會利率 (Fed)</div><div class="card-val" style="color:#a78bfa">4.50%</div></div>
            <div class="card"><div class="card-label">台灣央行重貼現率</div><div class="card-val" style="color:#a78bfa">2.00%</div></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">📊 年度資產趨勢 (台股 vs 黃金)</h3>
            <div style="height:280px;"><canvas id="mainChart"></canvas></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">🔥 錢線熱門追蹤</h3>
            <table><thead><tr><th>代號</th><th>名稱</th><th>訊號</th><th>關鍵理由</th></tr></thead><tbody>{t_html}</tbody></table>
        </div>
    </div>

    <script>
        new Chart(document.getElementById('mainChart'), {{
            type: 'line',
            data: {{
                labels: ['Q1', 'Q2', 'Q3', '2025Q4'],
                datasets: [
                    {{ label: '台股 (%)', data: [10, 25, 40, 65.8], borderColor: '#00e5ff', backgroundColor: 'rgba(0,229,255,0.1)', fill: true, tension: 0.4 }},
                    {{ label: '黃金 (%)', data: [15, 35, 55, 72], borderColor: '#fbbf24', borderDash: [5,5], tension: 0.4 }}
                ]
            }},
            options: {{ maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }}, scales: {{ y: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}, x: {{ ticks: {{ color: '#64748b' }}, grid: {{ display: false }} }} }} }}
        }});
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    v = get_video_data()
    a = get_ai_analysis(v)
    save_to_index(a, v)
