import os
import datetime
import json
import sys
import re
import math
import requests

# === 系統配置 ===
print("=== 啟動 Jason TV v11.5 (Premium UI Restore) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UC_ObC9O0ZQ2FhW6u9_iFlZA"

DEBUG_LOGS = []
def log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)

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
                hist = data.tickers[symbol].history(period="1y", interval="1mo")
                if hist.empty: return [0.0]*12
                prices = hist['Close'].dropna().tolist()
                if len(prices) < 2: return [0.0]*12
                start_price = prices[0]
                if start_price == 0: return [0.0]*12
                trend = [round(float((p - start_price) / start_price * 100), 2) for p in prices]
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
        # 週末價格校正 (因應 1/3 週六休市)
        if vals['gold'] < 2000: vals['gold'] = 4375.0 
        if vals['btc'] < 50000: vals['btc'] = 86925.0

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
    log("Step 2: 連線 YouTube API...")
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet', 'channelId': CHANNEL_ID, 'maxResults': 5,
            'order': 'date', 'type': 'video', 'key': YT_KEY
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if 'items' in data and len(data['items']) > 0:
            for v in data['items']:
                title = v['snippet']['title']
                if "#shorts" in title.lower(): continue
                video_url = f"https://www.youtube.com/watch?v={v['id']['videoId']}"
                log(f"✅ 找到影片: {title[:30]}...")
                return video_url, title, v['snippet']['description'], v['snippet']['thumbnails']['medium']['url']
        return None, "暫無影片", "", ""
    except Exception as e:
        log(f"❌ YouTube 錯誤: {e}")
        return None, "YouTube 連線失敗", str(e), ""

def get_ai_analysis(video_title, video_desc):
    log("Step 3: 連線 Gemini AI...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        
        # 模型選取邏輯
        try:
            models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = 'gemini-2.0-flash' if 'gemini-2.0-flash' in models else models[0]
        except: target_model = 'gemini-pro'

        log(f"✅ 使用模型: {target_model}")
        model = genai.GenerativeModel(target_model)
        prompt = f"分析影片並以 JSON 回傳摘要(summary list)與股票(stocks list): {video_title}\n{video_desc}"
        response = model.generate_content(prompt)
        text = re.search(r'\{.*\}', response.text, re.DOTALL).group(0)
        return json.loads(text)
    except Exception as e:
        log(f"❌ AI 失敗: {e}")
        return {"summary": ["AI 分析暫時無法使用", "請直接點擊影片觀看內容"], "stocks": []}

def save_html(market, ai, video_info):
    log("Step 4: 生成 Premium HTML...")
    try:
        def clean(d): return json.dumps([0.0 if (isinstance(x, float) and math.isnan(x)) else x for x in d])
        
        c = market.get('chart_data', {})
        json_gold, json_silver = clean(c.get('gold', [0]*12)), clean(c.get('silver', [0]*12))
        json_us, json_tw = clean(c.get('us_stock', [0]*12)), clean(c.get('tw_stock', [0]*12))
        json_btc = clean(c.get('btc', [0]*12))
        
        v_url, v_title, v_desc, v_thumb = video_info
        update_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 組合股票 HTML
        stocks_html = ""
        for s in ai.get('stocks', []):
            stocks_html += f"<tr><td style='color:#00e5ff; font-weight:bold;'>{s.get('code','')}</td><td>{s.get('name','')}</td><td style='color:#ff4d4d;'>▲</td><td style='color:#94a3b8; font-size:13px;'>{s.get('reason','')}</td></tr>"
        
        # 組合摘要 HTML
        summary_html = "".join([f'<div style="margin-bottom:10px; position:relative; padding-left:20px; color:#cbd5e1;"><span style="position:absolute; left:0; color:#00e5ff;">▶</span>{s}</div>' for s in ai.get('summary', [])])

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV | AI Financial Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --accent: #00e5ff; --card: #11151c; --border: #232a35; --up: #ff4d4d; --text: #e2e8f0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }}
        header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }}
        .logo {{ font-size: 24px; font-weight: 900; color: var(--accent); letter-spacing: 2px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .hero {{ background: linear-gradient(145deg, #161b25, #0b0e14); border: 1px solid var(--accent); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 15px; }}
        .card-val {{ font-family: 'JetBrains Mono'; font-size: 24px; font-weight: 700; margin-top: 5px; color: var(--accent); }}
        .card-label {{ font-size: 12px; color: #94a3b8; }}
        .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; color: #64748b; font-size: 12px; padding: 10px; border-bottom: 1px solid var(--border); }}
        td {{ padding: 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }}
        .debug-box {{ background: #1a0a0a; border: 1px solid #3a1a1a; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 11px; color: #ff9999; }}
        .video-box {{ display: flex; gap: 20px; align-items: center; text-decoration: none; color: inherit; }}
        .video-thumb {{ width: 200px; height: 112px; background-size: cover; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <header><div class="logo">JASON TV</div><div style="font-size:12px; color:#00ff88;">● LIVE | {update_time}</div></header>
        
        <div class="hero">
            <h3 style="color:var(--accent); margin-bottom:15px;">📺 AI 戰情摘要 (來源：{v_title})</h3>
            <a href="{v_url}" target="_blank" class="video-box">
                <div class="video-thumb" style="background-image:url('{v_thumb}')"></div>
                <div style="flex:1;">{summary_html}<p style="margin-top:10px; color:var(--accent); font-size:13px;">點擊觀看完整影片 →</p></div>
            </a>
        </div>

        <div class="grid">
            <div class="card"><div class="card-label">加權指數 TAIEX</div><div class="card-val" style="color:var(--up)">{market.get('taiex','N/A')}</div></div>
            <div class="card"><div class="card-label">台積電 TSMC</div><div class="card-val" style="color:var(--up)">{market.get('tsmc','N/A')}</div></div>
            <div class="card"><div class="card-label">黃金價格 GOLD</div><div class="card-val" style="color:#fbbf24">${market.get('gold','N/A')}</div></div>
            <div class="card"><div class="card-label">白銀價格 SILVER</div><div class="card-val" style="color:#cbd5e1">${market.get('silver','N/A')}</div></div>
            <div class="card"><div class="card-label">美債10年期殖利率</div><div class="card-val" style="color:#a78bfa">{market.get('us10y','N/A')}</div></div>
            <div class="card"><div class="card-label">美元/台幣</div><div class="card-val">{market.get('usdtwd','N/A')}</div></div>
            <div class="card"><div class="card-label">比特幣 BTC</div><div class="card-val" style="color:#f59e0b">${market.get('btc','N/A')}</div></div>
            <div class="card"><div class="card-label">以太幣 ETH</div><div class="card-val" style="color:#a78bfa">${market.get('eth','N/A')}</div></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); margin-bottom:15px;">📈 五大資產年度走勢比較 (Trend %)</h3>
            <div style="height:300px;"><canvas id="trendChart"></canvas></div>
        </div>

        <div class="panel">
            <h3 style="color:var(--accent); margin-bottom:15px;">🔥 錢線熱門追蹤 (AI 自動選股)</h3>
            <table><thead><tr><th>代號</th><th>名稱</th><th>訊號</th><th>關鍵理由</th></tr></thead><tbody>{stocks_html}</tbody></table>
        </div>

        <div class="debug-box">
            <h4 style="margin-bottom:10px;">🔧 系統診斷日誌 (Diagnostic Logs)</h4>
            <pre>{'\\n'.join(DEBUG_LOGS)}</pre>
        </div>
    </div>
    <script>
        const ctx = document.getElementById('trendChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: ['1月前','2月前','3月前','4月前','5月前','6月前','7月前','8月前','9月前','10月前','11月前','現在'],
                datasets: [
                    {{ label: 'BTC', data: {json_btc}, borderColor: '#f59e0b', tension: 0.4, fill: false }},
                    {{ label: '台股', data: {json_tw}, borderColor: '#00e5ff', tension: 0.4, fill: false }},
                    {{ label: '美股', data: {json_us}, borderColor: '#4CAF50', tension: 0.4, fill: false }},
                    {{ label: '黃金', data: {json_gold}, borderColor: '#fbbf24', tension: 0.4, fill: false }},
                    {{ label: '白銀', data: {json_silver}, borderColor: '#cbd5e1', tension: 0.4, borderDash: [5,5], fill: false }}
                ]
            }},
            options: {{ maintainAspectRatio: false, plugins: {{ legend: {{ labels: {{ color: '#94a3b8' }} }} }}, scales: {{ y: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}, x: {{ ticks: {{ color: '#64748b' }}, grid: {{ display: false }} }} }} }}
        }});
    </script>
</body>
</html>
"""
        with open("index.html", "w", encoding="utf-8") as f: f.write(html_content)
        log("✅ 網頁更新完成！請開啟 index.html 查看。")
    except Exception as e: log(f"❌ HTML 錯誤: {e}")

if __name__ == "__main__":
    market_data = get_market_data()
    video_info = get_youtube_video()
    ai_data = get_ai_analysis(video_info[1], video_info[2])
    save_html(market_data, ai_data, video_info)
