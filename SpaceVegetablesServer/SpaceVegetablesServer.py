from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
import datetime
import time
import threading
import automationhat
import logging
import telegram
from systemd.journal import JournalHandler
import configparser

from PIL import Image, ImageFont, ImageDraw
import ST7735 as ST7735

from fonts.ttf import Roboto as UserFont

# Create ST7735 LCD display class.
disp = ST7735.ST7735 (
        port=0,
        cs=ST7735.BG_SPI_CS_FRONT,
        dc=9,
        backlight=25,
        rotation=270,
        spi_speed_hz=4000000
)


class SimpleThreadedXMLRPCServer (ThreadingMixIn, SimpleXMLRPCServer):
    pass

config = configparser.ConfigParser()
config.read ('SpaceVegetablesServer.ini')


""" Variables definitions """
IP_address = config['default']['ipAddress']

""" AIR PUMP and White Lights are controled by an external RELAY
    controled by the outputs
"""

""" lights output """
# outputLights = 0
outputLights = int(config['default']['outputLights'])

""" Air Pump """
# outputAirPump = 2
outputAirPump = int(config['default']['outputAirPump'])


""" Water Pump """
""" Its the relay """
# outputWaterPump = 0
outputWaterPump = int(config['default']['outputWaterPump'])

# Telegram token
token = config['telegram']['telegramToken']
chatId = config['telegram']['chatId']

# constants
""" Time to keep lights on """
lightsTimeOn = 60 * 60 * 4 # 10 hours

""" LOGGING  """
log = logging.getLogger('SpaceVegetables')
log_fmt = logging.Formatter("%(levelname)s %(message)s")
log_ch = JournalHandler()
log_ch.setFormatter(log_fmt)
log.addHandler(log_ch)
log.setLevel(logging.DEBUG)



s = SimpleThreadedXMLRPCServer((IP_address, 8000), allow_none=True)
s.register_introspection_functions() #enables use of s.system.listMethods()
log.info("Starting XMLRPC Server")
 

""" Next functions will be displayed using threads """

""" This is a function to delete text from the LCD
    The element argument is what you want to delete
    
    Remove text is draw a rectangle
    where text is written
    0 = lights
    1 = air pump
    2 = water pump
"""
def removeText(element):
    disp.set_backlight(1)
    rectElements =  [30, 45, 60]
    del_rectangle = 30

    # draw the rectangle
    draw.rectangle ((130, rectElements[element], 
                    130 + del_rectangle, 
                    rectElements[element] + 15), 
                    (59, 55, 60))

    # the display will be done in the function
    disp.display(image)
    # sleep 5 minutes
    time.sleep(300)
    # reduce brightness of LCD
    disp.set_backlight(0)
    return 0


""" Write text to the LCD
"""
def writeText (element):
    disp.set_backlight(1)
    rectElements =  [30, 45, 60]
    draw.text((130,rectElements[element]), "On", font=font, fill=(156,170,171))
    disp.display(image)
    time.sleep(300)
    disp.set_backlight(0)
    return 0


# definig the threads
def tWriteText(element):
    log.info ("Thread to write text")
    twt = threading.Thread(target = writeText,args=(element,))
    twt.setName ('write text')
    twt.start()

def tRemoveText(element):
    log.info ("Thread to remove text")
    trt = threading.Thread(target = removeText,args=(element,))
    trt.setName ('remove text')
    trt.start()

""" this function will make sure that
    in case of a reboot - power outage -
    or restarting
    if something is running, will turn off
"""
def shutalloff():
    # turn off air pump
    automationhat.output[outputAirPump].off()
    # turn off water pump
    automationhat.relay.one.off()
    # turn off lights
    automationhat.output[outputLights].off()
    return 0


font_size = 13
font = ImageFont.truetype(UserFont, font_size)

# Initialise display.
disp.begin()


# color
text_color = (156, 170, 171)
background_color = (59, 55, 60)


image = Image.open("automation_image_LCD.jpg")
draw = ImageDraw.Draw(image)
# display the background
disp.display(image)

""" This function sends a message to Telegram """
""" Going to use only tomain functions """

def sendMessageTelegram (msg, 
        chat_id = chatId,
        token = token):
    msg = "AutomationPI: " + msg
    bot = telegram.Bot(token=token)
    try:
        bot.sendMessage(chat_id=chat_id, text=msg)
    except telegram.error.NetworkError:
        # If theres a problem with telegram or internet not available
        # dont let the SpaceVegetablesServer exit with error
        # just dont notify 
        pass


""" This function will turn the water pump on or off
    depende what comes from the client
"""
def turnAirPump(state):
    if state == 1:
        log.info("Turning air pump on")
        sendMessageTelegram ("Activating air pump")
        automationhat.output[outputAirPump].on()
        # display in the LCD
        tWriteText(1)
    else:
        log.info ("Turn air pump off")
        sendMessageTelegram ("Turning off air pump")
        automationhat.output[outputAirPump].off()
        # display in the LCD
        tRemoveText(1)
    return 0

s.register_function(turnAirPump)


""" this function will turn the water 
pump on or off depending on the state
"""
def turnWaterPump(state):
    if state == 1:
        # to OSD
        log.info("Turning water pump on")
        sendMessageTelegram ("Activating water pump")
        automationhat.relay.one.on()
        # display in the LCD
        tWriteText(2)
    else:
        # to OSD
        log.info("Turn water pump off")
        sendMessageTelegram ("Stoping water pump")
        automationhat.relay.one.off()
        # display in the LCD
        tRemoveText(2)
    return 0

s.register_function(turnWaterPump)

""" turn on lights """
""" White and Grow lights - red and blue """
def turnLights(state):
    if state == 1:
        # to OSD
        log.info("Turn lights on")
        sendMessageTelegram ("Activating lights")
        automationhat.output[outputLights].on()
        # display on the LCD
        tWriteText(0)
    else:
        # to OSD
        log.info("Turn lights off")
        sendMessageTelegram ("Stopping lights")
        automationhat.output[outputLights].off()
        # display in the LCD
        tRemoveText(0)
    return 0

s.register_function(turnLights)

""" turn on lights v2 """
""" White and Grow lights - red and blue """
def turnLightsv2():
    # to OSD
    log.info("Turn lights on")
    sendMessageTelegram ("Activating lights")
    automationhat.output[outputLights].on()
    time.sleep(lightsTimeOn) 
    # to OSD
    log.info("Turn lights off")
    sendMessageTelegram ("Stopping lights")
    automationhat.output[outputLights].off()
    return 0

s.register_function(turnLightsv2)


#turn off any thing that could be running
log.info("booting - Shuting all off")
shutalloff()

sendMessageTelegram ("Starting server")
while True:
    s.handle_request()
    
