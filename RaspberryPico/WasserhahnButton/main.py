# Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-w-micropython-ebook/

import machine, time, network, socket
from simple import MQTTClient
from machine import Pin


# Wi-Fi credentials 
SSID = 'Tom-Net-Main'
#SSID = 'Tom-Net-UG'
PASSWORD = 'Meerschweinchen?ZFT-2014'
#PASSWORD = 'Garfield20077'
STATIC_IP = '192.168.1.172'
SUBNET_MASK = '255.255.255.0'
GATEWAY = '192.168.1.1'
DNS = '8.8.8.8'

# MQTT-Broker-Konfiguration
BROKER = "192.168.1.205"  # Öffentlicher MQTT-Broker
PORT = 11883
CLIENT1_ID = "pico_client_1"
CLIENT2_ID = "pico_client_2"
TOPIC = "Garten/Wasserhahn/Command"

# Initialisierung der Onboard-LED
led_onboard = Pin("LED", Pin.OUT)
led_error = Pin(14, Pin.OUT)
led_wlan = Pin(15, Pin.OUT)
led_status = Pin(13, Pin.OUT)

# Initialisierung von GPIO14 als Eingang mit internem PULLDOWN-Widerstand
btn = Pin(12, Pin.IN, Pin.PULL_DOWN)

led_onboard.on()
led_error.off()
led_wlan.off()
led_status.off()

# Taster-Funktion
def button_handler(pin):
    mqtt_publish("on")

# Nachricht veröffentlichen
def mqtt_publish(payload):
    client1 = MQTTClient(CLIENT1_ID, BROKER, PORT)
    client1.connect()
    print("Mit MQTT-Broker verbunden")
    
    client1.publish(TOPIC, payload)
    print(f"Nachricht veröffentlicht: {payload}")
    
    client1.disconnect()
    print("Verbindung zum MQTT-Broker getrennt")    

def mqtt_callback(topic, payload):
    # MQTT-Nachricht ausgeben
    print("Topic: %s, Wert: %s" % (topic, payload))
    print()
    if payload == b'0':
        led_status.off()
    else:
        led_status.on()
        

# Connect to WLAN
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

# Wait for Wi-Fi connection
connection_timeout = 10
while connection_timeout > 0:
    if wlan.status() >= 3:
        break
    connection_timeout -= 1
    print('Waiting for Wi-Fi connection...')
    time.sleep(1)

# Check if connection is successful
if wlan.status() != 3:
    led_error.on()
    led_wlan.off()
    raise RuntimeError('Failed to establish a network connection')
else:
    print('Connection successful!')
    led_error.off()
    led_wlan.on()
    wlan.ifconfig((STATIC_IP, SUBNET_MASK, GATEWAY, DNS))

# Taster-Auslösung
btn.irq(trigger=Pin.IRQ_RISING, handler=button_handler)

client2 = MQTTClient(CLIENT2_ID, BROKER, PORT)
client2.set_callback(mqtt_callback)
client2.connect()
client2.subscribe(topic="Garten/Wasserhahn/Status")

while True:
    # LED einschalten
    led_onboard.on()
    # halbe Sekunde warten
    time.sleep(0.5)
    # LED ausschalten
    led_onboard.off()
    client2.check_msg()
    # 1 Sekunde warten
    time.sleep(1)    
