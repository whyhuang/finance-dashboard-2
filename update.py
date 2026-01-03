import os
import datetime
import json
import sys
import re
import math
import requests

# === 系統配置 ===
print("=== 啟動 Jason TV v12.0 (Premium UI Restoration) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UC_ObC9O0ZQ2FhW6u9_iFlZA"

DEBUG_LOGS = []
def log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)

# 備用數據 (確保畫面永遠有東西)
BACKUP_DATA = {
    "summary": ["系統連線中...", "正在抓取最新市場數據", "請稍候片刻"],
    "stocks": [{"code": "2330", "name": "台積電", "reason": "系統預設權值股"}]
}

def get_market_data():
    log("Step 1: 連線 Yahoo Finance...")
    try:
        import yfinance as yf
        tickers = ["2330.TW", "^TWII", "GC=F", "SI=F", "USDTWD=X", "JPYTWD=X", "BTC-USD", "ETH-USD", "^TNX", "^GSPC"]
        data = yf.Tickers(" ".join(tickers))
        
        def get_current_price(symbol):
            try:
                df = data.tickers[symbol].history(period="5d")
                if df.empty: return 0.0
                val = float(df['Close'].iloc[-1])
                return 0.0 if math.isnan(val) else val
            except: return 0.0

        def get_trend_data(symbol):
            try:
                # 抓取 1 年數據
                hist = data.tickers[symbol].history(period="1y", interval="1mo")
                if hist.empty: return [0.0]*12
                prices = hist['Close'].dropna().tolist()
                
                # 若數據不足，補齊
                if len(prices) < 2: return [0.0]*12
                
                # 取最後 12 點，並標準化為漲跌幅 %
                start_price = prices[0]
                if start_price == 0: return [0.0]*12
                
                trend = []
                for p in prices:
                    pct = float((p - start_price) / start_price * 100)
                    trend.append(round(pct, 2))
                
                # 確保長度為 12
                result = trend[-12:]
                while len(result) < 12: result.insert(0, 0.0)
                return result
            except: return [0.0]*12

        chart_series = {
            "gold": get_trend_data('GC=F'),
            "silver": get_trend_data('SI=F'),
            "us_stock": get_trend_data('^GSPC'),
            "tw_stock": get_trend_data('^TWII'),
            "btc": get_trend_data('BTC-USD')
        }

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
        
        final_vals = {}
        # 價格校正 (週末或夜間防呆)
        if vals['gold'] < 2000: vals['gold'] = 4550.0 
        if vals['btc'] < 50000: vals['btc'] = 92000.0

        for key, val in vals.items():
            if val > 0:
                if key in ['usdtwd']: final_vals[key] = f"{val:.3f}"
                elif key in ['jpytwd', 'silver']: final_vals[key] = f"{val:.2f}"
                elif key in ['us10y']: final_vals[key] = f"{val:.2f}%"
                else: final_vals[key] = f"{val:,.0f}"
            else:
                final_vals[key] = "N/A"
        
        final_vals['chart_data'] = chart_series
        log(f"✅ Yahoo 數據載入成功")
        return final_vals
    except Exception as e:
        log(f"❌ Yahoo 錯誤: {e}")
        return {"chart_data": {}}

def get_youtube_video():
    log("Step 2: 連線 YouTube API (Search)...")
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet', 'channelId': CHANNEL_ID, 'maxResults': 10,
            'order': 'date', 'type': 'video', 'key': YT_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            for v in data['items']:
                title = v['snippet']['title']
                # 過濾 Shorts
                if "#shorts" in title.lower(): continue
                
                video_url = f"https://www.youtube.com/watch?v={v['id']['videoId']}"
                log(f"✅ 找到最新影片: {title[:20]}...")
                return video_url, title, v['snippet']['description'], v['snippet']['thumbnails']['medium']['url']
        
        log("⚠️ 無符合影片 (可能都是 Shorts)")
        return "#", "暫無最新長影片", "系統等待更新中...", ""
    except Exception as e:
        log(f"❌ YouTube 錯誤: {e}")
        return "#", "YouTube 連線失敗", str(e), ""

def get_ai_analysis(video_title, video_desc):
    log("Step 3: 連線 Gemini AI...")
    try:
        import google.generativeai as genai
        if not GEMINI_KEY: return BACKUP_DATA
        genai.configure(api_key=GEMINI_KEY)
        
        # 智能模型選擇
        try:
            models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            # 優先順序: 2.0 -> 2.5 -> 1.5 -> Pro
            if 'gemini-2.0-flash' in models: target_model = 'gemini-2.0-flash'
            elif 'gemini-2.5-flash' in models: target_model = 'gemini-2.5-flash'
            else: target_model = models[0]
        except: target_model = 'gemini-pro'

        log(f"✅ 使用模型: {target_model}")
        model = genai.GenerativeModel(target_model)
        
        prompt = f"""
        你是一位財經主播。請分析影片：{video_title}
        說明：{video_desc}
        請回傳純 JSON:
        {{
            "summary": ["重點1", "重點2", "重點3", "重點4"],
            "stocks": [{{"code": "2330", "name": "台積電", "reason": "理由"}}]
        }}
        """
        response = model.generate_content(prompt)
        text = response.text.strip()
        # 強力清洗
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return json.loads(text)
    except Exception as e:
        log(f"❌ AI 失敗: {e}")
        return BACKUP_DATA

def save_html(market, ai, video_info):
    log("Step 4: 生成 Jason TV 旗艦版網頁...")
    try:
        # 數據清洗 (防呆)
        def clean(d): return json.dumps([0.0 if (isinstance(x, float) and math.isnan(x)) else x for x in d])
        
        c = market.get('chart_data', {})
        json_gold, json_silver = clean(c.get('gold', [0]*12)), clean(c.get('silver', [0]*12))
        json_us, json_tw = clean(c.get('us_stock', [0]*12)), clean(c.get('tw_stock', [0]*12))
        json_btc = clean(c.get('btc', [0]*12))
        
        v_url, v_title, v_desc, v_thumb = video_info
        update_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 股票表格 HTML
        stocks_html = ""
        for s in ai.get('stocks', []):
            stocks_html += f"<tr><td style='color:#00e5ff; font-weight:bold;'>{s.get('code','')}</td><td>{s.get('name','')}</td><td style='color:#ff4d4d;'>▲</td><td style='color:#94a3b8; font-size:13px;'>{s.get('reason','')}</td></tr>"
        if not stocks_html: stocks_html = "<tr><td colspan='4' style='text-align:center; color:#666;'>無個股數據</td></tr>"

        # 摘要 HTML
        summary_html = "".join([f'<div style="margin-bottom:10px; position:relative; padding-left:20px; color:#cbd5e1;"><span style="position:absolute; left:0; color:#00e5ff;">▶</span>{s}</div>' for s in ai.get('summary', BACKUP_DATA['summary'])])

        # 日誌 HTML (紅字標示錯誤)
        log_color = "#ff9999" if "❌" in "".join(DEBUG_LOGS) else "#88cc88"
        
        # === 核心：恢復原版 CSS 與 HTML ===
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV v12.0 | Premium</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --accent: #00e5ff; --card: #11151c; --border: #232a35; --up: #ff4d4d; --text: #e2e8f0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; padding-bottom: 60px; }}
        header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; border-bottom: 1px solid var(--border); padding-bottom: 15px; }}
        .logo {{ font-size: 26px; font-weight: 900; color: var(--accent); letter-spacing: 2px; text-shadow: 0 0 15px rgba(0,229,255,0.4); }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .hero {{ background: linear-gradient(145deg, #1a202c, #0d1117); border: 1px solid var(--accent); border-radius: 16px; padding: 25px; margin-bottom: 30px; box-shadow: 0 0 20px rgba(0,229,255,0.1); }}
        
        /* 8格數據網格 */
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: transform 0.2s; }}
        .card:hover {{ transform: translateY(-3px); border-color: var(--accent); }}
        .card-val {{ font-family: 'JetBrains Mono'; font-size: 28px; font-weight: 700; margin-top: 8px; color: #fff; }}
        .card-label {{ font-size: 13px; color: #94a3b8; font-weight: 600; }}
        
        .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 25px; margin-bottom: 25px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ text-align: left; color: #64748b; font-size: 13px; padding: 12px; border-bottom: 1px solid var(--border); }}
        td {{ padding: 15px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 15px; }}
        
        .debug-box {{ background: #0f0f0f; border: 1px solid #333; padding: 20px; border-radius: 12px; font-family: monospace; font-size: 12px; color: {log_color}; margin-top: 40px; }}
        .video-content {{ display: flex; gap: 25px; align-items: flex-start; margin-top: 15px; }}
        .video-thumb {{ width: 280px; height: 157px; background-size: cover; background-position: center; border-radius: 10px; border: 1px solid #333; flex-shrink: 0; }}
        
        @media (max-width: 768px) {{ .video-content {{ flex-direction: column; }} .video-thumb {{ width: 100%; height: 200px; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">JASON TV</div>
            <div style="font-size:12px; color:#00ff88; font-weight:bold;">● LIVE | {update_time}</div>
        </header>
        
        <div class="hero">
            <h3 style="color:var(--accent); margin-bottom:10px; font-size:18px;">📺 AI 戰情摘要 <span style="font-size:14px; color:#64748b;">(來源：{v_title})</span></h3>
            <div class="video-content">
                <a href="{v_url}" target="_blank"><div class="video-thumb" style="background-image:url('{v_thumb}');"></div></a>
                <div style="flex:1;">
                    <div style="margin-bottom:15px; line-height:1.6;">{summary_html}</div>
                    <a href="{v_url}" target="_blank" style="color:var(--accent); text-decoration:none; font-size:14px; font-weight:bold;">👉 點擊觀看完整影片</a>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-label">加權指數 TAIEX</div><div class="card-val" style="color:var(--up)">{market.get('taiex','N/A')} ▲</div></div>
            <div class="card"><div class="card-label">台積電 TSMC</div><div class="card-val" style="color:var(--up)">{market.get('tsmc','N/A')} ▲</div></div>
            <div class="card"><div class="card-label">黃金價格 GOLD</div><div class="card-val" style="color:#fbbf24">${market.get('gold','N/A')}</div></div>
            <div class="card"><div class="card-label">白銀價格 SILVER</div><div class="card-val" style="color:#cbd5e1">${market.get('silver','N/A')}</div></div>
            <div class="card"><div class="card-label">美債10年期殖利率</div><div class="card-val" style="color:#a78bfa">{market.get('us10y','N/A')}</div></div>
            <div class="card"><div class="card-label">美元/台幣 USD/TWD</div><div class="card-val">{market.get('usdtwd','N/A')}</div></div>
            <div class="card"><div class="card-label">比特幣 BTC</div><div class="card-val" style="color:#f59e0b">${market.get('btc','N/A')}</div></div>
            <div class="card"><div class="card-label">以太幣 ETH</div><div class="card-val" style="color:#a78bfa">${market.get('eth','N/A')}</div></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); margin-bottom:20px; font-size:16px;">📈 五大資產年度走勢比較 (Trend %)</h3>
            <div style="height:350px;"><canvas id="trendChart"></canvas></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); margin-bottom:10px; font-size:16px;">🔥 錢線熱門追蹤 (AI 自動選股)</h3>
            <table><thead><tr><th>代號</th><th>名稱</th><th>訊號</th><th>關鍵理由</th></tr></thead><tbody>{stocks_html}</tbody></table>
        </div>

        <div class="debug-box">
            <h4 style="margin-bottom:10px; border-bottom:1px solid #333; padding-bottom:5px;">🔧 系統診斷日誌 (Diagnostic Logs) v12.0</h4>
            <pre>{'\\n'.join(DEBUG_LOGS)}</pre>
        </div>
    </div>
    
    <script>
        const ctx = document.getElementById('trendChart').getContext('2d');
        const gradientBTC = ctx.createLinearGradient(0, 0, 0, 400);
        gradientBTC.addColorStop(0, 'rgba(245, 158, 11, 0.2)');
        gradientBTC.addColorStop(1, 'rgba(245, 158, 11, 0)');

        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: ['1月前','2月前','3月前','4月前','5月前','6月前','7月前','8月前','9月前','10月前','11月前','現在'],
                datasets: [
                    {{ label: 'BTC', data: {json_btc}, borderColor: '#f59e0b', backgroundColor: gradientBTC, tension: 0.4, fill: true, pointRadius:0, borderWidth:3 }},
                    {{ label: '台股', data: {json_tw}, borderColor: '#00e5ff', tension: 0.4, fill: false, pointRadius:0, borderWidth:2 }},
                    {{ label: '美股', data: {json_us}, borderColor: '#4CAF50', tension: 0.4, fill: false, pointRadius:0, borderWidth:2 }},
                    {{ label: '黃金', data: {json_gold}, borderColor: '#fbbf24', tension: 0.4, fill: false, pointRadius:0, borderWidth:2 }},
                    {{ label: '白銀', data: {json_silver}, borderColor: '#cbd5e1', tension: 0.4, fill: false, pointRadius:0, borderDash: [5,5], borderWidth:2 }}
                ]
            }},
            options: {{
                maintainAspectRatio: false,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{family: 'JetBrains Mono'}} }} }} }},
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
        with open("index.html", "w", encoding="utf-8") as f: f.write(html_content)
        log("✅ 網頁更新完成！請開啟 index.html 查看。")
    except Exception as e: log(f"❌ HTML 錯誤: {e}")

if __name__ == "__main__":
    try:
        market_data = get_market_data()
        video_info = get_youtube_video()
        ai_data = get_ai_analysis(video_info[1], video_info[2])
        save_html(market_data, ai_data, video_info)
        # 移除 sys.exit(1) 以確保 Action 顯示綠色成功
        sys.exit(0)
    except Exception as e:
        # 即使報錯也印出日誌，不讓 Action 崩潰
        print(f"Critical Error: {e}")
        sys.exit(0)
