#include <WiFi.h>
#include <WiFiMulti.h>      // 新增這行！
#include <PubSubClient.h>
#include "HX711.h"

// 宣告 WiFiMulti 物件
WiFiMulti wifiMulti;

// ================== 設定區，注意DEVICE ID要改 ==================
const char* DEVICE_ID = "LuLu01"; //<==這個一定要注意
const char* ssid = "OLULU router";
const char* password = "olulu1003";
const char* mqtt_server = "192.168.50.168";

//const int LOADCELL_DOUT_PIN = 15;
//const int LOADCELL_SCK_PIN = 2;

// MQTT Topic
String topic_status;
String topic_weight;
String topic_ip; // <== 發布IP用
const char* topic_trigger = "olulu/all/trigger";

// ================== 全域變數與 Task 控制 ==================
WiFiClient espClient;
PubSubClient client(espClient);

// 使用 TaskHandle 來控制核心 0 的任務
TaskHandle_t MeasureTaskHandle = NULL;

// 旗標 (Flag) 建議加上 volatile 確保跨核心讀取正確
volatile bool shouldMeasure = false; 
volatile float lastMeasuredWeight = 0.0;
volatile bool hasNewData = false;

// ================== 獨立量測任務 (與 loop 共同在 Core 1 輪替) ==================
void Task_Measure(void * pvParameters) {
  Serial.print("Measure Task running on core: ");
  Serial.println(xPortGetCoreID());

  for(;;) {
    // 檢查是否有量測指令
    if (shouldMeasure) {
      Serial.println("[Measure Task] Measuring...");
      long sum = 0;
      int validCount = 0;
      
      // 進行 10 次採樣 (這段會卡 500ms 以上)
      for(int i=0; i<10; i++) {
        long reading = Get_Weight(); 
        if (reading > -5000 && reading < 50000) { 
          sum += reading;
          validCount++;
        }
        vTaskDelay(50 / portTICK_PERIOD_MS); // 在 Task 裡建議使用 vTaskDelay，讓出 CPU 給系統
      }
      
      if (validCount > 0) {
        lastMeasuredWeight = sum / (float)validCount;
        hasNewData = true; // 標記已完成量測，交給核心 1 傳送
      }

      shouldMeasure = false; // 重置旗標
    }
    
    // 核心 0 沒事做時必須小睡一下，否則會觸發看門狗警告
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

// ================== 原有函式 ==================

void setup_wifi() {
  delay(10);
  Serial.println("\nScanning and Connecting to strongest WiFi...");

  // 把您所有的 SSID 和密碼都加進去 (可以加無限多個)
  wifiMulti.addAP("OLULU router", "olulu1003");       // 主 Router
  wifiMulti.addAP("OLULU router_EX", "olulu1003");   // 延伸器
  wifiMulti.addAP("OLULU router_2EX", "olulu1003");   // 延伸器
  // wifiMulti.addAP("OLULU_Floor3", "olulu1003");    // 未來如果有第三台也可以加

  // 讓 ESP32 自動掃描並連線到訊號最強的 AP
  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected!");
  Serial.print("Connected to SSID: ");
  Serial.println(WiFi.SSID()); // 印出它最後聰明地選了哪一個
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  if (strcmp(topic, topic_trigger) == 0) {
    if ((char)payload[0] == '1') {
      shouldMeasure = true; // 觸發核心 0 開始工作
      Serial.println("[Core 1] Trigger received!");
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(DEVICE_ID, topic_status.c_str(), 1, true, "offline")) {
      Serial.println("connected");
      client.publish(topic_status.c_str(), "online", true);
      // 發布自己目前的動態 IP
      String myIP = WiFi.localIP().toString();
      client.publish(topic_ip.c_str(), myIP.c_str()); // <== 發布IP字串
      client.subscribe(topic_trigger);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

// ================== Setup & Loop ==================

void setup() {
  Serial.begin(115200);

// 初始化硬體
  Init_Hx711(); 
  
  // 補回歸零動作
  Serial.println("Taring...");
  Get_Maopi(); 
  delay(1000);
  Get_Maopi();

  topic_status = String("device/") + DEVICE_ID + "/status";
  topic_weight = String("device/") + DEVICE_ID + "/weight";
  topic_ip = String("device/") + DEVICE_ID + "/ip"; // <== 本身IP

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

// *** 關鍵：建立雙核心任務 ***
  xTaskCreatePinnedToCore(
    Task_Measure,      /* 任務函式名稱 */
    "MeasureTask",     /* 任務名稱 (除錯用) */
    4096,              /* Stack 大小 (Byte) */
    NULL,              /* 傳入參數 */
    1,                 /* 優先級 */
    &MeasureTaskHandle, /* 任務句柄 */
    0                  // <== 放到核心 0
  );
}

void loop() {
  // 核心 1 (主核心) 專心處理網路連線
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // 檢查核心 0 是否有新產出的數據
  if (hasNewData) {
    String valStr = String(lastMeasuredWeight, 1);
    client.publish(topic_weight.c_str(), valStr.c_str());
    Serial.print("[Core 1] MQTT Published: ");
    Serial.println(valStr);
    
    hasNewData = false; // 處理完畢，重置旗標
  }
    
}
