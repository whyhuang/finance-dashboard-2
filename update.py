import datetime

def get_data():
    # 這裡紀錄今日最新正確數據
    now = datetime.datetime.now()
    # 調整時區為台北時間 (UTC+8)
    tw_time = now + datetime.timedelta(hours=8)
    return {
        "update_date": tw_time.strftime("%Y-%m-%d"),
        "taiex": "28,556",
        "tsmc": "1,510",
        "gold": "4,525", # 修正為你指定的最新金價歷史高點
        "usdtwd": "31.595"
    }

def generate_html(data):
    # 這就是 Jason TV v5.2 的完整旗艦版 HTML 模板
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV | 專業財經監控終端</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@500;700&family=Noto+Sans+TC:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #05070a; --card: #11151c; --accent: #00e5ff; --up: #ff4d4d; --down: #00ff88; --text: #e2e8f0; --border: #232a35; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Noto Sans TC', sans-serif; background: var(--bg); color: var(--text); overflow-x: hidden; }}
        header {{ position: fixed; top: 0; width: 100%; height: 60px; background: rgba(17, 21, 28, 0.98); backdrop-filter: blur(15px); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 20px; z-index: 1000; }}
        .logo {{ font-size: 24px; font-weight: 900; color: var(--accent); letter-spacing: 2px; text-shadow: 0 0 10px rgba(0, 229, 255, 0.5); }}
        .market-status {{ font-family: 'JetBrains Mono'; font-size: 11px; color: var(--down); }}
        .container {{ max-width: 1200px; margin: 80px auto 40px; padding: 0 20px; }}
        .hero-summary {{ background: linear-gradient(145deg, #161b25, #0b0e14); border: 1px solid var(--accent); border-radius: 16px; padding: 25px; margin-bottom: 30px; box-shadow: 0 0 20px rgba(0, 229, 255, 0.1); }}
        .summary-item {{ margin-bottom: 12px; font-size: 15px; line-height: 1.6; padding-left: 20px; position: relative; color: #cbd5e1; }}
        .summary-item::before {{ content: '▶'; position: absolute; left: 0; color: var(--accent); font-size: 12px; top: 3px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
        .card-main {{ font-family: 'JetBrains Mono'; font-size: 26px; font-weight: 700; display: flex; align-items: baseline; gap: 8px; }}
        .chart-panel {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 25px; min-height: 380px; position: relative; }}
        @media (max-width: 600px) {{ .logo {{ font-size: 20px; }} .container {{ margin-top: 75px; }} .card-main {{ font-size: 22px; }} }}
    </style>
</head>
<body>
    <header>
        <div class="logo">JASON TV</div>
        <div class="market-status">● AUTO LIVE | {data['update_date']}</div>
    </header>
    <div class="container">
        <div class="hero-summary">
            <h2 style="color:var(--accent); margin-bottom:15px;">📺 錢線百分百・自動化摘要</h2>
            <div class="summary-item"><b>外資休假，內資當道：</b> 台股攻克歷史高點，OTC 指數領先過高。</div>
            <div class="summary-item"><b>金價創歷史奇蹟：</b> 成功突破 <b>${data['gold']}</b> 大關，反映避險瘋狂。</div>
        </div>
        <div class="grid">
            <div class="card"><div style="color:#94a3b8; font-size:12px;">加權指數</div><div class="card-main" style="color:var(--up);">{data['taiex']} ▲</div></div>
            <div class="card"><div style="color:#94a3b8; font-size:12px;">台積電 (2330)</div><div class="card-main" style="color:var(--up);">{data['tsmc']} ▲</div></div>
            <div class="card"><div style="color:#94a3b8; font-size:12px;">黃金價格 (GOLD)</div><div class="card-main" style="color:#fbbf24;">${data['gold']}</div></div>
            <div class="card"><div style="color:#94a3b8; font-size:12px;">美元/台幣</div><div class="card-main" style="color:white;">{data['usdtwd']}</div></div>
        </div>
        <div class="chart-panel">
            <canvas id="mainChart"></canvas>
        </div>
    </div>
    <script>
        const ctx = document.getElementById('mainChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: ['Q1', 'Q2', 'Q3', 'Q4'],
                datasets: [{{ label: '台股 (%)', data: [10, 25, 40, 65.8], borderColor: '#00e5ff', tension: 0.4 }}]
            }},
            options: {{ responsive: true, maintainAspectRatio: false }}
        }});
    </script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

if __name__ == "__main__":
    data = get_data()
    generate_html(data)
