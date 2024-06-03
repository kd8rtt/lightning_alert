import network
import socket
from picozero import pico_temp_sensor, pico_led
from machine import Pin, WDT
import urequests
import time
import datetime


ssid = 'ENTER SSID'
password = 'ENTER PW'

def connect(indicator):
    count = 0
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False: # while trying to connect to Wi-Fi, flash the light
        count = count + 1
        print('Waiting for connection...')
        time.sleep(1)
        indicator.value(1)
        wdt.feed()
        if count > 29:
            machine.reset()
    indicator.value(0)
    print(wlan.ifconfig())  

def fetch_metar(airport):
    url = "https://aviationweather.gov/api/data/metar?ids=" + airport + "&format=raw&taf=false"
    response = urequests.get(url)
    print(response.text)
    return response.text

def check_lightning(metar_data):
    lightning_patterns = ["TS", "LTG"]
    for pattern in lightning_patterns:
        if pattern in metar_data:
            return True
    return False

def time_within_30_minutes(time1, time2):
    # Convert time strings to datetime objects
    if time1 == '9999':
        return False
    format_str = '%H%M'
    datetime1 = datetime.strptime(time1, format_str)
    datetime2 = datetime.strptime(time2, format_str)

    # Calculate the time difference
    time_diff = abs(datetime2 - datetime1)

    # Check if the time difference is within 30 minutes
    if time_diff <= timedelta(minutes=30):
        return True
    else:
        return False


def generate_alert(metar_data, last_lightning, t0):
    if check_lightning(metar_data): #check METAR for lightning indications
        last_lightning= metar_data[7:11]#record report time when lightning was detected
        lightning_active = 1 #generate alert for live lightning
    elif time_within_30_minutes(last_lightning, t0): #if no METAR indication now, check if there was one within last 30 minutes
        lightning_active = 2 #generate alert for recent lightning
    else:
        last_lightning = '9999' #reset lightning time
        lightning_active = 0 #turn off lightning alert
    return lightning_active, last_lightning

def print_to_terminal(airport, report_time, current_time, last_lightning_time, lightning_active, raw_metar): #this function prints a bunch of stuff for diagnostic purposes
    print('Airport:'),
    print(airport)

    print('Report time:'),
    print(report_time + 'Z')

    if last_lightning_time == '9999':
        pass
    else:
        print('Last lightning time:'),
        print(last_lightning_time + 'Z')

    print('Current time:'),
    print(current_time + 'Z')

    print('Lightning:'),
    if lightning_active == 1:
        print('Now')
    elif lightning_active == 2:
        print('Within last 30 minutes')
    else:
        print('Not detected')

    print('Report:'),
    print(raw_metar)
            

def main():
    last_lightning_time_1 = '9999' #initialize to an impossible time
    last_lightning_time_2 = '9999' #initialize to an impossible time
    lightning_active_1 = 0 #initialize to no active lightning
    lightning_active_2 = 0 #initialize to no active lightning
    airport_1 = 'KOJC' #specify first airport to check
    airport_2 = 'KIXD' #specify second airport to check
    wdt = WDT(timeout=8388)
    wdt.feed()
    led = Pin("LED", Pin.OUT)
    flash = Pin(0, Pin.OUT)
    run_led = Pin(15, Pin.OUT)
    run_led.value(1)
    led.value(1)
    connect(flash)
    
    while True: #main program loop
        wdt.feed()
        t = time.gmtime() #get current UTC time
        current_time = time.strftime("%H%M", t) #convert current UTC time to HHMM format
        wdt.feed()
        metar_data_1 = fetch_metar(airport_1) #get METAR for first airport
        wdt.feed()
        metar_data_2 = fetch_metar(airport_2) #get METAR for second airport
        wdt.feed()

        if metar_data_1: #check if METAR for first airport has contents
            report_time_1 = metar_data_1[7:11] #decode UTC time for report
            (lightning_active_1, last_lightning_time_1) = generate_alert(metar_data_1,last_lightning_time_1, current_time) #determine if an alert should be generated based on first airport 
        else:
            print("Failed to fetch METAR data for"), #print that METAR data not obtained
            print(airport_1),
            print("Retrying in 1 minute.")

        if metar_data_2: #check if METAR for second airport has contents
            report_time_2 = metar_data_2[7:11] #decode UTC time for report
            (lightning_active_2, last_lightning_time_2) = generate_alert(metar_data_2,last_lightning_time_2, current_time) #determine if an alert should be generated based on second airport 
        else:
            print("Failed to fetch METAR data for"), #print that METAR data not obtained
            print(airport_2),
            print("Retrying in 1 minute.")

        print('Station 1:')
        print_to_terminal(airport_1, report_time_1, current_time, last_lightning_time_1, lightning_active_1, metar_data_1)

        print('Station 2:')
        print_to_terminal(airport_2, report_time_2, current_time, last_lightning_time_2, lightning_active_2, metar_data_2)

        if lightning_active_1 or lightning_active_2 > 0:
            lightning_alert = 1
            print('Lightning Alert!')
        else:
            lightning_alert = 0

        flash.value(lightning_alert)
        print('Refreshing in 1 minute...')
        for x in range(11): # run through 12 times (12x5=60 total wait time)
            wdt.feed() # RP2040 has WDT limit of 8388ms for timeout, so need to use a for loop to let it go 60 seconds with intermediate pets
            print(x+1)
            time.sleep(5)  # sleep for 5 sec
            
            
    
    
if __name__ == "__main__":
    main()

