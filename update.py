import os
import datetime
import json
import sys
import re
import math

# === 系統配置 ===
print("=== 啟動 Jason TV v11.4 (YouTube Integration) ===")
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
        if vals['gold'] < 2000: vals['gold'] = 2650.0 
        if vals['btc'] < 50000: vals['btc'] = 95000.0

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

def get_youtube_video():
    """取得錢線百分百最新影片"""
    log("Step 2: 連線 YouTube API...")
    try:
        import requests
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'channelId': CHANNEL_ID,
            'maxResults': 1,
            'order': 'date',
            'type': 'video',
            'key': YT_KEY
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            log(f"❌ YouTube API 錯誤: {response.status_code}")
            return None, "無法連線 YouTube", "", ""
        
        data = response.json()
        
        if 'items' not in data or len(data['items']) == 0:
            log("⚠️ 找不到影片")
            return None, "暫無最新影片", "", ""
        
        video = data['items'][0]
        video_id = video['id']['videoId']
        snippet = video['snippet']
        title = snippet.get('title', '無標題')
        description = snippet.get('description', '')
        thumbnail = snippet.get('thumbnails', {}).get('medium', {}).get('url', '')
        
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        log(f"✅ 找到影片: {title[:50]}...")
        log(f"   影片連結: {video_url}")
        
        return video_url, title, description, thumbnail
        
    except Exception as e:
        log(f"❌ YouTube 錯誤: {e}")
        import traceback
        log(traceback.format_exc())
        return None, "YouTube 連線失敗", str(e), ""

def get_ai_analysis(video_title, video_desc):
    """使用 Gemini AI 分析影片內容"""
    log("Step 3: 連線 Gemini AI...")
    
    # 如果影片資訊無效，返回預設值
    if not video_title or video_title in ["暫無最新影片", "YouTube 連線失敗", "無法連線 YouTube"]:
        log("⚠️ 無有效影片資訊，跳過 AI 分析")
        return {
            "summary": ["等待最新影片更新", "系統將自動抓取錢線百分百最新內容"],
            "stocks": []
        }
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        
        # 列出可用模型
        log("ℹ️ 正在檢測可用模型...")
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    model_name = m.name.replace('models/', '')
                    available_models.append(model_name)
        except Exception as e:
            log(f"⚠️ 無法列出模型: {e}")
        
        # 選擇模型
        priority = ['gemini-2.0-flash-exp', 'gemini-2.0-flash', 'gemini-exp-1206', 'gemini-1.5-pro', 'gemini-pro']
        target_model = None
        for model in priority:
            if model in available_models:
                target_model = model
                break
        
        if not target_model and available_models:
            target_model = available_models[0]
        
        if not target_model:
            log("❌ 找不到可用的 Gemini 模型")
            return {"summary": ["AI 分析暫時無法使用"], "stocks": []}
        
        log(f"✅ 使用模型: {target_model}")
        model = genai.GenerativeModel(target_model)
        
        # 建立提示詞
        prompt = f"""你是一位專業的台股分析師。請分析以下「錢線百分百」YouTube 影片內容，並以 JSON 格式回傳：

影片標題：{video_title}
影片描述：{video_desc[:500]}

請提供：
1. 3-5 個重點摘要（每個 15-30 字）
2. 影片中提到的 2-3 檔重點股票（包含股票代號、名稱、提到的原因）

回傳格式（純 JSON，不要任何其他文字）：
{{
  "summary": [
    "重點1：市場趨勢分析",
    "重點2：產業動態觀察",
    "重點3：投資建議重點"
  ],
  "stocks": [
    {{"code": "2330", "name": "台積電", "reason": "AI 晶片需求強勁"}},
    {{"code": "2454", "name": "聯發科", "reason": "手機晶片市佔提升"}}
  ]
}}

注意：
- summary 要簡潔有力，聚焦在投資重點
- stocks 只列出影片明確提到的股票
- 如果沒提到具體股票，stocks 可以是空陣列
- 回傳純 JSON，不要 markdown 格式"""

        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # 清理 Markdown
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # 提取 JSON
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
            
            # 驗證數據格式
            if 'summary' not in result:
                result['summary'] = ["AI 分析完成，請查看影片詳情"]
            if 'stocks' not in result:
                result['stocks'] = []
            
            log(f"✅ AI 分析完成: {len(result.get('summary', []))} 個重點, {len(result.get('stocks', []))} 檔股票")
            return result
        
        log("⚠️ 無法解析 AI 回應")
        return {"summary": ["AI 分析完成，請查看影片"], "stocks": []}
        
    except Exception as e:
        log(f"❌ AI 失敗: {e}")
        import traceback
        log(traceback.format_exc())
        return {
            "summary": ["AI 分析暫時無法使用", "請直接觀看影片"],
            "stocks": []
        }

def save_html(market, ai, video_info, version="v11.4"):
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
        
        # 解包影片資訊
        video_url, video_title, video_desc, video_thumbnail = video_info
        
        # 生成影片區塊
        if video_url:
            video_html = f"""
    <div class="video-section">
        <h2>📺 錢線百分百 - 最新影片</h2>
        <div class="video-card">
            <a href="{video_url}" target="_blank" class="video-link">
                <div class="video-thumbnail" style="background-image: url('{video_thumbnail}');"></div>
                <div class="video-info">
                    <h3>{video_title}</h3>
                    <p>點擊觀看完整影片 →</p>
                </div>
            </a>
        </div>
    </div>"""
        else:
            video_html = """
    <div class="video-section">
        <h2>📺 錢線百分百 - 最新影片</h2>
        <div class="video-card" style="text-align: center; padding: 40px;">
            <p style="color: #888;">正在載入最新影片...</p>
        </div>
    </div>"""
        
        # 生成股票推薦表格
        stocks = ai.get('stocks', [])
        if stocks:
            stocks_html = ""
            for stock in stocks[:5]:
                stocks_html += f"""
        <tr>
            <td style="color: #00d4ff; font-weight: bold;">{stock.get('code', 'N/A')}</td>
            <td>{stock.get('name', 'N/A')}</td>
            <td style="color: #ff4444;">▲</td>
            <td style="font-size: 13px; color: #ccc;">{stock.get('reason', '權值股')}</td>
        </tr>"""
        else:
            stocks_html = """
        <tr>
            <td colspan="4" style="text-align: center; color: #888; padding: 20px;">
                本期影片未提及具體個股建議
            </td>
        </tr>"""
        
        # 生成 AI 摘要
        summary_html = ""
        for i, item in enumerate(ai.get('summary', ['載入中...'])[:6], 1):
            summary_html += f'<li><strong>重點 {i}：</strong>{item}</li>'
        
        html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jason TV {version} | Live</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', 'Microsoft JhengHei', Arial, sans-serif; 
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: #fff; 
            padding: 20px;
            min-height: 100vh;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 25px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }}
        .header h1 {{
            font-size: 42px;
            background: linear-gradient(45deg, #00d4ff, #7b2ff7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
            font-weight: 800;
        }}
        .version {{
            display: inline-block;
            background: linear-gradient(45deg, #ff4444, #ff8844);
            padding: 6px 18px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: bold;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.8; transform: scale(1.05); }}
        }}
        .update-time {{ color: #888; font-size: 14px; margin-top: 12px; }}
        
        .market-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 18px;
            margin-bottom: 30px;
        }}
        .market-card {{
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
            padding: 22px;
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s ease;
        }}
        .market-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,212,255,0.3);
            border-color: rgba(0,212,255,0.5);
        }}
        .market-label {{ color: #888; font-size: 13px; margin-bottom: 10px; font-weight: 500; }}
        .market-value {{ 
            font-size: 30px; 
            font-weight: 800;
            background: linear-gradient(45deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .chart-container {{
            background: rgba(255,255,255,0.05);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .video-section {{
            background: linear-gradient(135deg, rgba(255,68,68,0.15) 0%, rgba(255,136,68,0.15) 100%);
            padding: 30px;
            border-radius: 15px;
            border: 1px solid rgba(255,68,68,0.3);
            margin-bottom: 25px;
        }}
        .video-section h2 {{
            color: #ff6b6b;
            margin-bottom: 20px;
            font-size: 24px;
        }}
        .video-card {{
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            overflow: hidden;
            transition: transform 0.3s;
        }}
        .video-card:hover {{ transform: scale(1.02); }}
        .video-link {{
            display: flex;
            text-decoration: none;
            color: inherit;
            gap: 20px;
            align-items: center;
        }}
        .video-thumbnail {{
            width: 280px;
            height: 157px;
            background-size: cover;
            background-position: center;
            flex-shrink: 0;
        }}
        .video-info {{
            padding: 20px;
            flex: 1;
        }}
        .video-info h3 {{
            color: #fff;
            margin-bottom: 10px;
            font-size: 18px;
            line-height: 1.4;
        }}
        .video-info p {{
            color: #00d4ff;
            font-size: 14px;
        }}
        
        .ai-section {{
            background: linear-gradient(135deg, rgba(123,47,247,0.2) 0%, rgba(0,212,255,0.2) 100%);
            padding: 30px;
            border-radius: 15px;
            border: 1px solid rgba(123,47,247,0.3);
            margin-bottom: 25px;
        }}
        .ai-section h2 {{
            color: #00d4ff;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 24px;
        }}
        .ai-section ul {{ 
            list-style: none; 
            padding-left: 0;
        }}
        .ai-section li {{
            margin-bottom: 12px;
            line-height: 1.7;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            border-left: 3px solid #00d4ff;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 14px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{
            background: rgba(0,212,255,0.2);
            color: #00d4ff;
            font-weight: 600;
        }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        
        .debug-section {{
            background: rgba(40,40,40,0.5);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-top: 25px;
            font-size: 11px;
            font-family: 'Courier New', monospace;
        }}
        .debug-section h3 {{
            color: #888;
            margin-bottom: 12px;
            font-size: 14px;
        }}
        .debug-section pre {{
            color: #aaa;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        @media (max-width: 768px) {{
            .video-link {{ flex-direction: column; }}
            .video-thumbnail {{ width: 100%; height: 200px; }}
            .market-grid {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 JASON TV</h1>
        <span class="version">{version} | Live</span>
        <div class="update-time">最後更新: {now} (UTC+8)</div>
    </div>
    
    <div class="market-grid">
        <div class="market-card">
            <div class="market-label">📊 台積電 (2330.TW)</div>
            <div class="market-value">{market.get('tsmc', 'N/A')}</div>
        </div>
        <div class="market-card">
            <div class="market-label">📈 台股指數 (TAIEX)</div>
            <div class="market-value">{market.get('taiex', 'N/A')}</div>
        </div>
        <div class="market-card">
            <div class="market-label">🏆 黃金 (USD/oz)</div>
            <div class="market-value">{market.get('gold', 'N/A')}</div>
        </div>
        <div class="market-card">
            <div class="market-label">₿ 比特幣 (USD)</div>
            <div class="market-value">{market.get('btc', 'N/A')}</div>
        </div>
        <div class="market-card">
            <div class="market-label">💵 USD/TWD</div>
            <div class="market-value">{market.get('usdtwd', 'N/A')}</div>
        </div>
        <div class="market-card">
            <div class="market-label">💎 以太坊 (USD)</div>
            <div class="market-value">{market.get('eth', 'N/A')}</div>
        </div>
    </div>
    
    <div class="chart-container">
        <canvas id="trendChart"></canvas>
    </div>
    
    {video_html}
    
    <div class="ai-section">
        <h2>🔥 錢線熱門追蹤 (AI 自動選股)</h2>
        <table>
            <thead>
                <tr>
                    <th>代號</th>
                    <th>名稱</th>
                    <th>訊號</th>
                    <th>關鍵理由</th>
                </tr>
            </thead>
            <tbody>
                {stocks_html}
            </tbody>
        </table>
    </div>
    
    <div class="ai-section">
        <h2>💡 AI 影片摘要</h2>
        <ul>
            {summary_html}
        </ul>
    </div>
    
    <div class="debug-section">
        <h3>🔧 系統診斷日誌</h3>
        <pre>{''.join([log + '
' for log in DEBUG_LOGS])}</pre>
    </div>
    
    <script>
        const ctx = document.getElementById('trendChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: ['1月前', '2月前', '3月前', '4月前', '5月前', '6月前', '7月前', '8月前', '9月前', '10月前', '11月前', '12月前'],
                datasets: [
                    {{
                        label: '🏆 黃金',
                        data: {json_gold},
                        borderColor: '#FFD700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }},
                    {{
                        label: '⚪ 白銀',
                        data: {json_silver},
                        borderColor: '#C0C0C0',
                        backgroundColor: 'rgba(192, 192, 192, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }},
                    {{
                        label: '🇺🇸 美股',
                        data: {json_us},
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }},
                    {{
                        label: '🇹🇼 台股',
                        data: {json_tw},
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        pointRadius: 3,
                        pointHoverRadius: 5
                    }},
                    {{
                        label: '₿ 比特幣',
                        data: {json_btc},
                        borderColor: '#FF9800',
                        backgroundColor: 'rgba(255, 152, 0, 0.1)',
                        tension: 0.4,
                        borderWidth: 3,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{ 
                        labels: {{ 
                            color: '#fff', 
                            font: {{ size: 14, weight: '500' }},
                            padding: 15
                        }},
                        position: 'top'
                    }},
                    title: {{ 
                        display: true, 
                        text: '近一年漲跌趨勢 (%)', 
                        color: '#00d4ff',
                        font: {{ size: 20, weight: 'bold' }},
                        padding: 20
                    }}
                }},
                scales: {{
                    y: {{ 
                        ticks: {{ color: '#888', font: {{ size: 12 }} }},
                        grid: {{ color: 'rgba(255,255,255,0.1)' }}
                    }},
                    x: {{ 
                        ticks: {{ color: '#888', font: {{ size: 12 }} }},
                        grid: {{ color: 'rgba(255,255,255,0.1)' }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        
        output_path = 'index.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            log(f"✅ HTML 已寫入 {output_path} ({file_size:,} bytes)")
        else:
            log(f"❌ 警告: {output_path} 未成功建立")
        
    except Exception as e:
        log(f"❌ 存檔失敗: {e}")
        import traceback
        log(traceback.format_exc())

if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("🚀 Jason TV 啟動中...")
        print("="*60 + "\n")
        
        # 執行流程
        market_data = get_market_data()
        video_info
