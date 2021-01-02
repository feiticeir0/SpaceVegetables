from flask import Flask, request, jsonify
import os
import sqlite3

app = Flask(__name__)

app.debug = True


# Always get latest entries
# Empty variable is used when
# we want the latest entry that HAS VALUES
# or not - empty = 0 we don't want an empty value
# it's this way because are less calls 
def getDataFromDB(data,empty = 0):
    # connection to DB
    conn = sqlite3.connect ("/home/pi/SpaceVegetablesClient/spaceVegetables.db")
    cur = conn.cursor()
    if not empty:
        # data mas not be 0
        cur.execute("select " + data + " from Vegetables where " + data + " != 0.0 order by idVegetables desc limit 1")
    else:
        cur.execute("select " + data + " from Vegetables order by idVegetables desc limit 1")

    temp = cur.fetchone()
    if temp is None:
        return 0
    return temp[0]

# Router per definition
@app.route("/", methods=['GET'])
def home():
    return '<h1>Web services for Space Vegetables</h1>\n'

# Get temperature
@app.route('/api/v1/resources/temperature', methods=['GET'])
def getTemperature():
    return jsonify({'temperature':getDataFromDB('temperature')})

# Get temperature Inside
@app.route('/api/v1/resources/temperatureInside', methods=['GET'])
def getTemperatureInside():
    return jsonify({'temperature Inside':getDataFromDB('temperatureInside')})

# Get PH
@app.route('/api/v1/resources/ph', methods=['GET'])
def getPH():
    return jsonify({'ph':getDataFromDB('PH')})

# Get TDS
@app.route('/api/v1/resources/tds', methods=['GET'])
def getTDS():
    return jsonify({'tds':getDataFromDB('TDS')})

# Get humidity
@app.route('/api/v1/resources/humidity', methods=['GET'])
def getHumidity():
    return jsonify({'humidity':getDataFromDB('humidity')})

# Get humidity Inside
@app.route('/api/v1/resources/humidityInside', methods=['GET'])
def getHumidityInside():
    return jsonify({'humidity Inside':getDataFromDB('humidityInside')})

# Get pressure
@app.route('/api/v1/resources/pressure', methods=['GET'])
def getPressure():
    return jsonify({'pressure':getDataFromDB('pressure')})

# Get luminosity
@app.route('/api/v1/resources/luminosity', methods=['GET'])
def getLuminosity():
    return jsonify({'luminosity':getDataFromDB('lightSensor',1)})

# Get ligths on or off
@app.route('/api/v1/resources/lights', methods=['GET'])
def getLightStatus():
    return jsonify({'lights':getDataFromDB('lightsActive',1)})

# Get air pump on or off
@app.route('/api/v1/resources/airpump', methods=['GET'])
def getAirPumpStatus():
    return jsonify({'air pump active':getDataFromDB('airPumpActive',1)})

# Get water pump on or off
@app.route('/api/v1/resources/waterpump', methods=['GET'])
def getWaterPumpStatus():
    return jsonify({'water pump active':getDataFromDB('waterPumpActive',1)})

# Get all data
@app.route('/api/v1/resources/all', methods=['GET'])
def getAllData():
    temperature = getDataFromDB('temperature')
    temperatureInside = getDataFromDB('temperatureInside')
    humidity = getDataFromDB('humidity')
    humidityInside = getDataFromDB('humidityInside')
    pressure = getDataFromDB('pressure')
    luminosity = getDataFromDB('lightSensor',1)
    airPumpActive = getDataFromDB('airPumpActive',1)
    waterPumpActive = getDataFromDB('waterPumpActive',1)
    ph = getDataFromDB('PH')
    tds = getDataFromDB('TDS')
    # create response
    environment = [ 
            {
                'temperature': temperature,
                'temperatureInside': temperatureInside,
                'humidity': humidity,
                'humidityInside': humidityInside,
                'pressure': pressure,
                'air Pump Active': airPumpActive,
                'water Pump Active': waterPumpActive,
                'luminosity': luminosity,
                'tds': tds,
                'ph': ph
            }
            ]
    return jsonify(environment[0])

# main
if __name__ == "__main__":
    app.secret_key = os.urandom(24)
    app.run(host='0.0.0.0')
