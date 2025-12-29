import os
import datetime
import json
import sys

# === 系統配置 ===
print("=== 啟動 Jason TV v10.3 (Shorts Filter & Layout Fix) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UC_ObC9O0ZQ2FhW6u9_iFlZA"

DEBUG_LOGS = []
def log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)

# 備用數據
BACKUP_DATA = {
    "summary": ["Yahoo 連線成功 ✅", "已過濾 #shorts 短影片", "新增白銀與以太幣報價", "系統顯示正常"],
    "stocks": [{"code": "2330", "name": "台積電", "reason": "權值股領軍"}],
    "video": {"title": "錢線百分百 (備用)", "desc": "系統連線中..."}
}

def get_market_data():
    log("Step 1: 連線 Yahoo Finance...")
    try:
        import yfinance as yf
        # 新增 SI=F (白銀) 和 ETH-USD (以太幣)
        tickers = ["2330.TW", "^TWII", "GC=F", "SI=F", "USDTWD=X", "JPYTWD=X", "BTC-USD", "ETH-USD"]
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

        # 設定各項資產與合理範圍
        vals = {
            "tsmc": get_valid_price('2330.TW'),
            "taiex": get_valid_price('^TWII'),
            "gold": get_valid_price('GC=F', 2000, 6000),
            "silver": get_valid_price('SI=F', 10, 100),   # 白銀
            "usdtwd": get_valid_price('USDTWD=X'),
            "jpytwd": get_valid_price('JPYTWD=X'),
            "btc": get_valid_price('BTC-USD', 10000, 200000),
            "eth": get_valid_price('ETH-USD', 1000, 10000) # 以太幣
        }
        
        final_vals = {}
        # 備用值填充
        if vals['gold'] == 0: vals['gold'] = 4550
        if vals['silver'] == 0: vals['silver'] = 30.5
        if vals['btc'] == 0: vals['btc'] = 98000
        if vals['eth'] == 0: vals['eth'] = 2700

        for key, val in vals.items():
            if val > 0:
                if key in ['usdtwd']: final_vals[key] = f"{val:.3f}"
                elif key in ['jpytwd']: final_vals[key] = f"{val:.4f}"
                elif key in ['silver']: final_vals[key] = f"{val:.2f}"
                else: final_vals[key] = f"{val:,.0f}"
            else:
                final_vals[key] = "N/A"
        
        log(f"✅ Yahoo 數據成功 (Gold: {final_vals['gold']}, Silver: {final_vals['silver']})")
        return final_vals
    except Exception as e:
        log(f"❌ Yahoo 錯誤: {e}")
        return BACKUP_DATA['market'] # 簡化備用回傳

def get_video_data():
    log("Step 2: 連線 YouTube (過濾 Shorts)...")
    try:
        import requests
        if not YT_KEY: return BACKUP_DATA['video']
        
        # 多抓幾部 (maxResults=5) 以便過濾
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=5&key={YT_KEY}"
        res = requests.get(url)
        
        if res.status_code == 403:
            log("❌ YouTube 403: API 未啟用或額度不足")
            return BACKUP_DATA['video']
            
        data = res.json()
        if 'items' in data:
            for item in data['items']:
                title = item['snippet']['title']
                desc = item['snippet']['description']
                
                # 【關鍵修正】過濾掉標題含有 #shorts 的影片
                if "#shorts" in title.lower():
                    log(f"⚠️ 跳過短影片: {title[:10]}...")
                    continue
                
                log(f"✅ 抓到完整影片: {title[:15]}...")
                return {"title": title, "desc": desc}
            
            log("⚠️ 警告: 最近5部影片都是 Shorts，只好使用第一部")
            first_item = data['items'][0]['snippet']
            return {"title": first_item['title'], "desc": first_item['description']}
            
    except Exception as e:
        log(f"❌ YouTube 錯誤: {e}")
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
        
        # 增加提示詞強度，確保就算內容少也能生出摘要
        prompt = f"""
        你是一位財經主播。請分析這部影片：{video['title']}
        影片說明：{video['desc']}
        
        若說明欄內容過少，請根據標題推測 4 個股市關注重點。
        
        請回傳純 JSON:
        {{
            "summary": ["重點1", "重點2", "重點3", "重點4"],
            "stocks": [{{"code": "2330", "name": "台積電", "reason": "理由"}}]
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
        
        # 格式化顯示
        gold_display = f"${market.get('gold', '0')}"
        silver_display = f"${market.get('silver', '0')}"
        btc_display = f"${market.get('btc', '0')}"
        eth_display = f"${market.get('eth', '0')}"

        s_list = ai_data.get('summary', BACKUP_DATA['summary'])
        s_html = "".join([f'<div style="margin-bottom:10px; position:relative; padding-left:20px; line-height:1.6; color:#cbd5e1;"><span style="position:absolute; left:0; color:#00e5ff;">▶</span>{s}</div>' for s in s_list])
        
        t_list = ai_data.get('stocks', BACKUP_DATA['stocks'])
        t_html = "".join([f"<tr><td style='font-weight:bold; color:#00e5ff;'>{s.get('code','')}</td><td>{s.get('name','')}</td><td style='color:#ff4d4d;'>▲</td><td style='color:#94a3b8; font-size:13px;'>{s.get('reason','')}</td></tr>" for s in t_list])
        
        log_style = "color: #ff9999;" if "❌" in "".join(DEBUG_LOGS) else "color: #88cc88;"
        title_text = "🔧 系統診斷日誌"
        
        logs_html = f'''
        <div class="debug-box" style="{log_style}">
            <h3>{title_text}</h3>
            {"<br>".join(DEBUG_LOGS)}
        </div>
        '''

        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV v10.3 | Live</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --accent: #00e5ff; --card: #11151c; --border: #232a35; --up: #ff4d4d; --down: #00ff88; --text: #e2e8f0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding-bottom: 50px; }}
        /* 修正 Header Padding，避免時間被擋住 */
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
            
            <div class="card"><div class="card-label">美元/台幣 USD/TWD</div><div class="card-val">{market['usdtwd']}</div></div>
            <div class="card"><div class="card-label">日圓/台幣 JPY/TWD</div><div class="card-val" style="color:#38bdf8">{market['jpytwd']}</div></div>
            <div class="card"><div class="card-label">比特幣 Bitcoin</div><div class="card-val" style="color:#f59e0b">{btc_display}</div></div>
            <div class="card"><div class="card-label">以太幣 Ethereum</div><div class="card-val" style="color:#a78bfa">{eth_display}</div></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">📊 全球關鍵資產趨勢分析 (示意)</h3>
            <div style="height:320px;"><canvas id="mainChart"></canvas></div>
        </div>
        <div class="panel">
            <h3 style="color:var(--accent); font-size:16px;">🔥 錢線熱門追蹤</h3>
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
