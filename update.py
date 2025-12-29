import os
import datetime
import json
import sys
import numpy as np # 確保處理數據

# === 系統配置 ===
print("=== 啟動 Jason TV v10.7 (Stable AI & Line Chart) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UC_ObC9O0ZQ2FhW6u9_iFlZA"

DEBUG_LOGS = []
def log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)

# 備用數據
BACKUP_DATA = {
    "summary": ["Yahoo 連線成功 ✅", "AI 模型已鎖定穩定版", "圖表改為年度走勢比較", "BTC 數據運算修正"],
    "stocks": [{"code": "2330", "name": "台積電", "reason": "權值股領軍"}],
    "video": {"title": "錢線百分百 (備用)", "desc": "系統連線中..."}
}

def get_market_data():
    log("Step 1: 連線 Yahoo Finance...")
    try:
        import yfinance as yf
        tickers = ["2330.TW", "^TWII", "GC=F", "SI=F", "USDTWD=X", "JPYTWD=X", "BTC-USD", "ETH-USD", "^TNX", "^GSPC"]
        data = yf.Tickers(" ".join(tickers))
        
        # 1. 獲取即時價格
        def get_current_price(symbol):
            try:
                df = data.tickers[symbol].history(period="5d")
                if df.empty: return 0
                return df['Close'].iloc[-1]
            except: return 0

        # 2. 【關鍵升級】獲取過去 1 年的走勢數據 (每月一點)
        def get_trend_data(symbol):
            try:
                # 抓取 1 年歷史，間隔為 1 個月
                hist = data.tickers[symbol].history(period="1y", interval="1mo")
                if hist.empty: return [0]*12
                
                # 正規化：以第一個月為基準 (0%)，計算後續漲跌幅
                start_price = hist['Close'].iloc[0]
                if start_price == 0: return [0]*12
                
                trend = []
                for price in hist['Close']:
                    pct_change = ((price - start_price) / start_price) * 100
                    trend.append(round(pct_change, 2))
                
                # 確保只有 12 個點 (避免圖表太長)
                return trend[-12:] 
            except: return [0]*12

        # 準備圖表數據 (五大資產)
        chart_series = {
            "gold": get_trend_data('GC=F'),
            "silver": get_trend_data('SI=F'),
            "us_stock": get_trend_data('^GSPC'),
            "tw_stock": get_trend_data('^TWII'),
            "btc": get_trend_data('BTC-USD')
        }
        
        # 檢查 BTC 數據 (Debug)
        log(f"📊 BTC 走勢數據 (最後3個月): {chart_series['btc'][-3:]}")

        # 即時報價
        vals = {
            "tsmc": get_current_price('2330.TW'),
            "taiex": get_current_price('^TWII'),
            "gold": get_current_price('GC=F'),
            "silver": get_current_price('SI=F'),
            "usdtwd": get_current_price('USDTWD=X'),
            "jpytwd": get_current_price('JPYTWD=X'),
            "btc": get_current_price('BTC-USD'),
            "eth": get_current_price('ETH-USD'),
            "us10y": get_current_price('^TNX')
        }
        
        # 數據防呆與備用值
        final_vals = {}
        if vals['gold'] == 0: vals['gold'] = 4550
        if vals['btc'] == 0: vals['btc'] = 98000

        for key, val in vals.items():
            if val > 0:
                if key in ['usdtwd']: final_vals[key] = f"{val:.3f}"
                elif key in ['jpytwd']: final_vals[key] = f"{val:.4f}"
                elif key in ['silver']: final_vals[key] = f"{val:.2f}"
                elif key in ['us10y']: final_vals[key] = f"{val:.2f}%"
                else: final_vals[key] = f"{val:,.0f}"
            else:
                final_vals[key] = "N/A"
        
        # 將圖表數據打包
        final_vals['chart_data'] = chart_series
        
        log(f"✅ Yahoo 數據成功")
        return final_vals
    except Exception as e:
        log(f"❌ Yahoo 錯誤: {e}")
        return BACKUP_DATA.get('market', {})

def get_video_data():
    log("Step 2: 連線 YouTube (過濾 Shorts)...")
    try:
        import requests
        if not YT_KEY: return BACKUP_DATA['video']
        
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=5&key={YT_KEY}"
        res = requests.get(url)
        data = res.json()
        if 'items' in data:
            for item in data['items']:
                title = item['snippet']['title']
                desc = item['snippet']['description']
                if "#shorts" in title.lower(): continue
                log(f"✅ 抓到影片: {title[:15]}...")
                return {"title": title, "desc": desc}
    except: pass
    return BACKUP_DATA['video']

def get_ai_analysis(video):
    log("Step 3: 連線 Gemini AI...")
    try:
        import google.generativeai as genai
        if not GEMINI_KEY: return BACKUP_DATA
        
        genai.configure(api_key=GEMINI_KEY)
        
        # 【關鍵修復】強制使用 1.5-flash，不讓它自動選最新的不穩定版
        target_model = 'gemini-1.5-flash'
        log(f"✅ 強制鎖定模型: {target_model}")
        model = genai.GenerativeModel(target_model)
        
        prompt = f"""
        你是一位財經主播。請分析這部影片：{video['title']}
        影片說明：{video['desc']}
        
        請回傳純 JSON (不要任何 Markdown 標記，只要 JSON):
        {{
            "summary": ["重點1", "重點2", "重點3", "重點4"],
            "stocks": [{{"code": "2330", "name": "台積電", "reason": "理由"}}]
        }}
        """
        response = model.generate_content(prompt)
        
        # 強力清洗 JSON (去除 ```json 等標記)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("\n", 1)[0]
        
        log("✅ AI 分析成功")
        return json.loads(text)
    except Exception as e:
        log(f"❌ AI 失敗: {e}")
        return BACKUP_DATA

def save_html(ai_data, video, market):
    log("Step 4: 生成 HTML...")
    try:
        tz = datetime.timezone(datetime.timedelta(hours=8))
        update_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")
        
        # 準備 Chart.js 數據
        chart_series = market.get('chart_data', {})
        # 轉成 JSON 字串供 JS 使用
        json_gold = json.dumps(chart_series.get('gold', []))
        json_silver = json.dumps(chart_series.get('silver', []))
        json_us = json.dumps(chart_series.get('us_stock', []))
        json_tw = json.dumps(chart_series.get('tw_stock', []))
        json_btc = json.dumps(chart_series.get('btc', []))

        s_list = ai_data.get('summary', BACKUP_DATA['summary'])
        s_html = "".join([f'<div style="margin-bottom:10px; position:relative; padding-left:20px; line-height:1.6; color:#cbd5e1;"><span style="position:absolute; left:0; color:#00e5ff;">▶</span>{s}</div>' for s in s_list])
        
        t_list = ai_data.get('stocks', BACKUP_DATA['stocks'])
        t_html = "".join([f"<tr><td style='font-weight:bold; color:#00e5ff;'>{s.get('code','')}</td><td>{s.get('name','')}</td><td style='color:#ff4d4d;'>▲</td><td style='color:#94a3b8; font-size:13px;'>{s.get('reason','')}</td></tr>" for s in t_list])
        
        log_style = "color: #ff9999;" if "❌" in "".join(DEBUG_LOGS) else "color: #88cc88;"
        logs_html = f'<div class="debug-box" style="{log_style}"><h3>🔧 系統診斷日誌</h3>{"<br>".join(DEBUG_LOGS)}</div>'

        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV v10.7 | Live</title>
    <script src="[https://cdn.jsdelivr.net/npm/chart.js](https://cdn.jsdelivr.net/npm/chart.js)"></script>
    <link href="[https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap](https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap)" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --accent: #00e5ff; --card: #11151c; --border: #232a35; --up: #ff4d4d; --down: #00ff88; --text: #e2e8f0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding-bottom: 50px; }}
        header {{ position: fixed; top: 0; width: 100%; height: 60px; background: rgba(17,21,28,0.95); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 30px; z-index: 1000; box-sizing: border-box; }}
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
        .debug-box {{ margin-top: 50px; padding: 20px; background: #2a0a0a; border: 1px solid #333; font-family: monospace; font-size: 12px; border-radius: 8px; }}
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
            <div class="card"><div class="card-label">黃金 GOLD</div><div class="card-val" style="color:#fbbf24">${market['gold']}</div></div>
            <div class="card"><div class="card-label">白銀 SILVER</div><div class="card-val" style="color:#cbd5e1">${market['silver']}</div></div>
            <div class="card"><div class="card-label">美債10年殖利率</div><div class="card-val" style="color:#a78bfa">{market['us10y']}</div></div>
            <div class="card"><div class="card-label">美元/台幣</div><div class="card-val">{market['usdtwd']}</div></div>
            <div class="card"><div class="card-label">比特幣 BTC</div><div class="card-val" style="color:#f59e0b">${market['btc']}</div></div>
            <div class="card"><div class="card-label">以太幣 ETH</div><div class="card-val" style="color:#a78bfa">${market['eth']}</div></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">📊 五大資產過去一年走勢比較 (Trend %)</h3>
            <div style="height:350px;"><canvas id="mainChart"></canvas></div>
        </div>
        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">🔥 錢線熱門追蹤 (AI 自動選股)</h3>
            <table><thead><tr><th>代號</th><th>名稱</th><th>訊號</th><th>關鍵理由</th></tr></thead><tbody>{t_html}</tbody></table>
        </div>
        {logs_html}
    </div>
    <script>
        function updateClock() {{
            const now = new Date();
            document.getElementById('clock').innerHTML = '● LIVE | ' + now.toLocaleString('zh-TW', {{ hour12: false }});
        }}
        setInterval(updateClock, 1000);
        updateClock();
        
        // 折線圖配置
        const ctx = document.getElementById('mainChart').getContext('2d');
        // 產生過去12個月的標籤 (簡易版)
        const labels = Array.from({{length: 12}}, (_, i) => i + 1 + '月');

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [
                    {{ label: '比特幣 (BTC)', data: {json_btc}, borderColor: '#f59e0b', borderWidth: 3, tension: 0.4 }},
                    {{ label: '台股 (TAIEX)', data: {json_tw}, borderColor: '#00e5ff', borderWidth: 2, tension: 0.4 }},
                    {{ label: '美股 (S&P500)', data: {json_us}, borderColor: '#38bdf8', borderWidth: 2, tension: 0.4 }},
                    {{ label: '黃金 (Gold)', data: {json_gold}, borderColor: '#fbbf24', borderWidth: 2, tension: 0.4 }},
                    {{ label: '白銀 (Silver)', data: {json_silver}, borderColor: '#cbd5e1', borderWidth: 1, tension: 0.4, borderDash: [5,5] }}
                ]
            }},
            options: {{
                maintainAspectRatio: false,
                plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }},
                scales: {{
                    y: {{
                        grid: {{ color: 'rgba(255,255,255,0.05)' }},
                        ticks: {{ color: '#64748b', callback: function(val){{return val+'%'}} }}
                    }},
                    x: {{ grid: {{ display: false }}, ticks: {{ color: '#64748b' }} }}
                }},
                elements: {{ point: {{ radius: 0, hitRadius: 10 }} }} // 隱藏點，讓線條更平滑
            }}
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
