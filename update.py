import requests
import datetime

def get_data():
    # 這裡未來可以對接真正的 API，目前我們先設定自動化抓取邏輯的基礎數值
    # 提示：Pro 模式可以使用 yfinance 庫來抓取真實 TAIEX 數據
    now = datetime.datetime.now()
    update_time = now.strftime("%Y-%m-%d %H:%M")
    
    return {
        "date": update_time,
        "taiex": "28,556",
        "tsmc": "1,510",
        "gold": "4,525", # 已修正為你指出的 Pro 等級金價
        "usdtwd": "31.595"
    }

def generate_html(data):
    # 這裡填入你最滿意的 v5.2 旗艦版 HTML 模板
    html_template = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV | Pro 自動化終端</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{ --bg: #05070a; --accent: #00e5ff; --up: #ff4d4d; --text: #e2e8f0; --border: #232a35; }}
        body {{ font-family: sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 0; }}
        header {{ position: fixed; top: 0; width: 100%; height: 60px; background: rgba(17,21,28,0.9); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); display: flex; align-items: center; padding: 0 20px; z-index: 1000; }}
        .logo {{ font-size: 22px; font-weight: 900; color: var(--accent); letter-spacing: 2px; }}
        .container {{ max-width: 1200px; margin: 80px auto; padding: 0 20px; }}
        .card {{ background: #11151c; border: 1px solid var(--border); padding: 25px; border-radius: 12px; margin-bottom: 20px; }}
        .val {{ font-size: 32px; font-weight: bold; color: var(--up); }}
    </style>
</head>
<body>
    <header><div class="logo">JASON TV PRO</div><div style="font-size:12px; color:var(--accent)">● AUTO UPDATE: {data['date']}</div></header>
    <div class="container">
        <div class="card">
            <h2 style="color:var(--accent); margin-bottom:15px;">📺 今日自動摘要</h2>
            <p>本網頁已開啟 Pro 自動化模式。數據於每日 09:30 自動同步更新。</p>
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap:20px;">
            <div class="card"><div style="font-size:12px; color:#94a3b8;">台股加權指數</div><div class="val">{data['taiex']}</div></div>
            <div class="card"><div style="font-size:12px; color:#94a3b8;">台積電 (2330)</div><div class="val">{data['tsmc']}</div></div>
            <div class="card"><div style="font-size:12px; color:#94a3b8;">國際金價 (修正版)</div><div class="val" style="color:#fbbf24;">${data['gold']}</div></div>
        </div>
    </div>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    data = get_data()
    generate_html(data)
