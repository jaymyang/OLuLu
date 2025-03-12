#include "HX711.h"
//注意不同的板子要用不同的WiFi檔
#include <WiFi.h>
//#include <ESP8266WiFi.h>
#include <PubSubClient.h>

const char* ssid = "OLULU router";
const char* password = "olulu1003";
//注意IP
//const char* mqtt_server = "192.168.50.127"; // MQTT 伺服器 IP
const char* mqtt_server = "192.168.50.150"; // MQTT 伺服器 IP
const int mqtt_port = 1883; // MQTT 埠口
const char* mqtt_topic_sub = "olulu/command"; // 訂閱主題
const char* mqtt_topic_pub = "olulu/response"; // 發布主題

char python_order;
String Weight = "A";
String temp_Weight = "";
//注意ID有沒有更正
String ID = "LuLu01"; 
int i;
String Get_Weight_Safe() {
    int raw_weight = Get_Weight();
    if (raw_weight > 5000 || raw_weight < -1000) {
        Serial.println("Error: Invalid weight data!");
        return "ERR";  // 回傳錯誤碼，Python 端可以忽略這筆資料
    }
    return String(raw_weight);
}

WiFiClient espClient;
PubSubClient client(espClient); //建立 PubSubClient 物件 client。

void setup() {
  Serial.begin(9600);
  delay(10);
  Serial.println("Connecting to WiFi...");

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("WiFi connected");

  client.setServer(mqtt_server, mqtt_port);// MQTT 伺服器 IP & port
  client.setCallback(callback);
  //HX711
  Init_Hx711();
  Get_Maopi();
  delay(3000);
  Get_Maopi();
  //MQTT
  connectMQTT(); //去進行連線
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
    if (millis() - lastPrintTime >= 3000) { // 除錯用，每 3 秒確認一次 MQTT 狀態
    Serial.println("MQTT is running...");
    lastPrintTime = millis();
  }
}

//MQTT連線函式連接到 MQTT 伺服器並訂閱主題。
void connectMQTT() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect(ID.c_str())) {
      Serial.println("connected");
      
      // **確認訂閱成功**
      if (client.subscribe(mqtt_topic_sub)) {
        Serial.println("Subscribed to topic: " + String(mqtt_topic_sub));
      } else {
        Serial.println("Subscription failed!");
      }
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

//秤重用
void collectWeightData() {
    String Weight = "A";
    Weight.reserve(50); // 預先分配記憶體，避免記憶體碎片化
    int readings = 0;
    unsigned long lastReadTime = millis(); // 記錄上次讀取的時間

    while (readings < 10) {
        if (millis() - lastReadTime >= 500) { // 每 500ms 讀取一次
            lastReadTime = millis(); // 更新計時器
            String weightValue = Get_Weight_Safe();
            Weight += "," + weightValue;
            readings++;
        }
    }

    Weight += "," + ID;
    client.publish(mqtt_topic_pub, Weight.c_str()); // 發送數據
    Serial.println("Sent weight data: " + Weight);
}

//當收到 MQTT 訊息時呼叫，處理命令。
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
  }
  Serial.println();

  if (strcmp(topic, mqtt_topic_sub) == 0) {
    if ((char)payload[0] == '1') {
      Weight = "A";
      for (i = 1; i <= 10; i++) {
        temp_Weight = Get_Weight();
        Weight = Weight + "," + temp_Weight;
        delay(500);
      }
      Weight = Weight + "," + ID;
      
      // 確保 Weight 內容正確
      Serial.print("Publishing MQTT Data: ");
      Serial.println(Weight);

      if (client.publish(mqtt_topic_pub, Weight.c_str())) {
        Serial.println("MQTT Publish Successful");
      } else {
        Serial.println("MQTT Publish Failed");
      }
    } else if ((char)payload[0] == '9') {
      Weight = "R," + ID;
      if (client.publish(mqtt_topic_pub, Weight.c_str())) {
        Serial.println("MQTT Identity Publish Successful");
      } else {
        Serial.println("MQTT Identity Publish Failed");
      }
    } else {
      Serial.println("Invalid command received");
    }
  }
}
