import os
import datetime
import json
import sys

# === 系統配置 ===
print("=== 啟動 Jason TV v9.1 (Debug Fix) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UCq0y2w004V8666"

# 備用數據 (確保網頁永遠有東西看)
BACKUP_DATA = {
    "summary": ["系統連線中，顯示備用數據", "請檢查 GitHub Actions Log", "V9.1 介面測試正常", "等待下一次自動更新"],
    "stocks": [{"code": "2330", "name": "台積電", "reason": "系統預設值"}],
    "market": {
        "tsmc": "1,510", "taiex": "28,556", "gold": "$4,525", 
        "usdtwd": "31.595", "jpytwd": "0.2150", "btc": "$98,450"
    },
    "video": {"title": "錢線百分百 (備用)", "desc": "系統維護中。"}
}

def get_market_data():
    """抓取 Yahoo Finance"""
    print("Step 1: 連線 Yahoo Finance...")
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
        
        # 格式化
        return {
            "tsmc": f"{vals['tsmc']:.0f}" if vals['tsmc'] > 0 else BACKUP_DATA['market']['tsmc'],
            "taiex": f"{vals['taiex']:,.0f}" if vals['taiex'] > 0 else BACKUP_DATA['market']['taiex'],
            "gold": f"${vals['gold']:,.0f}" if vals['gold'] > 0 else BACKUP_DATA['market']['gold'],
            "usdtwd": f"{vals['usdtwd']:.3f}" if vals['usdtwd'] > 0 else BACKUP_DATA['market']['usdtwd'],
            "jpytwd": f"{vals['jpytwd']:.4f}" if vals['jpytwd'] > 0 else BACKUP_DATA['market']['jpytwd'],
            "btc": f"${vals['btc']:,.0f}" if vals['btc'] > 0 else BACKUP_DATA['market']['btc']
        }
    except Exception as e:
        print(f"❌ Yahoo 失敗: {e}")
        return BACKUP_DATA['market']

def get_video_data():
    """抓取 YouTube"""
    print("Step 2: 連線 YouTube...")
    try:
        import requests
        if not YT_KEY: return BACKUP_DATA['video']
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={CHANNEL_ID}&order=date&type=video&maxResults=1&key={YT_KEY}&q=錢線百分百"
        res = requests.get(url)
        data = res.json()
        if 'items' in data and len(data['items']) > 0:
            item = data['items'][0]['snippet']
            return {"title": item['title'], "desc": item['description']}
    except Exception as e:
        print(f"❌ YouTube 失敗: {e}")
    return BACKUP_DATA['video']

def get_ai_analysis(video):
    """抓取 Gemini"""
    print("Step 3: 呼叫 Gemini AI...")
    try:
        import requests
        if not GEMINI_KEY: return {"summary": BACKUP_DATA['summary'], "stocks": BACKUP_DATA['stocks']}
        prompt = f"請閱讀影片：{video['title']} \n內容：{video['desc']} \n回傳純 JSON (無Markdown)：{{'summary': ['4個重點'], 'stocks': [{{'code':'代號','name':'股名','reason':'原因'}}]}}"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        text = res.json()['candidates'][0]['content']['parts'][0]['text']
        clean_json = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        print(f"❌ AI 失敗: {e}")
        return {"summary": BACKUP_DATA['summary'], "stocks": BACKUP_DATA['stocks']}

def save_html(ai_data, video, market):
    """生成 HTML (統一函數名稱)"""
    print("Step 4: 正在寫入 index.html ...")
    try:
        update_time = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
        
        s_html = "".join([f'<div style="margin-bottom:10px; position:relative; padding-left:20px; line-height:1.6; color:#cbd5e1;"><span style="position:absolute; left:0; color:#00e5ff;">▶</span>{s}</div>' for s in ai_data.get('summary', [])])
        t_html = "".join([f"<tr><td style='font-weight:bold; color:#00e5ff;'>{s.get('code','')}</td><td>{s.get('name','')}</td><td style='color:#ff4d4d;'>▲</td><td style='color:#94a3b8; font-size:13px;'>{s.get('reason','')}</td></tr>" for s in ai_data.get('stocks', [])])

        html = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV v9.1 | Real-Time Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --accent: #00e5ff; --card: #11151c; --border: #232a35; --up: #ff4d4d; --down: #00ff88; --text: #e2e8f0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding-bottom: 50px; }}
        header {{ position: fixed; top: 0; width: 100%; height: 60px; background: rgba(17,21,28,0.95); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 1000; }}
        .logo {{ font-size: 22px; font-weight: 900; color: var(--accent); letter-spacing: 2px; text-shadow: 0 0 10px rgba(0,229,255,0.5); }}
        .container {{ max-width: 1200px; margin: 80px auto; padding: 0 20px; }}
        .hero {{ background: linear-gradient(145deg, #161b25, #0b0e14); border: 1px solid var(--accent); border-radius: 16px; padding: 25px; margin-bottom: 30px; box-shadow: 0 0 30px rgba(0,229,255,0.05); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: 0.3s; }}
        .card:hover {{ border-color: var(--accent); transform: translateY(-3px); }}
        .card-val {{ font-family: 'JetBrains Mono'; font-size: 26px; font-weight: 700; color: var(--text); margin-top: 8px; }}
        .card-label {{ font-size: 12px; color: #94a3b8; }}
        .panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 25px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ text-align: left; color: #64748b; font-size: 12px; border-bottom: 1px solid var(--border); padding: 10px; }}
        td {{ padding: 15px 10px; border-bottom: 1px solid rgba(255,255,255,0.05); font-size: 14px; }}
    </style>
</head>
<body>
    <header><div class="logo">JASON TV</div><div style="color:#00ff88; font-size:11px;">● LIVE | {update_time}</div></header>
    <div class="container">
        <div class="hero">
            <h2 style="color:var(--accent); margin-bottom:20px; font-size:18px; font-weight:bold;">📺 AI 戰情摘要 (來源：{video['title']})</h2>
            <div>{s_html}</div>
        </div>
        <div class="grid">
            <div class="card"><div class="card-label">加權指數 TAIEX</div><div class="card-val" style="color:var(--up)">{market['taiex']} ▲</div></div>
            <div class="card"><div class="card-label">台積電 TSMC</div><div class="card-val" style="color:var(--up)">{market['tsmc']} ▲</div></div>
            <div class="card"><div class="card-label">黃金價格 GOLD</div><div class="card-val" style
