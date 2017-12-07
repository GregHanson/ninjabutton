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
stopButtonPressed = False
startTime = 0.0
endTime = 0.0

@app.route('/health', methods=['GET'])
def health():
    return Response(status=200)

@app.route('/start', methods=['POST'])
def start():
    global startTime, startSignal
    print "START signal received . . ."
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
    global endTime, stopSignal
    print "STOP signal received"
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


def playBuzzer(lock):
    with lock:
        #turn buzzer on
        GPIO.output(24, True)
        time.sleep(3)
        #turn off buzzer
        GPIO.output(24, False)

def notifyDisplay():
    s = requests.Session()
    retries = Retry(
        total=5, 
        read=5,
        connect=5,
        backoff_factor=0.3, 
        status_forcelist=[ 502, 503, 504 ])
    s.mount('http://', HTTPAdapter(max_retries=retries))
    s.get("http://noisemakerpi/done")

def reset():
    global startTime, endTime
    global startSignal, stopSignal
    startSignal = False
    stopSignal = False
    stopButtonPressed = False
    

def start():
    global buzzerLock
    while not startSignal:
        time.sleep(.01)

    while not stopSignal:
        time.sleep(.01)

    if stopButtonPressed:
        t = threading.Thread(target=playBuzzer, args=(buzzerLock,))
        t.daemon = True
        t.start()

    notifyDisaply()


    reset()

def waitForStart():
    while True:
        start()
        print "Finished one iteration"

def waitForFinishButton():
    global stopButtonPressed, buzzerLock
    while True:
         button_state = GPIO.input(DOME)
         if button_state == False:
            with endLock:
                stopButtonPressed = True
                stopSignal = True
            print('Button Pressed...')
            playBuzzer(buzzerLock)
            time.sleep(2)

if __name__ == '__main__':
    try:
        s = threading.Thread(target=waitForStart)
        s.daemon = True
        s.start()

        b = threading.Thread(target=waitForFinishButton)
        b.daemon = True
        b.start()
        
        #start flask server
        app.run(port=9080, debug=True)
    except (KeyboardInterrupt, SystemExit):
        print "caught keyboard interrupt"
    finally:
        GPIO.cleanup()
