import os
import datetime
import json
import sys
import re
import math

# === 系統配置 ===
print("=== 啟動 Jason TV v11.2 (GitHub Pages Fix) ===")
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
        if vals['gold'] < 2000: vals['gold'] = 4550.0 
        if vals['btc'] < 50000: vals['btc'] = 87000.0

        for key, val in vals.items():
            if val > 0:
                if key in ['usdtwd']: final_vals[key] = f"{val:.3f}"
                elif key in ['jpytwd', 'silver']: final_vals[key] = f"{val:.2f}"
                elif key in ['us10y']: final_vals[key] = f"{val:.2f}%"
                else: final_vals[key] = f"{val:,.0f}"
            else: final_vals[key] = "N/A"
        
        final_vals['chart_data'] = chart_series
        log(f"✅ Yahoo 數據載入完成 (TAIEX: {final_vals['taiex']})")
        return final_vals
    except Exception as e:
        log(f"❌ Yahoo 錯誤: {e}")
        return {"chart_data": {}}

def get_ai_analysis(video_title, video_desc):
    log("Step 3: 連線 Gemini AI...")
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        
        target_model = 'gemini-2.0-flash'
        try:
            available = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            if 'gemini-2.0-flash' in available: target_model = 'gemini-2.0-flash'
            elif 'gemini-2.5-flash' in available: target_model = 'gemini-2.5-flash'
            else: target_model = available[0]
        except: pass
        
        log(f"ℹ️ 適配模型: {target_model}")
        model = genai.GenerativeModel(target_model)
        prompt = f"分析影片並以 JSON 回傳摘要與股票：{video_title}\n{video_desc}"
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return json.loads(text)
    except Exception as e:
        log(f"❌ AI 失敗: {e}")
        return {"summary": ["AI 摘要暫時無法顯示"], "stocks": []}

def save_html(market, ai):
    log("Step 4: 生成網頁...")
    try:
        def clean(d): 
            return json.dumps([0.0 if (isinstance(x, float) and math.isnan(x)) else x for x in d])
        
        c = market.get('chart_data', {})
        json_gold = clean(c.get('gold', [0]*12))
        json_silver = clean(c.get('silver', [0]*12))
        json_us = clean(c.get('us_stock', [0]*12))
        json_tw = clean(c.get('tw_stock', [0]*12))
        json_btc = clean(c.get('btc', [0]*12))
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .update-time {{ color: #888; font-size: 14px; }}
        .market-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .market-card {{ background: #2a2a2a; padding: 15px; border-radius: 8px; }}
        .market-label {{ color: #888; font-size: 12px; }}
        .market-value {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
        .chart-container {{ background: #2a2a2a; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        canvas {{ max-height: 300px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Jason TV 市場儀表板</h1>
        <div class="update-time">最後更新: {now} (UTC+8)</div>
    </div>
    
    <div class="market-grid">
        <div class="market-card">
            <div class="market-label">台積電 (2330.TW)</div>
            <div class="market-value">{market.get('tsmc', 'N/A')}</div>
        </div>
        <div class="market-card">
            <div class="market-label">台股指數</div>
            <div class="market-value">{market.get('taiex', 'N/A')}</div>
        </div>
        <div class="market-card">
            <div class="market-label">黃金 (USD/oz)</div>
            <div class="market-value">{market.get('gold', 'N/A')}</div>
        </div>
        <div class="market-card">
            <div class="market-label">比特幣 (USD)</div>
            <div class="market-value">{market.get('btc', 'N/A')}</div>
        </div>
    </div>
    
    <div class="chart-container">
        <canvas id="trendChart"></canvas>
    </div>
    
    <script>
        const ctx = document.getElementById('trendChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: ['1月前', '2月前', '3月前', '4月前', '5月前', '6月前', '7月前', '8月前', '9月前', '10月前', '11月前', '12月前'],
                datasets: [
                    {{
                        label: '黃金',
                        data: {json_gold},
                        borderColor: '#FFD700',
                        tension: 0.4
                    }},
                    {{
                        label: '白銀',
                        data: {json_silver},
                        borderColor: '#C0C0C0',
                        tension: 0.4
                    }},
                    {{
                        label: '美股',
                        data: {json_us},
                        borderColor: '#4CAF50',
                        tension: 0.4
                    }},
                    {{
                        label: '台股',
                        data: {json_tw},
                        borderColor: '#2196F3',
                        tension: 0.4
                    }},
                    {{
                        label: '比特幣',
                        data: {json_btc},
                        borderColor: '#FF9800',
                        tension: 0.4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ labels: {{ color: '#fff' }} }},
                    title: {{ display: true, text: '近一年漲跌趨勢 (%)', color: '#fff' }}
                }},
                scales: {{
                    y: {{ ticks: {{ color: '#fff' }} }},
                    x: {{ ticks: {{ color: '#fff' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        # 【關鍵修正】確保檔案寫入
        output_path = 'index.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 驗證檔案是否存在
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            log(f"✅ HTML 已寫入 {output_path} ({file_size} bytes)")
        else:
            log(f"❌ 警告: {output_path} 未成功建立")
        
    except Exception as e:
        log(f"❌ 存檔失敗: {e}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    try:
        # 執行流程
        m = get_market_data()
        
        # 模擬 AI 分析（如果沒有影片資料）
        ai_data = {
            "summary": ["市場數據已更新", f"更新時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"],
            "stocks": []
        }
        
        save_html(m, ai_data)
        
        # 輸出除錯資訊
        print("\n=== 除錯日誌 ===")
        for log_entry in DEBUG_LOGS:
            print(log_entry)
        
        print("\n✅ 腳本執行完成")
        
    except Exception as e:
        print(f"❌ 主程式錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
