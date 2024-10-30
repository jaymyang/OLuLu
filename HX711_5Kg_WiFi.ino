#include "HX711.h"
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "Rose-mesh";        //路由器SSID，視情況改
const char* password = "75521926";      // 密碼
const char* host = "192.168.1.101";     // PC端IP address of the PC
const uint16_t port = 8080;             // Port number for communication
//以下是秤重
char python_order; //是否秤重的指令
String Weight = "A";
String temp_Weight = "";
//HX711的設定
int Sec_Count = 0;
int Status = 0, Status_Pre = 1;
int Flag_Up = 0, Flag_Down = 0;
int i;

WiFiClient client;
//以下是setup
void setup() {
// 初始化序列埠，以便連上電腦偵錯
  Serial.begin(9600);      
  delay(10);
  Serial.println("Connecting to WiFi...");
 
// 連接 WiFi
  Serial.println();
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("WiFi connected");
  
// 初始化HX711模組連接的IO設置
  Init_Hx711();       
  Get_Maopi();    // 取皮重
  delay(3000);
  Get_Maopi();    // 再次取皮重
}

//以下是主程式
void loop() {
// 確認連接到 Python 伺服器
  if (!client.connect(host, port)) {
    Serial.println("Connection failed");
    delay(500); // 嘗試重新連接
    return;
  }
// 等待並接收來自 Python 的資料
  while (client.connected()) {
    if (client.available()) {
  python_order = client.read();
  if (python_order == '1') {  // Python 傳來開始信號
    Weight = "A";           // 初始化Weight字串
    for (i = 1; i <= 10; i++) {
      temp_Weight = Get_Weight(); // 計算放在感測器上的重物重量
      Weight = Weight + "," + temp_Weight;
      delay(500); //每0.5秒收一個數字
    }
   
    //if (!client.connect(host, port)) {
    //  Serial.println("Connection failed");
    //  delay(5000);  // 延遲後重試
    //  return;
    //}

    // 傳送訊息
    Serial.println("Sending message...");
    client.println(Weight);
    python_order = 'E';
  }

    // 等待回應（以後可以擴充成由伺服器端確認入字是否正確）
    //while (client.connected() && client.available() == 0) {
    //  delay(10);
    //}

    //while (client.available()) {
    //  String line = client.readStringUntil('\n');
    //  Serial.println(line);
    //}
      else {
        ;
    //client.stop(); // 關閉連線
    //delay(5000);   // 等待5秒後才允許再次傳送
  }
}
}
}
