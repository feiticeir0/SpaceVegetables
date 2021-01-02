import sys
import time
import schedule
import glob
import os
import requests
import logging
from systemd.journal import JournalHandler
import configparser

config = configparser.ConfigParser()
config.read ('SpaceVegetablesTweeter.ini')


url_web_services = config['default']['urlWebServices']

""" LOGGING """
log = logging.getLogger('SpaceVegetablesTweeter')
log_fmt = logging.Formatter("%(levelname)s %(message)s")
log_ch = JournalHandler()
log_ch.setFormatter(log_fmt)
log.addHandler(log_ch)
log.setLevel(logging.DEBUG)


# try to import modules
# picamera
try:
    import picamera
except ImportError:
    print ("Picamera Python module is not installed")
    print ("Execute sudo pip3 install picamera")
    sys.exit()

#PIL
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print ("Pillow-PIL is not installed")
    print ("Execute sudo pip3 install Pillow-PIL")
    sys.exit()


# Twitter
try:
    import tweepy
except ImportError:
    print ("Tweepy is not installed")
    print ("Execute sudo pip3 install tweepy")


#constants
pictureFolder = config['default']['pictureFolder']
pictureWaterMark = config['default']['pictureWaterMark']

# Twitter settings
def get_api(cfg):
    auth = tweepy.OAuthHandler(cfg['consumer_key'], cfg['consumer_secret'])
    auth.set_access_token(cfg['access_token'], cfg['access_token_secret'])
    return tweepy.API(auth)

# sendToTwitter()
def sendToTwitterv2():
    log.info("Sending to Twitter")
    cfg = {
            "consumer_key"          : config['twitter']['consumerKey'],
            "consumer_secret"       : config['twitter']['consumerSecret'],
            "access_token"          : config['twitter']['accessToken'],
            "access_token_secret"   : config['twitter']['accessTokenSecret']
    }

    api = get_api(cfg)
    # get latest file in directory
    list_of_files = glob.glob('images/*.jpg')
    latest_file = max(list_of_files, key=os.path.getctime)

    #status message
    message = getEnvironment()
    message += "#spacevegetables #element14 #1meterofpi"
    status = api.update_with_media (pictureFilename, message)


# add a watermark
def addWatermark():
    log.info("Adding watermark")
    # size of watermark to add
    # Remember - should be a small image - change dimentions here
    # NOTE: Probably do this automatically :)
    size_w = 105
    size_h = 105
    # load watermark
    img_watermark = Image.open(pictureWaterMark)
    # load image taken from camera
    img_orig = Image.open(pictureFilename)
    

    # Perform calculations for the image size
    img_w, img_h = img_orig.size
    # the 20 is a margin from the edge of W and H
    def_w = (img_w - 20) - size_w
    def_h = (img_h - 20) - size_h
    img_orig.paste(img_watermark, (def_w, def_h), img_watermark)
    img_orig.save(pictureFilename)
    #img_orig.show()

def addTimestamp():
    log.info("Adding timestamp")
    img = Image.open(pictureFilename)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/ttf-bitstream-vera/Vera.ttf", 20)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    draw.text((953,1050),stamp, (255,255,255),font=font)
    img.save (pictureFilename)

""" Get environment status
from Space Vegetables """
def getEnvironment():
    log.info("Getting environmental status")
    response = requests.get(url_web_services + 'all')
    # get all we need about environment
    r = response.json()
    units = ["",
            " %",
            " lux",
            "",
            "hPa",
            " ppm",
            "ºC",
            ""]
    print (r)
    message = ""
    unitsval = 0
    for values in r:
        if values == "humidity" or values == "temperature":
            continue
        val = "{:<20}{} {}".format(values,r[values],units[unitsval])
        unitsval += 1
        message += val + "\n"
    return message


# schedule to send to twitter
log.info("Scheduling sending to Twitter")
schedule.every(4).hours.do(sendToTwitterv2)

# main
if __name__ == "__main__":
    while True:
        log.info("Taking a picture")
        pictureFilename = pictureFolder + time.strftime("%Y%m%d-%H%M%S") + '.jpg'
        with picamera.PiCamera() as camera:
            camera.resolution = (1920,1080)
            #camera.rotation = 180
            camera.start_preview()
            time.sleep(3)
            camera.capture(pictureFilename)
            camera.stop_preview()

        #add watermark
        addWatermark()

        #add timestamp
        addTimestamp()

        # sleep 10 minutes
        log.info("Sleeping 10 minutes")
        time.sleep(600)
        schedule.run_pending()

