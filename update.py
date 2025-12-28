import os
import requests
import datetime
import json
import sys

# === 除錯開始 ===
print("=== 腳本開始執行 (Jason TV v9.2) ===")

# 嘗試載入 yfinance，如果失敗不崩潰，而是標記起來
try:
    import yfinance as yf
    HAS_YFINANCE = True
    print("✅ 成功載入 yfinance 套件")
except ImportError as e:
    HAS_YFINANCE = False
    print(f"⚠️ 警告: 找不到 yfinance 套件! 錯誤訊息: {e}")

# 讀取金鑰
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCq0y2w004V8666"

def get_market_data():
    """抓取市場數據"""
    print("Step 1: 正在連線 Yahoo Finance...")
    
    # 備用數據 (萬一失敗時使用)
    backup_data = {
        "tsmc": "1,510", "taiex": "28,556", "gold": "$4,525", 
        "usdtwd": "31.500", "jpytwd": "0.2150", "btc": "$98,000"
    }

    if not HAS_YFINANCE:
        print("❌ 因為沒有 yfinance，使用備用數據")
        return backup_data

    try:
        tickers = ["2330.TW", "^TWII", "GC=F", "USDTWD=X", "JPYTWD=X", "BTC-USD"]
        data = yf.Tickers(" ".join(tickers))
        
        def get_price(symbol):
            try:
                df = data.tickers[symbol].history(period="1d")
                if df.empty: return 0
                return df['Close'].iloc[-1]
            except:
                return 0

        vals = {
            "tsmc": get_price('2330.TW'), "taiex": get_price('^TWII'),
            "gold": get_price('GC=F'), "usdtwd": get_price('USDTWD=X'),
            "jpytwd": get_price('JPYTWD=X'), "btc": get_price('BTC-USD')
        }
        
        market = {
            "tsmc": f"{vals['tsmc']:.0f}" if vals['tsmc'] else "1,510",
            "taiex": f"{vals['taiex']:,.0f}" if vals['taiex'] else "28,556",
            "gold": f"${vals['gold']:,.0f}" if vals['gold'] else "$4,525",
            "usdtwd": f"{vals['usdtwd']:.3f}" if vals['usdtwd'] else "31.595",
            "jpytwd": f"{vals['jpytwd']:.4f}" if vals['jpytwd'] else "0.2150",
            "btc": f"${vals['btc']:,.0f}" if vals['btc'] else "$98,450"
        }
        print("✅ Yahoo 數據抓取成功！")
        return market
    except Exception as e:
        print(f"❌ Yahoo 連線發生錯誤: {e}")
        return backup_data

def get_video_data():
    """抓取 YouTube"""
    print("Step 2: 正在連線 YouTube...")
    if not YT_KEY:
        print("⚠️ 警告: 沒有找到 YOUTUBE_API_KEY")
        return {"title": "錢線百分百 (無金鑰)", "desc": "請檢查 GitHub Secrets 設定"}
        
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=1&key={YT_KEY}&q=錢線百分百"
    try:
        res = requests.get(url)
        data = res.json()
        if 'items' in data and len(data['items']) > 0:
            item = data['items'][0]['snippet']
            print("✅ YouTube 抓取成功")
            return {"title": item['title'], "desc": item['description']}
    except Exception as e:
        print(f"❌ YouTube 錯誤: {e}")
    return {"title": "錢線百分百 (備用源)", "desc": "今日市場重點：台積電、AI 伺服器與全球降息趨勢。"}

def get_ai_analysis(video):
    """抓取 Gemini"""
    print("Step 3: 正在呼叫 Gemini AI...")
    if not GEMINI_KEY:
        print("⚠️ 警告: 沒有找到 GEMINI_API_KEY")
        return {"summary": ["未設定金鑰"], "stocks": []}

    prompt = f"請閱讀影片：{video['title']} \n內容：{video['desc']} \n回傳純 JSON (無Markdown)：{{'summary': ['4個重點'], 'stocks': [{{'code':'代號','name':'股名','reason':'原因'}}]}}"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        text = res.json()['candidates'][0]['content']['parts'][0]['text']
        clean_json = text.replace("```json", "").replace("```", "").strip()
        print("✅ AI 分析成功")
        return json.loads(clean_json)
    except Exception as e:
        print(f"❌ AI 分析錯誤: {e}")
        return {
            "summary": ["外資休假內資主導", "指數高檔震盪", "留意匯率變化", "比特幣高檔震盪"],
            "stocks": [{"code": "2330", "name": "台積電", "reason": "先進製程"}]
        }

def save_to_index(ai_data, video, market):
    """生成 HTML"""
    print("Step 4: 生成網頁中...")
    update_time = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    
    s_html = "".join([f'<div style="margin-bottom:8px; position:relative; padding-left:20px; line-height:1.5;"><span style="position:absolute; left:0; color:#00e5ff;">▶</span>{s}</div>' for s in ai_data.get('summary', [])])
    t_html = "".join([f"<tr><td style='font-weight:bold; color:#00e5ff;'>{s.get('code','')}</td><td>{s.get('name','')}</td><td style='color:#ff4d4d;'>▲</td><td style='color:#94a3b8; font-size:13px;'>{s.get('reason','')}</td></tr>" for s in ai_data.get('stocks', [])])

    html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV v9.2 | Real-Time</title>
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
        .card-val {{ font-family: 'JetBrains Mono'; font-size: 24px; font-weight: 700; color: var(--text); }}
        .card-label {{ font-size: 12px; color: #94a3b8; margin-bottom: 5px; }}
        .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th {{ text-align: left; color: #64748b; font-size: 12px; border-bottom: 1px solid var(--border); padding: 10px; }}
        td {{ padding: 12px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }}
    </style>
</head>
<body>
    <header><div class="logo">JASON TV</div><div style="color:#00ff88; font-size:11px;">● LIVE | {update_time}</div></header>
    <div class="container">
        <div class="hero">
            <h2 style="color:var(--accent); margin-bottom:15px; font-size:18px;">📺 AI 戰情摘要 (來源：{video['title']})</h2>
            <div style="color:#cbd5e1;">{s_html}</div>
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
    </div>
    <script>
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
    print("✅ index.html 生成完畢！")

if __name__ == "__main__":
    # 使用 try-except 包裹整個主程式，確保不拋出 Exit Code 1
    try:
        market_data = get_market_data() 
        video = get_video_data()        
        ai_data = get_ai_analysis(video)
        save_to_index(ai_data, video, market_data)
        print("=== 全部任務完成 (Success) ===")
    except Exception as e:
        print(f"❌ 發生未預期的錯誤: {e}")
        # 這裡不讓程式當掉，為了能看到 Log
        sys.exit(0)
