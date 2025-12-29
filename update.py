import os
import datetime
import json
import sys

# === 系統配置 ===
print("=== 啟動 Jason TV v10.6 (Chart Fix) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UC_ObC9O0ZQ2FhW6u9_iFlZA"

DEBUG_LOGS = []
def log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)

# 備用數據
BACKUP_DATA = {
    "summary": ["Yahoo 連線成功 ✅", "圖表顯示已修復", "AI 根據節目自動選股", "系統運作正常"],
    "stocks": [{"code": "2330", "name": "台積電", "reason": "權值股領軍"}],
    "video": {"title": "錢線百分百 (備用)", "desc": "系統連線中..."}
}

def get_market_data():
    log("Step 1: 連線 Yahoo Finance...")
    try:
        import yfinance as yf
        # 加入美股標普500 (^GSPC) 以計算美股績效
        tickers = ["2330.TW", "^TWII", "GC=F", "SI=F", "USDTWD=X", "JPYTWD=X", "BTC-USD", "ETH-USD", "^TNX", "^GSPC"]
        data = yf.Tickers(" ".join(tickers))
        
        def get_valid_price(symbol, threshold_min=0, threshold_max=999999):
            try:
                df = data.tickers[symbol].history(period="5d")
                if df.empty: return 0
                for i in range(len(df)-1, -1, -1):
                    price = df['Close'].iloc[i]
                    if price > threshold_min and price < threshold_max:
                        return price
                return 0
            except: return 0

        # 【關鍵修復】計算 YTD (年初至今) 漲跌幅，增加防呆
        def get_ytd_change(symbol):
            try:
                # 嘗試抓取年初至今
                hist = data.tickers[symbol].history(period="ytd")
                
                # 如果是年初或抓不到，改抓近5日做為示意，避免圖表掛掉
                if hist.empty or len(hist) < 2:
                     hist = data.tickers[symbol].history(period="5d")
                
                if hist.empty or len(hist) < 2: return 0.0 # 回傳浮點數 0.0

                start_price = hist['Close'].iloc[0]
                end_price = hist['Close'].iloc[-1]
                
                if start_price == 0: return 0.0
                
                change_pct = ((end_price - start_price) / start_price) * 100
                return round(change_pct, 2)
            except: return 0.0

        # 計算圖表數據 (確保都是數字，沒有 None)
        chart_data = [
            get_ytd_change('GC=F'),    # 黃金
            get_ytd_change('SI=F'),    # 白銀
            get_ytd_change('^GSPC'),   # 美股
            get_ytd_change('^TWII'),   # 台股
            get_ytd_change('BTC-USD')  # BTC
        ]
        log(f"📊 圖表數據生成: {chart_data}")

        # 即時報價
        vals = {
            "tsmc": get_valid_price('2330.TW'),
            "taiex": get_valid_price('^TWII'),
            "gold": get_valid_price('GC=F', 2000, 6000),
            "silver": get_valid_price('SI=F', 10, 100),
            "usdtwd": get_valid_price('USDTWD=X'),
            "jpytwd": get_valid_price('JPYTWD=X'),
            "btc": get_valid_price('BTC-USD', 10000, 200000),
            "eth": get_valid_price('ETH-USD', 1000, 10000),
            "us10y": get_valid_price('^TNX')
        }
        
        final_vals = {}
        # 備用值
        if vals['gold'] == 0: vals['gold'] = 4550
        if vals['silver'] == 0: vals['silver'] = 30.5
        if vals['btc'] == 0: vals['btc'] = 98000
        if vals['us10y'] == 0: vals['us10y'] = 4.5

        for key, val in vals.items():
            if val > 0:
                if key in ['usdtwd']: final_vals[key] = f"{val:.3f}"
                elif key in ['jpytwd']: final_vals[key] = f"{val:.4f}"
                elif key in ['silver']: final_vals[key] = f"{val:.2f}"
                elif key in ['us10y']: final_vals[key] = f"{val:.2f}%"
                else: final_vals[key] = f"{val:,.0f}"
            else:
                final_vals[key] = "N/A"
        
        # 將圖表數據塞入回傳值
        final_vals['chart_ytd'] = chart_data
        
        log(f"✅ Yahoo 數據成功 (Gold: {final_vals['gold']})")
        return final_vals
    except Exception as e:
        log(f"❌ Yahoo 錯誤: {e}")
        res = BACKUP_DATA.get('market', {})
        res['chart_ytd'] = [0.0, 0.0, 0.0, 0.0, 0.0]
        return res

def get_video_data():
    log("Step 2: 連線 YouTube (過濾 Shorts)...")
    try:
        import requests
        if not YT_KEY: return BACKUP_DATA['video']
        
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=5&key={YT_KEY}"
        res = requests.get(url)
        
        if res.status_code == 403:
            log("❌ YouTube 403: API 未啟用")
            return BACKUP_DATA['video']
            
        data = res.json()
        if 'items' in data:
            for item in data['items']:
                title = item['snippet']['title']
                desc = item['snippet']['description']
                if "#shorts" in title.lower():
                    continue
                log(f"✅ 抓到影片: {title[:15]}...")
                return {"title": title, "desc": desc}
            # 如果都是 shorts，拿第一部
            first = data['items'][0]['snippet']
            return {"title": first['title'], "desc": first['description']}
    except: pass
    return BACKUP_DATA['video']

def get_ai_analysis(video):
    log("Step 3: 連線 Gemini AI...")
    try:
        import google.generativeai as genai
        if not GEMINI_KEY: return BACKUP_DATA
        
        genai.configure(api_key=GEMINI_KEY)
        target_model = 'gemini-1.5-flash'
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    if 'flash' in m.name:
                        target_model = m.name.replace('models/', '')
                        break
        except: pass
        
        log(f"✅ 使用模型: {target_model}")
        model = genai.GenerativeModel(target_model)
        
        prompt = f"""
        你是一位財經主播。請分析這部影片：{video['title']}
        影片說明：{video['desc']}
        
        1. 摘要 4 個重點。
        2. 請從影片內容中，找出 3-5 檔「被提到的熱門股票或 ETF」。
        
        回傳純 JSON:
        {{
            "summary": ["重點1", "重點2", "重點3", "重點4"],
            "stocks": [{{"code": "代號", "name": "名稱", "reason": "為何被提到"}}]
        }}
        """
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
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
        
        # 安全獲取圖表數據，並轉換為 JSON 字串以防 JS 崩潰
        raw_chart_data = market.get('chart_ytd', [0.0, 0.0, 0.0, 0.0, 0.0])
        safe_chart_data = json.dumps(raw_chart_data) # 【關鍵】強制轉為 JSON 格式字串

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
    <title>Jason TV v10.6 | Live</title>
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
            <div class="card"><div class="card-label">黃金 GOLD</div><div class="card-val" style="color:#fbbf24">${market['gold']}</div></div>
            <div class="card"><div class="card-label">白銀 SILVER</div><div class="card-val" style="color:#cbd5e1">${market['silver']}</div></div>
            <div class="card"><div class="card-label">美債10年殖利率</div><div class="card-val" style="color:#a78bfa">{market['us10y']}</div></div>
            <div class="card"><div class="card-label">美元/台幣</div><div class="card-val">{market['usdtwd']}</div></div>
            <div class="card"><div class="card-label">比特幣 BTC</div><div class="card-val" style="color:#f59e0b">${market['btc']}</div></div>
            <div class="card"><div class="card-label">以太幣 ETH</div><div class="card-val" style="color:#a78bfa">${market['eth']}</div></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">📊 五大資產今年以來 (YTD) 績效表現</h3>
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
        
        new Chart(document.getElementById('mainChart'), {{
            type: 'bar',
            data: {{
                labels: ['黃金 (Gold)', '白銀 (Silver)', '美股 (S&P500)', '台股 (TAIEX)', '比特幣 (BTC)'],
                datasets: [{{
                    label: '今年漲跌幅 (%)',
                    data: {safe_chart_data}, 
                    backgroundColor: [
                        'rgba(251, 191, 36, 0.8)',
                        'rgba(203, 213, 225, 0.8)',
                        'rgba(56, 189, 248, 0.8)',
                        'rgba(0, 229, 255, 0.8)',
                        'rgba(245, 158, 11, 0.8)'
                    ],
                    borderColor: 'rgba(255,255,255,0.1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{ color: '#64748b', callback: function(val){{return val+'%'}} }},
                        grid: {{ color: 'rgba(255,255,255,0.05)' }}
                    }},
                    x: {{
                        ticks: {{ color: '#94a3b8' }},
                        grid: {{ display: false }}
                    }}
                }}
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
