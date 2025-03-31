#ifndef __HX711__H__
#define __HX711__H__

#include <Arduino.h>

#define HX711_SCK 2 //MCU32 用2，esp8266用13
#define HX711_DT 15 //NodeMCU-32S的D3是無法做PWM的，改選D15或其他D-pin；ESP8266用12

extern void Init_Hx711();
extern unsigned long HX711_Read(void);
extern unsigned int Get_Weight();
extern void Get_Maopi();

#endif
