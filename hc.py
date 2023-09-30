import os
import sys
import signal
import time
import logging
import spidev as SPI
from lib import LCD_1inch69
from PIL import Image, ImageDraw, ImageFont
from guizero import App, PushButton, Picture, Text
from gpiozero import LED, MCP3008
import RPi.GPIO as GPIO
from time import sleep

INCREASE_BUTTON_GPIO = 17
DECREASE_BUTTON_GPIO = 22
temp_setpoint = 65
flag_heater_status = "off"
flag_request_heat = "off"
flag_heater_error = "off"
current_temp = "-"
status_message = "Loading..."

NUM_TEMP_SAMPLES = 50
NUM_TEMP_PASSES = 4

#Display pin configuration
RST = 27
DC = 25
BL = 18
bus = 0
device = 0

meas_list = []

disp = LCD_1inch69.LCD_1inch69()
disp.Init()
disp.clear()
FontLarge = ImageFont.truetype("/home/dking/poolcontroller/font/Font02.ttf",80)
FontSmall = ImageFont.truetype("/home/dking/poolcontroller/font/Font02.ttf",40)

image1 = Image.new("RGB", (disp.width,disp.height), "BLACK")
draw = ImageDraw.Draw(image1)
draw.text((75,50), str(current_temp), fill = "WHITE", font=FontLarge)
draw.text((90,160), str(temp_setpoint), fill = "WHITE", font=FontSmall)
draw.text((20,220), str(status_message), fill = "WHITE", font=FontSmall)
disp.ShowImage(image1)

def check_sensors():
	check_leds()
	check_temp()

def status(msg):
	global status_message
	status_message = msg

def error(msg):
	global flag_heater_error
	global status_message
	flag_heater_error = "on"
	status_message = msg

def clear_error():
	global status_message
	global flag_heater_error
	flag_heater_error = "off"
	status_message = ""

def heater_status(status):
	global flag_heater_status
	if (status=="on"):
		flag_heater_status = "on"
	else:
		flag_heater_status = "off"

def set_heater(status):
	global flag_request_heat
	if (status=="on"):
		flag_request_heat = "on"
		heater.on()
	else:
		flag_request_heat = "off"
		heater.off()

def check_leds():
	meas_list = []
	meas_max = 0
	sensor_list = ["heater","error"]
	val_list = []

	while (len(val_list) < len(sensor_list)):
		sensor_name = sensor_list[len(val_list)]
		if(sensor_name=="heater"):
			sensor = heat_sensor
		else:
			sensor = error_sensor
		meas_list.clear()
		meas_max = 0
		while (len(meas_list) < 30):
			val = round(sensor.value * 3.3,3)
			meas_list.append(val)
			if (val > 1.8):
				meas_max = meas_max + 1
			sleep(.001)
		val_list.append(meas_max)

	if (val_list[0] > 3):
		heater_status("on")
	else:
		heater_status("off")

	if (val_list[1] > 3):
		error("Check Flow")
	else:
		clear_error()

def check_temp():
	global current_temp
	temp_list = []
	while (len(temp_list) < NUM_TEMP_SAMPLES):
		val = round(temp_sensor.value * 3.3,3)
		temp_list.append(val)
		sleep(.001)
	avg = round(sum(temp_list)/len(temp_list),3)
	meas_list.append(avg)
	print("t" + str(len(meas_list)) + ": " + str(avg))
	if (len(meas_list)==NUM_TEMP_PASSES):
		avg = round(sum(meas_list)/len(meas_list),3)
		temp = voltage_to_temp(round(avg,2))
		meas_list.clear()
		print("Avg temp: " + str(temp))
		current_temp = str(temp)
		if (temp < int(temp_setpoint)):
			set_heater("on")
		else:
			set_heater("off")

def voltage_to_temp(v):
	temp = int(round(-31.746 * (v - 5.1902),1))
	return temp

temp_sensor = MCP3008(channel=0,differential=True,max_voltage=3.3,device=1)
heat_sensor = MCP3008(channel=2,differential=True,max_voltage=3.3,device=1)
error_sensor = MCP3008(channel=4,differential=True,max_voltage=3.3,device=1)
heater = LED("GPIO16")

def signal_handler(sig, frame):
	GPIO.cleanup()
	sys.exit(0)

def increase_pressed_callback(channel):
	print("Increase Pressed via Interrupt")
	global temp_setpoint 
	temp_setpoint= int(temp_setpoint) + 1
	#print("New setpoint = " + str(temp_setpoint))

def decrease_pressed_callback(channel):
        print("Decrease Pressed via Interrupt")
        global temp_setpoint 
        temp_setpoint= int(temp_setpoint) - 1
        #print("New setpoint = " + str(temp_setpoint))

if __name__=='__main__':
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(INCREASE_BUTTON_GPIO,GPIO.IN,pull_up_down=GPIO.PUD_UP)
	GPIO.setup(DECREASE_BUTTON_GPIO,GPIO.IN,pull_up_down=GPIO.PUD_UP)


GPIO.add_event_detect(INCREASE_BUTTON_GPIO,GPIO.FALLING, callback=increase_pressed_callback,bouncetime=500)
GPIO.add_event_detect(DECREASE_BUTTON_GPIO,GPIO.FALLING, callback=decrease_pressed_callback,bouncetime=500)

def update_display():
	disp = LCD_1inch69.LCD_1inch69()
	background = "BLACK"
	textfill = "WHITE"
	setpointfill = "WHITE"

	if(flag_request_heat == "on"):
		setpointfill = "RED"
	
	if (flag_heater_error == "on"):
		background = "YELLOW"
		textfill = "BLACK"
		setpointfill = "BLACK"
	elif(flag_heater_status == "on"):
		background = "RED"
		setpointfill = "WHITE"

	image1 = Image.new("RGB", (disp.width,disp.height), background)
	draw = ImageDraw.Draw(image1)
	draw.text((75,50), str(current_temp), fill = textfill, font=FontLarge)
	draw.text((90,160), str(temp_setpoint), fill = setpointfill, font=FontSmall)
	draw.text((20,220), str(status_message), fill = textfill, font=FontSmall)
	disp.ShowImage(image1)
	return()
	
while True:
	update_display()
	check_sensors()
	sleep(.001)
	


#signal.signal(signal.SIGINT,signal_handler)
#signal.pause
