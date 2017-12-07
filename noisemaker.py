import threading, time, spidev
import RPi.GPIO as GPIO
import json

from flask import Flask, request, Response

app = Flask(__name__)

GPIO.setmode(GPIO.BCM)
GPIO.setup(24, GPIO.OUT)  #TURN on LED strip to GPIO24

startLock = threading.Lock()
endLock = threading.Lock()

stopSignal = False
startSignal = False
startTime = 0.0
endTime = 0.0

spi = spidev.SpiDev()

@app.route('/start', methods=['POST'])
def start():
    global startTime
    global startSignal
    print "START signal received . . . "
    try:
        data = json.loads(request.data)
        with startLock:
            startTime = data['start_time']
            startSignal = True
    except:
        startTime = time.time()
        startSignal = True
        print "error getting start time"
    return Response(status=200)

@app.route('/stop', methods=['POST'])
def stop():
    global endTime
    global stopSignal
    print "STOP signal received . . ."
    try:
        data = json.loads(request.data)
        with endLock:
            endTime = data['stop_time']
            stopSignal = True
    except:
        endTime = time.time()
        stopSignal = True
        print "error getting stop time"
    return Response(status=200)

def disable():
    #turn off display
    print "disable() not configured"
    # channel = 1
    # spi.open(0,channel) # Port 0 , Chip Select 1
    # spiValue = spi.xfer2([1,OutValue])
    # time.sleep(2)
    # spi.close()
    # return spiValue


def display(start, end):
    display = end - start
    mins = int(display / 60)
    seconds = int(display % 60)
    milli = int((display % 1)*100)
    print ("Mins:{0} Secs:{1} Milli:{2}".format(mins, seconds, milli))

#def postTime(start, stop):

def reset():
    global startTime, endTime
    global startSignal, stopSignal
    startSignal = False
    stopSignal = False

def finished(start, stop):
    i = 0
    while i < 3:
        display(start, stop)
        time.sleep(2)
        disable()
        time.sleep(1)
        i+=1

def start():
    while not startSignal:
        time.sleep(2)

    while not stopSignal:
        time.sleep(.01)
        display(startTime, time.time())

    finished(startTime, endTime)
    reset()

def runDisplay():
    while True:
        start()
        print "FINISHED"

    
if __name__ == '__main__':
    t = threading.Thread(target=runDisplay)
    try:
        #start LED display monitoring
        t.daemon = True
        t.start()
        
        #start flask server
        app.run(port=9080, debug=True)
    except (KeyboardInterrupt, SystemExit):
        print "caught keyboard interrupt"
    finally:
        GPIO.cleanup()        
