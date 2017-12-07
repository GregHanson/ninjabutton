import threading, time, json
import RPi.GPIO as GPIO
from flask import Flask, request, Response
import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

app = Flask(__name__)

DOME = 23
BUZZER = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(DOME, GPIO.IN, pull_up_down=GPIO.PUD_UP)  #dome button to GPIO23
GPIO.setup(BUZZER, GPIO.OUT)  # to GPIO24

buzzerLock = threading.Lock()
startLock = threading.Lock()
endLock = threading.Lock()

stopSignal = False
startSignal = False
startButtonPressed = False
startTime = 0.0
endTime = 0.0

@app.route('/health', methods=['GET'])
def health():
    dStatus = 404
    fStatus = 404
    try:
        d = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        d.mount('http://', HTTPAdapter(max_retries=retries))
        dResp = d.get("http://noisemakerpi/health")
        dStatus = dResp.status_code
    except:
        print "Error connecting to noisemakerpi"

    try:
        f = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        f.mount('http://', HTTPAdapter(max_retries=retries))
        fResp = f.get("http://finisherbuttonpi/health")
        fStatus = fResp.status_code
    except:
        print "Error connecting to finisherbuttonpi"

    if fResp.status_code == requests.codes.ok and dResp.status_code == requests.codes.ok:
        return Response(status=200)

    data = {
        "finish_status": fStatus,
        "display_status": dStatus,
    }
    js = json.dumps(data)
    return Response(js, status=200, mimetype='application/json')

@app.route('/stop', methods=['POST'])
def stop():
    global endTime, stopSignal
    print "STOP signal received"
    try:
        data = json.loads(request.data)
        with endLock:
            endTime = data['stop_time']
            doneSignal = True
    except:
        endTime = time.time()
        doneSignal = True
        print "error getting stop time"
    return Response(status=200)

def playBuzzer(lock):
    with lock:
        i = 0
        while i < 3:
            #turn buzzer on
            GPIO.output(24, True)
            time.sleep(1)
            #turn off buzzer
            GPIO.output(24, False)
            time.sleep(1)

        GPIO.output(24, True)
        time.sleep(3)
        GPIO.output(24, False)

def notifyStop()
    global startTime
    try:
        s = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        resp = s.get("http://stopbuttonpi/start")
        if response.status_code != requests.codes.ok:
            print "Error notifying stop"
    except:
        print "Error exception occurred notifying display"


def notifyDisplay():
    global startTime
    try:
        s = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        resp = s.get("http://noisemakerpi/start")
        if response.status_code != requests.codes.ok:
            print "Error notifying display"
    except:
        print "Error exception occurred notifying display" 


def reset():
    global startTime, endTime
    global startSignal, stopSignal
    startSignal = False
    doneSignal = False
    startButtonPressed = False


def start():
    global startButtonPressed, buzzerLock, startTime
    
    while not startButtonPressed:
        time.sleep(0.1)

    d = threading.Thread(target=notifyDisplay)
    d.daemon = True
    f = threading.Thread(target=notifyStop)
    f.daemon = True

    playBuzzer(buzzerLock)
    startTime = time.time()
    n.start()
    d.start()

    while not doneSignal:
        time.sleep(.01)

    while not stopSignal:
        time.sleep(.01)

    reset()

def waitForStart():
    while True:
        start()
        print "Finished one iteration"

def waitForStartButton():
    global startButtonPressed
    while True:
         button_state = GPIO.input(DOME)
         if button_state == False:
            with endLock:
                startButtonPressed = True
                stopSignal = True
            print('Button Pressed...')
            time.sleep(2)

if __name__ == '__main__':
    try:
        s = threading.Thread(target=waitForStart)
        s.daemon = True
        s.start()

        b = threading.Thread(target=waitForStartButton)
        b.daemon = True
        b.start()

        #start flask server
        app.run(port=9080, debug=True)
    except (KeyboardInterrupt, SystemExit):
        print "caught keyboard interrupt"
    finally:
        GPIO.cleanup()

