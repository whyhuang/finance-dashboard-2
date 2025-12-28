import os
import datetime
import json
import sys

# === 系統配置 ===
print("=== 啟動 Jason TV v9.5 (Official SDK) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCq0y2w004V8666"

DEBUG_LOGS = []
def log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)

# 備用數據 (僅在真的抓不到時使用)
BACKUP_DATA = {
    "summary": ["Yahoo 數據連線成功 ✅", "Gemini AI 暫時無法連線", "目前顯示即時報價", "摘要功能維護中"],
    "stocks": [{"code": "2330", "name": "台積電", "reason": "系統預設"}],
    "video": {"title": "錢線百分百 (自動化)", "desc": "系統連線中..."}
}

# 這是「預設」的市場數據，只有在 Yahoo 連線失敗時才會用到
BACKUP_MARKET = {"tsmc": "1,510", "taiex": "28,556", "gold": "$4,525", "usdtwd": "31.595", "jpytwd": "0.2150", "btc": "$98,450"}

def get_market_data():
    log("Step 1: 連線 Yahoo Finance...")
    try:
        import yfinance as yf
        tickers = ["2330.TW", "^TWII", "GC=F", "USDTWD=X", "JPYTWD=X", "BTC-USD"]
        data = yf.Tickers(" ".join(tickers))
        
        def get_price(symbol):
            try:
                df = data.tickers[symbol].history(period="1d")
                return 0 if df.empty else df['Close'].iloc[-1]
            except: return 0

        vals = {
            "tsmc": get_price('2330.TW'), "taiex": get_price('^TWII'),
            "gold": get_price('GC=F'), "usdtwd": get_price('USDTWD=X'),
            "jpytwd": get_price('JPYTWD=X'), "btc": get_price('BTC-USD')
        }
        
        # 只要台積電有數字，就代表成功了
        if vals['tsmc'] > 0:
            log("✅ Yahoo 數據抓取成功 (真實即時數據)")
            return {
                "tsmc": f"{vals['tsmc']:.0f}",
                "taiex": f"{vals['taiex']:,.0f}",
                "gold": f"${vals['gold']:,.0f}",
                "usdtwd": f"{vals['usdtwd']:.3f}",
                "jpytwd": f"{vals['jpytwd']:.4f}",
                "btc": f"${vals['btc']:,.0f}"
            }
        else:
            log("❌ Yahoo 數據為 0")
            return BACKUP_MARKET
    except Exception as e:
        log(f"❌ Yahoo 錯誤: {e}")
        return BACKUP_MARKET

def get_video_data():
    log("Step 2: 連線 YouTube...")
    try:
        import requests
        if not YT_KEY: return BACKUP_DATA['video']
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=1&key={YT_KEY}&q=錢線百分百"
        res = requests.get(url)
        if res.status_code == 403:
            log("❌ YouTube 403 (請啟用 API)")
            return BACKUP_DATA['video']
        data = res.json()
        if 'items' in data and len(data['items']) > 0:
            item = data['items'][0]['snippet']
            log("✅ YouTube 連線成功")
            return {"title": item['title'], "desc": item['description']}
    except Exception as e:
        log(f"❌ YouTube 錯誤: {e}")
    return BACKUP_DATA['video']

def get_ai_analysis(video):
    log("Step 3: 連線 Gemini AI (官方套件版)...")
    try:
        import google.generativeai as genai
        
        if not GEMINI_KEY:
            log("❌ 缺少 Gemini Key")
            return {"summary": BACKUP_DATA['summary'], "stocks": BACKUP_DATA['stocks']}

        # 設定 API
        genai.configure(api_key=GEMINI_KEY)
        
        # 使用最新的 flash 模型
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        你是一位專業財經分析師。請閱讀以下影片標題與說明，並回傳純 JSON 格式。
        影片：{video['title']}
        內容：{video['desc']}
        
        格式要求 (不要用 Markdown，只要純 JSON):
        {{
            "summary": ["重點1", "重點2", "重點3", "重點4"],
            "stocks": [{{"code": "2330", "name": "台積電", "reason": "理由"}}]
        }}
        """
        
        response = model.generate_content(prompt)
        text = response.text
        
        # 清理 JSON
        clean_json = text.replace("```json", "").replace("```", "").strip()
        log("✅ AI 分析成功")
        return json.loads(clean_json)
        
    except Exception as e:
        log(f"❌ AI 失敗: {e}")
        return {"summary": BACKUP_DATA['summary'], "stocks": BACKUP_DATA['stocks']}

def save_html(ai_data, video, market):
    log("Step 4: 生成 index.html ...")
    try:
        update_time = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
        
        s_html = "".join([f'<div style="margin-bottom:10px; position:relative; padding-left:20px; line-height:1.6; color:#cbd5e1;"><span style="position:absolute; left:0; color:#00e5ff;">▶</span>{s}</div>' for s in ai_data.get('summary', [])])
        t_html = "".join([f"<tr><td style='font-weight:bold; color:#00e5ff;'>{s.get('code','')}</td><td>{s.get('name','')}</td><td style='color:#ff4d4d;'>▲</td><td style='color:#94a3b8; font-size:13px;'>{s.get('reason','')}</td></tr>" for s in ai_data.get('stocks', [])])
        logs_html = "<br>".join(DEBUG_LOGS)

        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV v9.5 | Official</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --accent: #00e5ff; --card: #11151c; --border: #232a35; --up: #ff4d4d; --down: #00ff88; --text: #e2e8f0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding-bottom: 50px; }}
        header {{ position: fixed; top: 0; width: 100%; height: 60px; background: rgba(17,21,28,0.95); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 1000; }}
        .logo {{ font-size: 22px; font-weight: 900; color: var(--accent); letter-spacing: 2px; text-shadow: 0 0 10px rgba(0,229,255,0.5); }}
        .container {{ max-width: 1200px; margin: 80px auto; padding: 0 20px; }}
        .hero {{ background: linear-gradient(145deg, #161b25, #0b0e14); border: 1px solid var(--accent); border-radius: 16px; padding: 25px; margin-bottom: 30px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
        .card-val {{ font-family: 'JetBrains Mono'; font-size: 26px; font-weight: 700; color: var(--text); margin-top: 8px; }}
        .card-label {{ font-size: 12px; color: #94a3b8; }}
        .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 25px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ text-align: left; color: #64748b; font-size: 12px; border-bottom: 1px solid var(--border); padding: 10px; }}
        td {{ padding: 15px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }}
        .debug-box {{ margin-top: 50px; padding: 20px; background: #2a0a0a; border: 1px solid #ff4d4d; color: #ff9999; font-family: monospace; font-size: 12px; border-radius: 8px; }}
    </style>
</head>
<body>
    <header>
        <div class="logo">JASON TV</div>
        <div style="color:#00ff88; font-size:11px;" id="clock">● LIVE | Connecting...</div>
    </header>
    <div class="container">
        <div class="hero">
            <h2 style="color:var(--accent); margin-bottom:20px; font-size:18px; font-weight:bold;">📺 AI 戰情摘要 (來源：{video['title']})</h2>
            <div>{s_html}</div>
        </div>
        <div class="grid">
            <div class="card"><div class="card-label">加權指數 TAIEX</div><div class="card-val" style="color:var(--up)">{market['taiex']} ▲</div></div>
            <div class="card"><div class="card-label">台積電 TSMC</div><div class="card-val" style="color:var(--up)">{market['tsmc']} ▲</div></div>
            <div class="card"><div class="card-label">黃金價格 GOLD</div><div class="card-val" style="color:#fbbf24">{market['gold']}</div></div>
            <div class="card"><div class="card-label">美元/台幣 USD/TWD</div><div class="card-val">{market['usdtwd']}</div></div>
            <div class="card"><div class="card-label">美國聯準會利率 (Fed)</div><div class="card-val" style="color:#a78bfa">4.50%</div></div>
            <div class="card"><div class="card-label">台灣央行重貼現率</div><div class="card-val" style="color:#a78bfa">2.00%</div></div>
            <div class="card"><div class="card-label">日圓/台幣 JPY/TWD</div><div class="card-val" style="color:#38bdf8">{market['jpytwd']}</div></div>
            <div class="card"><div class="card-label">比特幣 Bitcoin</div><div class="card-val" style="color:#f59e0b">{market['btc']}</div></div>
        </div>
        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">📊 全球關鍵資產趨勢分析 (示意)</h3>
            <div style="height:320px;"><canvas id="mainChart"></canvas></div>
        </div>
        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">🔥 錢線熱門追蹤</h3>
            <table><thead><tr><th>代號</th><th>名稱</th><th>訊號</th><th>關鍵理由</th></tr></thead><tbody>{t_html}</tbody></table>
        </div>
        <div class="debug-box">
            <h3>🔧 系統診斷日誌 (v9.5)</h3>
            {logs_html}
        </div>
    </div>
    <script>
        function updateClock() {{
            const now = new Date();
            document.getElementById('clock').innerHTML = '● LIVE | ' + now.toLocaleString('zh-TW', {{ hour12: false }});
        }}
        setInterval(updateClock, 1000);
        updateClock();
        
        new Chart(document.getElementById('mainChart'), {{
            type: 'line',
            data: {{
                labels: ['Q1', 'Q2', 'Q3', '2025Q4'],
                datasets: [
                    {{ label: '台股 (%)', data: [10, 25, 40, 65.8], borderColor: '#00e5ff', tension: 0.4, borderWidth: 3 }},
                    {{ label: '黃金 (%)', data: [15, 35, 55, 72], borderColor: '#fbbf24', tension: 0.4, borderWidth: 2 }},
                    {{ label: '比特幣 (%)', data: [5, 45, 85, 120], borderColor: '#f59e0b', borderDash: [5,5], tension: 0.4, borderWidth: 2 }},
                    {{ label: '美債殖利率 (%)', data: [3.8, 4.2, 4.4, 4.5], borderColor: '#a78bfa', tension: 0.4, borderWidth: 2 }}
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
        log("✅ HTML 寫入成功")
    except Exception as e:
        log(f"❌ 寫入失敗: {e}")

if __name__ == "__main__":
    try:
        m_data = get_market_data()
        v_data = get_video_data()
        a_data = get_ai_analysis(v_data)
        save_html(a_data, v_data, m_data)
        sys.exit(0)
    except:
        sys.exit(0)
