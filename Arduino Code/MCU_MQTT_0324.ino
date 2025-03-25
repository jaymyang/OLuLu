#include "HX711.h"
//注意不同的板子要用不同的WiFi檔
#include <WiFi.h> //ESP32的WiFi程式庫
//#include <ESP8266WiFi.h> //ESP8266的WiFi程式庫
#include <PubSubClient.h> //MQTT程式庫
//路由器SSID與密碼
const char* ssid = "OLULU router";
const char* password = "olulu1003";
//注意IP
//const char* mqtt_server = "192.168.50.127"; // MQTT 伺服器 IP
const char* mqtt_server = "192.168.50.150"; // MQTT 伺服器 IP
const int mqtt_port = 1883; // MQTT 埠口

const char* mqtt_broadcast_sub = "olulu/command"; // 訂閱廣播主題(接收命令)
String sub_topic="command/LuLu01"; //command/ID;// // 宣告ID專屬 mqtt_topic_sub，使用 ID 建立訂閱主題字串
const char* mqtt_topic_pub = "olulu/response"; // 發布(回傳資料)

char python_order;      // 從 Python 收到的命令字元 (暫未使用)
String Weight = "A";    // 儲存重量資料的字串，"A"為資料表頭識別碼
String temp_Weight = "";// 暫存單次讀取的重量字串
//注意ID有沒有更正
String ID = "LuLu01";   //本機ID，注意各機器不能重複
int i;                  // 迴圈計數器
// 讀取重量檢查重量是否在合理範圍內
String Get_Weight_Safe() {
    int raw_weight = Get_Weight();                    // 呼叫 HX711 庫的 Get_Weight() 函式讀取重量
    Serial.print("Raw weight: ");
    Serial.println(raw_weight);
    if (raw_weight > 5000 || raw_weight < -1000) {
        Serial.println("Error: Invalid weight data!");
        return "-9999";  // 回傳錯誤碼
    }
    return String(raw_weight);    // 如重量合理，回傳重量字串
}

WiFiClient espClient;
PubSubClient client(espClient); //建立 PubSubClient 物件 client。

void setup() {
  Serial.begin(9600);// 初始化序列埠，用於除錯
  delay(10);
  Serial.println("Connecting to WiFi...");
  // 連接 WiFi 網路
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { // 等待 WiFi 連接成功
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");

  client.setServer(mqtt_server, mqtt_port);// MQTT 伺服器 IP & port
  client.setCallback(callback);             // 設定 MQTT 回呼函式，用於處理接收到的訊息
  //HX711
  Init_Hx711();// 初始化 HX711 感測器
  Get_Maopi();
  delay(3000);
  Get_Maopi();
  //MQTT
  connectMQTT(); //連接 MQTT 伺服器
}
//檢查 MQTT 連線並呼叫 client.loop()。
void loop() {
    static unsigned long lastMQTTCheck = 0;

    if (!client.connected() && millis() - lastMQTTCheck > 10000) { // 10 秒檢查一次
        lastMQTTCheck = millis();
        connectMQTT();
    }
    
    client.loop(); // 處理 MQTT 通訊
    static unsigned long lastPrintTime = 0;
    if (millis() - lastPrintTime >= 5000) { // 除錯用，每 5 秒確認一次 MQTT 狀態
    Serial.println("MQTT is running...");
    lastPrintTime = millis();
  }
}

//MQTT連線函式連接到 MQTT 伺服器並訂閱主題。
void connectMQTT() {
  while (!client.connected()) {                     // 如果未連接到 MQTT 伺服器
    Serial.print("Attempting MQTT connection...");
    if (client.connect(ID.c_str())) {
      Serial.println("connected");      
      // **確認訂閱成功**
      if (client.subscribe(mqtt_broadcast_sub)) {             // 訂閱廣播主題
        Serial.println("Subscribed to topic: " + String(mqtt_broadcast_sub));
      } else {
        Serial.println("Subscripting broadcast failed!");
      }  
      if (client.subscribe(sub_topic.c_str())) {            //訂閱本感測器專屬指令
        Serial.println("Subscribed to topic: " + sub_topic);
      } else {
        Serial.println("Subscription ID channel failed!");
      }
      client.publish(mqtt_topic_pub, "R,LuLu01");
      Serial.println("Sent: R,LuLu01");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);                // 延遲 5 秒後重試
    }
  }
}

//MQTT 回呼函式，當收到 MQTT 訊息時呼叫，處理命令。指令放在payload
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();

  if (strcmp(topic, sub_topic.c_str()) == 0) { // 比對ID專屬主題--如果接收到的主題是訂閱的主題
    if ((char)payload[0] == '1') {            // 命令是 '1'
      Weight.reserve(50);                     // 預先分配記憶體，避免記憶體碎片化
      Weight = "A";                           // 重置重量字串
      int err_count=0;                        // 重置錯誤計數器
      for (i = 1; i <= 10; i++) {             // 讀取 10 次重量
        temp_Weight = Get_Weight_Safe() ;
        if (temp_Weight=="-9999"){            // 如果讀取到錯誤碼，錯誤計數+1
          err_count++; 
        }
        else {
          Weight = Weight + "," + temp_Weight;// 將重量加入字串
        }
        delay(500);                           // 等 0.5 秒
      }
      if (err_count > 5){                     // 如果錯誤次數超過 5 次，重新開機
        Serial.println("Err_count>5. Reset Arduino");
        ESP.restart();
      }
      Weight = Weight + "," + ID;             // 將 ID 加入字串末尾，作為識別
      
      // 確保 Weight 內容正確
      Serial.print("Publishing MQTT Data: ");
      Serial.println(Weight);

      if (client.publish(mqtt_topic_pub, Weight.c_str())) { // 發布重量資料到 MQTT
        Serial.println("MQTT Publish Successful");
      } else {
        Serial.println("MQTT Publish Failed");
      }
    } 
  }
  else if (strcmp(topic, mqtt_broadcast_sub) == 0) {
    if ((char)payload[0] == '9') {                   // 如果接收到的命令是 '9'
      Weight = "R," + ID;                                   // 回傳字串，R為識別，加上ID
      if (client.publish(mqtt_topic_pub, Weight.c_str())) { // 發布 ID 到 MQTT
        Serial.println("MQTT Identity Publish Successful");
      } else {
        Serial.println("MQTT Identity Publish Failed");
      }
    } else {
      Serial.println("Invalid command received in broadcast");
    }
  }
}