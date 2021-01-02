import xmlrpc.client
import time
import datetime
import threading
import prctl
import serial
import schedule
import sys
import logging
from systemd.journal import JournalHandler
import urllib3
from subprocess import PIPE, Popen
import telegram
import board
import busio
from adafruit_htu21d import HTU21D
import configparser

from bme280 import BME280
from ltr559 import LTR559

import sqlite3


from PIL import Image, ImageFont, ImageDraw
import ST7735 as ST7735
from fonts.ttf import Roboto as UserFont

# Create ST7735 LCD display class.
disp = ST7735.ST7735 (
        port=0,
        cs=1,
        dc=9,
        backlight=12,
        rotation=270,
        spi_speed_hz=1000000
)


config = configparser.ConfigParser()
config.read ('SpaceVegetablesClient.ini')


""" Remove text is draw a rectangle
    where text is written
    0 = temperature
    1 = humidity
    2 = ph
    3 = tds
"""
def removeText():
    rectElements =  [17, 32, 47, 63]
    del_rectangle = 40

    for i in range(4):
        # draw the rectangle in all elements
        draw.rectangle ((118, rectElements[i], 118 + del_rectangle, rectElements[i] + 15), (255, 182, 141))

    # draw.rectangle ((118, rectElements[element], 118 + del_rectangle, rectElements[element] + 15), (255, 182, 141))
    return 0

""" Write text to the LCD """

def writeText (elements):
    disp.set_backlight(1)
    rectElements =  [17, 32, 47, 63]
    for i in range(4):
        draw.text((118,rectElements[i]), elements[i], font=font, fill=(255, 255, 255))

    disp.display(image)
    time.sleep(300)
    disp.set_backlight(0)
    return 0


""" threads to function above write text
    only write text needs thread
    the removetext is called before to erase any previous values
"""
def tWriteText(elements):
    log.info("Thread to write text")
    twt = threading.Thread(target = writeText, args=(elements,))
    twt.setName ('Write text')
    twt.start()

font_size = 13
font = ImageFont.truetype(UserFont, font_size)

# Initialise display.
disp.begin()

image = Image.open(config['default']['backgroundImage'])
draw = ImageDraw.Draw(image)
disp.display(image)


# constants
# ThingSpeak
TSUrl = config['thingspeak']['url']

# temperature/humidity/pressure - enviro
bme280 = BME280()

# temperature/humidity HTU21
i2c = busio.I2C (board.SCL, board.SDA)
sensorhtu21d = HTU21D(i2c)

# sleep time is in seconds
# multiply per 60 for minutes
# airPumpTimeOn = 60 * 15     # 15 minutes
#waterPumpTimeOn = 60 * 20   # 20 minutes 
# lightsTimeOn = 60 * 60 * 10  # 10 hour

airPumpTimeOn = int(config['default']['airpumptimeon']) * 60     # 15 minutes
waterPumpTimeOn = int(config['default']['waterpumptimeon']) * 60  # 20 minutes 
lightsTimeOn = int(config['default']['lightstimeon']) * 60 * 60  # 10 hour

# Server_IP_address = "192.168.2.77"
Server_IP_address = config['default']['serverIpAddress']

# Telegram token
token = config['telegram']['telegramToken']
chatId = config['telegram']['chatId']

""" This function sends a message to Telegram """
""" Going to use only to main functions """
def sendMessageTelegram (msg, 
        chat_id = chatId,
        token = token):
    msg = "EnviroPI: " + msg
    bot = telegram.Bot(token=token)
    try:
        bot.sendMessage(chat_id=chat_id, text=msg)
    except telegram.error.NetworkError:
        # If there's some problem, handling the exception
        # so the SpaceVegetablesClient will not exit with an error
        # If cannot reach telegram or internet, just continue
        pass


""" Read TDS values from Arduino Pro Micro """
def getTDS():
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    readtds = ser.readline().decode('utf-8').rstrip()
    return (readtds)

""" LOGGING """
log = logging.getLogger('SpaceVegetablesClient')
log_fmt = logging.Formatter("%(levelname)s %(message)s")
log_ch = JournalHandler()
log_ch.setFormatter(log_fmt)
log.addHandler(log_ch)
log.setLevel(logging.DEBUG)


""" Functions definitions """

""" DATABASE FUNCTIONS """
""" This will get environmental condiditions
    and populate the database with those conditions
"""
bme280 = BME280()
ltr559 = LTR559()

def sendToThingSpeak (url):
    log.info ("Updating ThingSpeak")
    toUpdate = TSUrl + url
    f = urllib3.PoolManager()
    response = f.request('GET',toUpdate)


def get_cpu_temperature():
    process = Popen(['/usr/bin/vcgencmd', 'measure_temp'], stdout=PIPE, universal_newlines=True)
    output, _error = process.communicate()
    return float(output[output.index('=') + 1:output.rindex("'")])

def environmentalConditions(conn):
    print("Getting environmental data")
    log.info("Getting environmental data")
    # get data
    #temperature = round(bme280.get_temperature(),1)
    humidity = round(bme280.get_humidity(),1)
    pressure = round(bme280.get_pressure(),1)
    lux = round(ltr559.get_lux(),1)


    #smooth cpu temperature
    cpu_temps = [get_cpu_temperature()] * 5

    factor = 7.00

    cpu_temp = get_cpu_temperature()
    cpu_temps = cpu_temps[1:] + [cpu_temp]
    avg_cpu_temp = sum(cpu_temps) / float (len(cpu_temps))
    raw_temp = bme280.get_temperature()

    temperature = round(raw_temp - ((avg_cpu_temp - raw_temp) / factor),1)


    humidityInside = round(sensorhtu21d.relative_humidity,1)
    temperatureInside = round(sensorhtu21d.temperature,1)
    
    #get TDS
    tds = getTDS()
    
    # get datetime
    dt = datetime.datetime.now()
    # format the date time to insert into the database
    dtdb = dt.strftime ("%Y-%m-%d %H:%M:%S")

    curs = conn.cursor()

    log.info("Populating database with environmental data")
    curs.execute (""" insert into Vegetables (TDS,temperature,humidity,pressure,lightSensor,temperatureInside,humidityInside,dateTime) values ((?),(?),(?),(?),(?),(?),(?),(?)) """, (tds, temperature, humidity, pressure, lux, temperatureInside, humidityInside,dtdb))
    conn.commit()

    # Send to thingspeak
    log.info("Updating ThingSpeak")
    field1 = str(temperatureInside)
    field2 = str(humidityInside)
    field3 = str(pressure)
    field4 = str(lux)
    field5 = str(tds)
    field6 = str(0)

    toUpdate = "&field1=" + field1 + "&field2=" + field2 + "&field3=" + field3 + "&field4=" + field4 + "&field5=" + field5 + "&field6=" + field6
    sendToThingSpeak (toUpdate)
    # update display
    # remove all from display
    removeText()
    disp.display(image)
    # update
    toOSD = [field1, field2, field6, field5]
    tWriteText(toOSD)



def setDBWaterPump(conn,pumpState):
    log.info("Populating water pump state into database")
    # get datetime
    dt = datetime.datetime.now()
    # format the date time to insert into the database
    dtdb = dt.strftime ("%Y-%m-%d %H:%M:%S")

    curs = conn.cursor()
    curs.execute (""" insert into Vegetables (waterPumpActive, dateTime) values ((?), (?)) """, (pumpState, dtdb))
    conn.commit()

    toUpdate = "&field7=" + str(pumpState)
    sendToThingSpeak(toUpdate)


def setDBAirPump(conn,pumpState):
    log.info("Populating air pump state into database")
    # get datetime
    dt = datetime.datetime.now()
    # format the date time to insert into the database
    dtdb = dt.strftime ("%Y-%m-%d %H:%M:%S")

    curs = conn.cursor()
    curs.execute (""" insert into Vegetables (airPumpActive, dateTime) values ((?), (?)) """, (pumpState, dtdb))
    conn.commit()

    toUpdate = "&field8=" + str(pumpState)
    sendToThingSpeak(toUpdate)


def setDBLights(conn,lightsState):
    log.info("Populating lights state into database")
    # 0 - off
    # 1 - on
    # get datetime
    dt = datetime.datetime.now()
    # format the date time to insert into the database
    dtdb = dt.strftime ("%Y-%m-%d %H:%M:%S")

    curs = conn.cursor()
    curs.execute (""" insert into Vegetables (lightsActive, dateTime) values ((?), (?)) """, (lightsState, dtdb))
    conn.commit()

""" Lights will have their own timer """

""" 
Start and stop Air Pump for oxigenation of water
"""
def airPump(conn):
    prctl.set_name("Air Pump")
    # to OSD
    sendMessageTelegram("Activating Air Pump")
    log.info("Activating air pump into automationPI")
    server = xmlrpc.client.ServerProxy ('http://' + Server_IP_address + ':8000', allow_none=True)
    server.turnAirPump(1)
    # set air pump db
    setDBAirPump(conn,1)
    time.sleep(airPumpTimeOn)
    sendMessageTelegram("Stoping Air Pump")
    log.info("Deactivating air pump into automationPI")
    server.turnAirPump(0)
    setDBAirPump(conn,0)

""" 
Start and stop water pump for NFC
"""
def waterPump(conn):
    # set thread name
    prctl.set_name("Water Pump")
    log.info("Activating water pump into automationPI")
    sendMessageTelegram("Activating water pump Pump")
    server = xmlrpc.client.ServerProxy ('http://' + Server_IP_address + ':8000', allow_none=True)
    server.turnWaterPump(1)
    setDBWaterPump(conn,1)
    time.sleep(waterPumpTimeOn)
    sendMessageTelegram("Stoping water Pump")
    log.info("Deactivating water pump into automationPI")
    server.turnWaterPump(0)
    setDBWaterPump(conn,0)
    return 0

""" OLD: Before testing resulted in success
    with one function to control all
"""
#def turnLights(conn):
#    prctl.set_name("Lights")
#    log.info("Turnin on lights into automationPI")
#    sendMessageTelegram ("Turning On Lights")
#    server = xmlrpc.client.ServerProxy ('http://' + Server_IP_address + ':8000', allow_none=True)
#    server.turnLightsv2()
#    setDBLights(conn,1)


def turnLights(conn):
    prctl.set_name("Lights")
    log.info("Turning on lights into automationPI")
    sendMessageTelegram ("Turning On Lights")
    server = xmlrpc.client.ServerProxy ('http://' + Server_IP_address + ':8000', allow_none=True)
    server.turnLights(1)
    setDBLights(conn,1)
    time.sleep(lightsTimeOn)
    #server = xmlrpc.client.ServerProxy ('http://' + Server_IP_address + ':8000', allow_none=True)
    log.info("Turning off lights")
    sendMessageTelegram("Turnin off lights")
    server.turnLights(0)
    setDBLights(conn,0)
    return 0


""" The functions to spawn threads """
def tAirPump(conn):
    log.info("Thread to air pump")
    ax = threading.Thread (target = airPump, args=(conn,))
    ax.setName ('Air Pump')
    ax.start()
    return 0

def tWaterPump(conn):
    log.info("Thread to water pump")
    aw = threading.Thread (target = waterPump,args=(conn,))
    aw.setName('Water Pump')
    aw.start()
    return 0

def tLights(conn):
    log.info("Thread to lights")
    atl = threading.Thread (target = turnLights,args=(conn,))
    atl.setName('Lights')
    atl.start()
    return 0

""" In case of a power outage, check if the lights should be active
    because the instructions to turn the lights on
    comes from the client - that is schedule at 8am
    if it reboots, it will schedule for next day 8am

    This function will run before the main function
    It only runs once, when the program starts
    like if a reboot or startup
"""

def checkActiveLights():
    global lightsTimeOn
    log.info("Checking if lights needed to be active")
    now = datetime.datetime.now().time()
    start8am = datetime.time(8,0,0)
    end18pm = datetime.time(18,0,0)
    if now > start8am and now < end18pm:
        #need to turn them on
        #but make some time diferences
        toend = datetime.datetime.combine(datetime.date.today(),end18pm)
        tonow = datetime.datetime.combine(datetime.date.today(),now)
        stilLit = toend - tonow
        lightsTimeOn = round(stilLit.total_seconds(),0)
        msg = "Power outage. Turning lights on for: " + str(lightsTimeOn)
        sendMessageTelegram (msg)
        log.info(msg)
        # call the functions to turn the lights
        tLights(conn)
    else:
        log.info("Not the corret time to activate lights")

    return 0


"""
    Reseting here the light time because
    if there's a power outage, this variable gets changed
    to the time left until 18:00. If nothing more happens
    that value remains, so, next time at 0800, when the lights
    turn on, the last value remains and the lights turn off at that time
    called everyday at 07:50
"""
def resetLightsTime():
    global lightsTimeOn
    lightsTimeOn = 60 * 60 * 10 #10 hours
    return 0


def checkActiveThreads():
    ac = threading.activeCount()
    log.info ("There are %s threads active", str(ac))
    sendMessageTelegram("There are " + str(ac) + " threads active")
    message = str(threading.enumerate())
    log.info(message)
    sendMessageTelegram (message)
    return 0

#set sqlite3 connection
log.info ("Connecting to database")
conn = sqlite3.connect("/home/pi/SpaceVegetablesClient/spaceVegetables.db", check_same_thread=False)
""" Scheduling """

# Schedules for water and air pump
""" Turn water pump every hour for about 15m """
""" airPumpTimedOn """ 
log.info("Scheduling air pump")
schedule.every().day.at("09:00").do(tAirPump,conn)
#schedule.every().day.at("11:00").do(tAirPump,conn)
schedule.every().day.at("13:00").do(tAirPump,conn)
#schedule.every().day.at("15:00").do(tAirPump,conn)
schedule.every().day.at("17:00").do(tAirPump,conn)
#schedule.every().day.at("19:00").do(tAirPump,conn)
schedule.every().day.at("21:00").do(tAirPump,conn)


""" Schedule - for now
The more the plants grow, the more time it needs to be pumping
In the off ligths period (night time), no pumping is needed
So, we're goint to specify every time
It's the only way
Remember to check the waterPumpTimedOn 
20m every 1.5 hours - for starters
"""
log.info("Scheduling water pump")
schedule.every().day.at("08:00").do(tWaterPump,conn)
schedule.every().day.at("09:30").do(tWaterPump,conn)
schedule.every().day.at("11:00").do(tWaterPump,conn)
schedule.every().day.at("12:30").do(tWaterPump,conn)
schedule.every().day.at("14:00").do(tWaterPump,conn)
schedule.every().day.at("15:30").do(tWaterPump,conn)
schedule.every().day.at("17:00").do(tWaterPump,conn)
schedule.every().day.at("18:30").do(tWaterPump,conn)
schedule.every().day.at("20:00").do(tWaterPump,conn)


# Turn lights on
log.info("Scheduling lights on")
schedule.every().day.at("08:00").do(tLights,conn)

# Environmental conditions
log.info("Scheduling environmental conditions")
schedule.every(30).minutes.do(environmentalConditions,conn)

# Scheduling reset lights time
log.info("Scheduling lights time reset")
schedule.every().day.at("07:50").do(resetLightsTime)

# threads active
log.info("scheduling active threads")
schedule.every(4).hours.do(checkActiveThreads)

# Check if lights needed to be started
# power outage and this function executes just at program start
checkActiveLights()

event = threading.Event()

sendMessageTelegram ("Starting server")
while True:
    schedule.run_pending()
    time.sleep(1)

