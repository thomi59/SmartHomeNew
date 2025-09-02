# Rui Santos & Sara Santos - Random Nerd Tutorials
# Complete project details at https://RandomNerdTutorials.com/raspberry-pi-pico-w-micropython-ebook/

import machine, onewire, ds18x20, time, network, socket, ntptime, ujson
import webrepl
from simple import MQTTClient
from machine import Pin


# Wi-Fi credentials
SSID = 'Tom-Net-Main'
#SSID = 'Tom-Net-UG'
PASSWORD = 'Meerschweinchen?ZFT-2014'
#PASSWORD = 'Garfield20077'
STATIC_IP = '192.168.1.192'
SUBNET_MASK = '255.255.255.0'
GATEWAY = '192.168.1.1'
DNS = '8.8.8.8'

# MQTT-Broker-Konfiguration
BROKER = "192.168.1.205"  # Öffentlicher MQTT-Broker
PORT = 11883
CLIENT_ID = "pico_client"
TOPIC = "Gefrierschrank/Temperatur"

# Initialisierung der Onboard-LED
led_onboard = Pin("LED", Pin.OUT)
led_error = Pin(14, Pin.OUT)
led_wlan = Pin(15, Pin.OUT)

# Pin configuration for DS18B20 temperature sensor
ds_pin = machine.Pin(22)

# Create DS18X20 object using OneWire protocol with specified pin
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

led_onboard.on()
led_error.off()
led_wlan.off()

# Zeit synchronisieren
def sync_time():
    print("Synchronisiere Zeit via NTP...")
    try:
        ntptime.host = "129.6.15.28"  # ch.pool.ntp.org (ntp-server Schweiz)
        ntptime.settime()
        print("Zeit synchronisiert.")
    except:
        print("Fehler bei NTP-Zeit.")
        
# Schritt 2: UTC → Schweizer Zeit (MEZ / MESZ)
# Funktion zur Sommerzeit-Erkennung für Schweiz (MESZ)
def is_dst(year, month, day, hour):
    # Letzter Sonntag im März
    for d in range(31, 24, -1):
        t = time.mktime((year, 3, d, 0, 0, 0, 0, 0))
        if time.localtime(t)[6] == 6:  # Sonntag
            march_last_sunday = d
            break

    # Letzter Sonntag im Oktober
    for d in range(31, 24, -1):
        t = time.mktime((year, 10, d, 0, 0, 0, 0, 0))
        if time.localtime(t)[6] == 6:
            oct_last_sunday = d
            break

    # Sommerzeit gilt zwischen: letzter So März, 2:00 Uhr bis letzter So Okt, 3:00 Uhr
    if (month > 3 and month < 10):
        return True
    elif month == 3 and (day > march_last_sunday or (day == march_last_sunday and hour >= 2)):
        return True
    elif month == 10 and (day < oct_last_sunday or (day == oct_last_sunday and hour < 3)):
        return True
    else:
        return False

# Schweizer Zeit aus UTC berechnen
def get_swiss_time():
    t = time.localtime()  # UTC-Zeit vom System
    year, month, day, hour, minute, second, *_ = t

    offset = 2 if is_dst(year, month, day, hour) else 1  # MESZ oder MEZ
    hour = (hour + offset) % 24

    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        year, month, day, hour, minute, second
    )

def celsius_to_fahrenheit(temp_celsius):
    # Convert temperature from Celsius to Fahrenheit
    temp_fahrenheit = temp_celsius * (9/5) + 32 
    return temp_fahrenheit

# Nachricht veröffentlichen
def mqtt_publish(payload):
    client = MQTTClient(CLIENT_ID, BROKER, PORT)
    client.connect()
    print("Mit MQTT-Broker verbunden")
    
    client.publish(TOPIC, payload)
    print(f"Nachricht veröffentlicht: {payload}")
    
    client.disconnect()
    print("Verbindung zum MQTT-Broker getrennt")    

# Scan for DS18B20 sensors and print their ROM addresses
roms = ds_sensor.scan()
print('Found DS devices: ', roms)

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
    webrepl.start(8266, 'livia2011')

while True:
    # Initiate temperature conversion for all sensors
    ds_sensor.convert_temp()
    time.sleep_ms(750)  # Wait for the conversion to complete (750 ms is recommended)

    sync_time()
    print("Programmstart:", get_swiss_time())
    
    for rom in roms:
        print(rom)
        
        # Read temperature in Celsius from the sensor
        temp_c = ds_sensor.read_temp(rom)
        
        # Convert Celsius temperature to Fahrenheit
        temp_f = celsius_to_fahrenheit(temp_c)
        datum = get_swiss_time()

        # Print the temperature readings
        print('temperature (ºC):', "{:.2f}".format(temp_c))
        print('temperature (ºF):', "{:.2f}".format(temp_f))
        print()
        data = {
            "time": datum,
            "value": "{:.2f}".format(temp_c)
        }
        json_data = ujson.dumps(data)
        mqtt_publish(json_data)

    time.sleep(60)  # Wait for 60 seconds before taking readings again

