import os
import json
import csv
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "bed_config.json")

# ================= 網頁前端 HTML + JavaScript (使用 Chart.js) =================
#為確保在內部網路能執行，需先建立static 資料夾，並從https://cdn.jsdelivr.net/npm/chart.js
#將該檔案（chart.js）存在static 資料夾中
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>OLuLu 遠端即時監控</title>
    <script src="/static/chart.js"></script>
    <style>
        body { font-family: 'Microsoft JhengHei UI', Arial, sans-serif; background-color: #F5F7FA; margin: 0; padding: 15px; }
        .container { max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h2 { color: #333; text-align: center; margin-top: 0; }
        select { width: 100%; padding: 12px; font-size: 18px; border-radius: 8px; border: 1px solid #ccc; margin-bottom: 20px; }
        .chart-container { position: relative; height: 40vh; width: 100%; }
        .status { text-align: center; color: #888; font-size: 14px; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🏥 OLuLu 即時重量監控</h2>
        
        <label for="bedSelect" style="font-weight: bold; color: #555;">請選擇床位：</label>
        <select id="bedSelect" onchange="updateChart()"></select>
        
        <div class="chart-container">
            <canvas id="weightChart"></canvas>
        </div>
        
        <div class="status" id="lastUpdated">載入中...</div>
    </div>

    <script>
        let chartInstance = null;
        let globalData = {};

        // 1. 向 Flask 伺服器獲取最新資料
        async function fetchData() {
            try {
                const response = await fetch('/api/data');
                globalData = await response.json();
                
                const select = document.getElementById('bedSelect');
                const currentSelection = select.value;
                
                // 更新下拉選單
                select.innerHTML = '<option value="">-- 請選擇病床 --</option>';
                for (const bedName in globalData) {
                    const option = document.createElement('option');
                    option.value = bedName;
                    option.textContent = `[${bedName}] 病歷號: ${globalData[bedName].patient_id}`;
                    select.appendChild(option);
                }
                
                // 保持原來的選擇，如果沒有則不選
                if (currentSelection && globalData[currentSelection]) {
                    select.value = currentSelection;
                }
                
                updateChart();
                document.getElementById('lastUpdated').textContent = `最後更新時間: ${new Date().toLocaleTimeString()}`;
            } catch (error) {
                document.getElementById('lastUpdated').textContent = '⚠️ 無法連線至伺服器';
            }
        }

        // 2. 繪製或更新圖表
        function updateChart() {
            const selectedBed = document.getElementById('bedSelect').value;
            const ctx = document.getElementById('weightChart').getContext('2d');
            
            if (!selectedBed || !globalData[selectedBed]) {
                if (chartInstance) chartInstance.destroy();
                return;
            }

            const bedData = globalData[selectedBed];
            
            if (chartInstance) chartInstance.destroy();
            
            chartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: bedData.times,
                    datasets: [{
                        label: '重量 (g/ml)',
                        data: bedData.weights,
                        borderColor: '#FF9F43',
                        backgroundColor: 'rgba(255, 159, 67, 0.2)',
                        borderWidth: 2,
                        pointRadius: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, suggestedMax: 500 }
                    },
                    animation: { duration: 0 } // 關閉動畫讓手機更省電
                }
            });
        }

        // 初次載入
        fetchData();
        // 每 60 秒自動背景刷新一次資料
        setInterval(fetchData, 60000);
    </script>
</body>
</html>
"""

# ================= 後端 API 邏輯 =================

@app.route('/')
def index():
    """首頁：直接回傳 HTML 字串"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    """API：讀取 json 與 csv，回傳給前端繪圖"""
    response_data = {}
    
    if not os.path.exists(CONFIG_FILE):
        return jsonify(response_data)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        for bed_name, info in config.items():
            pid = info.get("patient_id")
            if not pid: continue
            
            # 讀取對應的 CSV 歷史資料 (這裡設定只抓最後 60 筆，約 1 小時資料)
            csv_file = os.path.join(BASE_DIR, f"{pid}.csv")
            times, weights = [], []
            
            if os.path.exists(csv_file):
                try:
                    with open(csv_file, "r", encoding="utf-8") as cf:
                        # 讀取最後 60 筆有效資料
                        rows = [r for r in csv.reader(cf) if len(r) >= 2 and r[0].strip() != "Time"]
                        recent_rows = rows[-60:]
                        for row in recent_rows:
                            times.append(row[0][-5:]) # 只取 "HH:MM" 格式
                            weights.append(float(row[1]))
                except Exception:
                    pass
            
            response_data[bed_name] = {
                "patient_id": pid,
                "times": times,
                "weights": weights
            }
            
    except Exception as e:
        print(f"API 讀取錯誤: {e}")

    return jsonify(response_data)

if __name__ == '__main__':
    # host='0.0.0.0' 代表允許區域網路內的所有設備連線
    # port=5000 是預設的網頁連接埠
    print("🌐 OLuLu Web Server 已啟動！")
    print("📱 請在手機瀏覽器輸入: http://[您的伺服器IP]:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
