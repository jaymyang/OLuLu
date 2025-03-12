#ifndef __HX711__H__
#define __HX711__H__

#include <Arduino.h>

#define HX711_SCK 2
#define HX711_DT 15 //NodeMCU-32S的D3是無法做PWM的，改選D15或其他D-pin
//#define HX711_SCK 13 //在https://randomnerdtutorials.com/esp8266-load-cell-hx711/說這樣可以
//#define HX711_DT 12 //ESP8266，先試試看12

extern void Init_Hx711();
extern unsigned long HX711_Read(void);
extern unsigned int Get_Weight();
extern void Get_Maopi();

#endif