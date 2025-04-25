import network
import time
from umqtt.simple import MQTTClient
from machine import Pin, PWM, SoftI2C
import utime  
from dht import DHT22
import ssd1306  

SSID = "Wokwi-GUEST"
PASSWORD = ""

MQTT_BROKER = "mqtt-dashboard.com"  
CLIENT_ID = "ahmedchFise20242"  
TOPIC_LED1 = "home/led1"
TOPIC_LED2 = "home/led2"
TOPIC_SERVO = "home/servo"

led1 = Pin(5, Pin.OUT)  
led2 = Pin(18, Pin.OUT)  

i2c = SoftI2C(scl=Pin(22), sda=Pin(21), freq=400000)
oled_width = 128
oled_height = 64
oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

btn1 = Pin(26, Pin.IN)
btn2 = Pin(25, Pin.IN)

servo = PWM(Pin(13), freq=50)  

dht_sensor = DHT22(Pin(4))

buzzer = Pin(19, Pin.OUT)

def set_servo_angle(angle):
    duty = int((angle / 180) * 102 + 26) 
    servo.duty(duty)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        time.sleep(1)
    print("Connected to Wi-Fi! IP Address:", wlan.ifconfig()[0])

def mqtt_callback(topic, msg):
    print(f"Received message on topic {topic}: {msg}")
    if topic == TOPIC_LED1.encode() and msg == b"ON":
        led1.value(1)
    elif topic == TOPIC_LED1.encode() and msg == b"OFF":
        led1.value(0)
    elif topic == TOPIC_LED2.encode() and msg == b"ON":
        led2.value(1)
    elif topic == TOPIC_LED2.encode() and msg == b"OFF":
        led2.value(0)
    elif topic == TOPIC_SERVO.encode() and msg == b"OPEN":
        set_servo_angle(40)
        oled.fill(0)
        oled.text("Door Unlocked", 0, 0)
        oled.show()
        time.sleep(4)  
        set_servo_angle(90)
        oled.fill(0)
        oled.text("Door Locked", 0, 0)
        oled.show()

def connect_mqtt():
    client = MQTTClient(CLIENT_ID, MQTT_BROKER)
    client.set_callback(mqtt_callback)
    client.connect()
    print(f"Connected to MQTT Broker: {MQTT_BROKER}")
    client.subscribe(TOPIC_LED1)
    client.subscribe(TOPIC_LED2)
    client.subscribe(TOPIC_SERVO)
    return client

last_triggered = {btn1: 0, btn2: 0}  
DEBOUNCE_TIME_MS = 200  

def button_handler(pin):
    global last_triggered
    current_time = utime.ticks_ms()
    
    if utime.ticks_diff(current_time, last_triggered[pin]) > DEBOUNCE_TIME_MS:
        last_triggered[pin] = current_time
        
        if pin == btn1:
            led1.value(not led1.value())
            if led1.value() == 1:
                print("LED1 set manually to ON")
            else:
                print("LED1 set manually to OFF")
        elif pin == btn2:
            led2.value(not led2.value())
            if led2.value() == 1:
                print("LED2 set manually to ON")
            else:
                print("LED2 set manually to OFF")

btn1.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)
btn2.irq(trigger=Pin.IRQ_FALLING, handler=button_handler)

def update_oled():
    global temp
    oled.fill(0)
    oled.text("LED1: ON" if led1.value() == 1 else "LED1: OFF", 0, 0)
    oled.text("LED2: ON" if led2.value() == 1 else "LED2: OFF", 0, 10)
    temp = dht_sensor.temperature() 
    oled.text("Temp: {:.1f}C".format(temp), 0, 20)
    hum = dht_sensor.humidity()
    oled.text("Hum: {:.1f}%".format(hum), 0, 30)
    oled.show()

def read_dht22():
    try:
        dht_sensor.measure()  
        update_oled() 
        print("Temperature: {:.1f}C, Humidity: {:.1f}%".format(dht_sensor.temperature(), dht_sensor.humidity()))
        if temp >= 60: 
            print("Fire detected! Activating buzzer...")
            oled.fill(0)
            oled.text("FIRE DETECTED!", 0, 0)
            
            buzzer.value(1)  
            set_servo_angle(40)
            oled.text("Door Unlocked", 0, 10)
            oled.show()
        else:
            buzzer.value(0) 
            set_servo_angle(90)
    except OSError as e:
        print("Failed to read sensor.")

connect_wifi()
mqtt_client = connect_mqtt()
try:
    while True:
        mqtt_client.check_msg()  
        read_dht22()  
        time.sleep(2)  
except KeyboardInterrupt:
    print("Disconnecting...")
    mqtt_client.disconnect()