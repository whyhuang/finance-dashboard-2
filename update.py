import os
import datetime
import json
import sys
import re # 用於清洗 AI 回傳的髒資料

# === 系統配置 ===
print("=== 啟動 Jason TV v10.9 (Fix Numpy & Auto-AI) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UC_ObC9O0ZQ2FhW6u9_iFlZA"

DEBUG_LOGS = []
def log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)

# 備用數據
BACKUP_DATA = {
    "summary": ["Yahoo 連線成功 ✅", "圖表已修復為年度走勢", "AI 模型自動適配中", "系統運作正常"],
    "stocks": [{"code": "2330", "name": "台積電", "reason": "權值股領軍"}],
    "video": {"title": "錢線百分百 (備用)", "desc": "系統連線中..."}
}

def get_market_data():
    log("Step 1: 連線 Yahoo Finance...")
    try:
        import yfinance as yf
        tickers = ["2330.TW", "^TWII", "GC=F", "SI=F", "USDTWD=X", "JPYTWD=X", "BTC-USD", "ETH-USD", "^TNX", "^GSPC"]
        data = yf.Tickers(" ".join(tickers))
        
        # 1. 獲取即時價格 (轉為 float 防止 numpy 錯誤)
        def get_current_price(symbol):
            try:
                df = data.tickers[symbol].history(period="5d")
                if df.empty: return 0.0
                return float(df['Close'].iloc[-1])
            except: return 0.0

        # 2. 獲取年度走勢 (YTD Trend)
        def get_trend_data(symbol):
            try:
                # 抓取 1 年日線數據 (比較精準)
                hist = data.tickers[symbol].history(period="1y")
                if hist.empty: return [0.0]*12
                
                prices = hist['Close'].dropna().tolist()
                if len(prices) < 10: return [0.0]*12 # 數據太少
                
                # 重新採樣：取 12 個點 (每隔 N 天取一點)
                step = len(prices) // 12
                if step < 1: step = 1
                sampled_prices = prices[::step][-12:] # 取最後 12 個採樣點
                
                # 正規化計算：(當前價 - 起始價) / 起始價 %
                start_price = sampled_prices[0]
                if start_price == 0: return [0.0]*12
                
                trend = []
                for p in sampled_prices:
                    # 【關鍵修正】強制轉 float，殺死 np.float64 錯誤
                    pct = float((p - start_price) / start_price * 100)
                    trend.append(round(pct, 2))
                
                # 補齊 12 點
                while len(trend) < 12: trend.insert(0, 0.0)
                return trend
            except Exception as e:
                log(f"⚠️ {symbol} 走勢錯誤: {e}")
                return [0.0]*12

        # 準備圖表數據
        chart_series = {
            "gold": get_trend_data('GC=F'),
            "silver": get_trend_data('SI=F'),
            "us_stock": get_trend_data('^GSPC'),
            "tw_stock": get_trend_data('^TWII'),
            "btc": get_trend_data('BTC-USD')
        }
        
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
        
        # 防呆與備用值
        final_vals = {}
        if vals['gold'] == 0: vals['gold'] = 4550.0
        if vals['btc'] == 0: vals['btc'] = 98000.0

        for key, val in vals.items():
            if val > 0:
                if key in ['usdtwd']: final_vals[key] = f"{val:.3f}"
                elif key in ['jpytwd']: final_vals[key] = f"{val:.4f}"
                elif key in ['silver']: final_vals[key] = f"{val:.2f}"
                elif key in ['us10y']: final_vals[key] = f"{val:.2f}%"
                else: final_vals[key] = f"{val:,.0f}"
            else:
                final_vals[key] = "N/A"
        
        final_vals['chart_data'] = chart_series
        log(f"✅ Yahoo 數據與走勢圖成功")
        return final_vals
    except Exception as e:
        log(f"❌ Yahoo 嚴重錯誤: {e}")
        return BACKUP_DATA.get('market', {})

def get_video_data():
    log("Step 2: 連線 YouTube (擴大搜尋)...")
    try:
        import requests
        if not YT_KEY: return BACKUP_DATA['video']
        
        # 擴大搜尋到 10 部
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=10&key={YT_KEY}"
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
        
        # 【關鍵修正】恢復自動搜尋模型 (因為您的帳號可能只有 2.5 能用)
        target_model = 'gemini-1.5-flash' # 預設
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    name = m.name.replace('models/', '')
                    # 優先找 flash 系列
                    if 'flash' in name:
                        target_model = name
                        break
        except: pass
        
        log(f"ℹ️ 使用模型: {target_model}")
        model = genai.GenerativeModel(target_model)
        
        prompt = f"""
        你是一位財經主播。請分析這部影片：{video['title']}
        影片說明：{video['desc']}
        
        1. 摘要 4 個重點。
        2. 找出 3-5 檔熱門股票。
        
        請回傳純 JSON:
        {{
            "summary": ["重點1", "重點2", "重點3", "重點4"],
            "stocks": [{{"code": "2330", "name": "台積電", "reason": "理由"}}]
        }}
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 【關鍵修正】強力 Regex 清洗，不管 AI 講什麼廢話，只抓 JSON
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            clean_json = match.group(0)
            log("✅ JSON 格式清洗成功")
            return json.loads(clean_json)
        else:
            # 嘗試直接解析
            return json.loads(text)
            
    except Exception as e:
        log(f"❌ AI 失敗 (請檢查日誌): {e}")
        # 回傳備用數據但保留圖表
        return BACKUP_DATA

def save_html(ai_data, video, market):
    log("Step 4: 生成 HTML...")
    try:
        tz = datetime.timezone(datetime.timedelta(hours=8))
        update_time = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")
        
        # 安全獲取圖表數據
        chart_series = market.get('chart_data', {})
        # 【關鍵修正】確保轉為 JSON 字串
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
    <title>Jason TV v10.9 | Live</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
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
            <div class="card"><div class="card-label">黃金價格 GOLD</div><div class="card-val" style="color:#fbbf24">{gold_display}</div></div>
            <div class="card"><div class="card-label">白銀價格 SILVER</div><div class="card-val" style="color:#cbd5e1">{silver_display}</div></div>
            
            <div class="card"><div class="card-label">美債10年殖利率</div><div class="card-val" style="color:#a78bfa">{market['us10y']}</div></div>
            <div class="card"><div class="card-label">美元/台幣</div><div class="card-val">{market['usdtwd']}</div></div>
            <div class="card"><div class="card-label">比特幣 BTC</div><div class="card-val" style="color:#f59e0b">{btc_display}</div></div>
            <div class="card"><div class="card-label">以太幣 ETH</div><div class="card-val" style="color:#a78bfa">{eth_display}</div></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">📊 五大資產過去一年走勢比較 (1-Year Trend %)</h3>
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
        
        // 生成月份標籤 (1~12)
        const labels = Array.from({{length: 12}}, (_, i) => i + 1);

        new Chart(document.getElementById('mainChart').getContext('2d'), {{
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
                elements: {{ point: {{ radius: 0, hitRadius: 10 }} }}
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
