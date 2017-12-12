import threading, time, spidev, json
import RPi.GPIO as GPIO
from flask import Flask, request, Response
import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

app = Flask(__name__)

LED = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED, GPIO.OUT)  #TURN on LED strip to GPIO24

stateLock = threading.Lock()

STATE = 0
WAIT = 1
STARTED = 3
DONE = 4
RESET = 5
STOP = 6

startTime = 0.0
endTime = 0.0

spi = spidev.SpiDev()
spi.open(0, 1) # Port 0 , Chip Select 1

@app.route('/health', methods=['GET'])
def heath():
    print "HEALTHCHECK received"
    return Response(status=200)

@app.route('/start', methods=['POST'])
def start():
    global STATE, stateLock
    print "START signal received"
    try:
        data = json.loads(request.data)
        with stateLock:
            startTime = data['start_time']
            STATE = STARTED
    except:
        startTime = time.time()
        STATE = STARTED
        print "error getting start time"
    return Response(status=200)

@app.route('/stop', methods=['POST'])
def stop():
    global STATE, stateLock
    print "STOP signal received"
    try:
        data = json.loads(request.data)
        with stateLock:
            endTime = data['stop_time']
            STATE = STOP
    except:
        endTime = time.time()
        STATE = STOP
        print "error getting start time"
    return Response(status=200)

@app.route('/reset', methods=['POST'])
def reset():
    global STATE, stateLock
    print "RESET signal received"
    with stateLock:
        STATE = RESET
    return Response(status=200)

def enableDisplay():
    GPIO.output(LED, True)
    return

def disableDisplay():
    #turn off display
    GPIO.output(LED, False)    # channel = 1
    # spi.open(0,channel) # Port 0 , Chip Select 1
    # spiValue = spi.xfer2([1,OutValue])
    # time.sleep(2)
    # spi.close()
    # return spiValue

def convertToByte(digit):
    tens = digit / 10
    ones = digit % 10
    return hex((tens << 4) | ones)

def display(start, end):
    display = end - start
    mins = int(display / 60)
    seconds = int(display % 60)
    milli = int((display % 1)*100)

    minByte = convertToByte(mins)
    secByte = convertToByte(seconds)
    milliByte = convertToByte(milli)

    print ("Mins:{0} Secs:{1} Milli:{2}".format(mins, seconds, milli))

    spiValue = spi.xfer2([minByte, secByte, milliByte])

def finished(start, stop):
    i = 0
    while i < 3:
        disableDisplay()
        time.sleep(1)
        enableDisplay()
        time.sleep(2)
        i+=1

def waitForStart():
    global STATE
    currState = -1
    while True:
        with stateLock:
            currState = STATE
        if currState == WAIT:
            enableDisplay()
            display(0, 0)
            time.sleep(0.1)
        elif currState == STARTED:
            display(startTime, time.time())
            time.sleep(0.1)
        elif currState == RESET:
            with stateLock:
                STATE = WAIT
        elif currState == STOP:
            # POST time?
            with stateLock:
                STATE = WAIT
        elif currState == DONE :
            finished(startTime, endTime)
            # POST time?
            time.sleep(20)
            with stateLock:
                STATE = WAIT
            print "Finished one iteration"
        else:
            print "WARNING unknown state: " + str(currState)

if __name__ == '__main__':
    STATE = WAIT
    try:

        s = threading.Thread(target=waitForStart)
        s.daemon = True
        s.start()

        #start flask server
        app.run(port=9080, debug=True)
    except (KeyboardInterrupt, SystemExit):
        print "caught keyboard interrupt"
    finally:
        GPIO.cleanup()
        spi.close()
