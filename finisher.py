import threading, time
from flask import Flask, request
app = Flask(__name__)

DOME = 23
BUZZER = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(DOME, GPIO.IN, pull_up_down=GPIO.PUD_UP)  #dome button to GPIO23
GPIO.setup(BUZZER, GPIO.OUT)  # to GPIO24

buzzerLock = threading.Lock()
stateLock = threading.Lock()

STATE = 0
WAIT = 1
STARTED = 3
DONE = 4
RESET = 5
STOP = 6

startTime = 0.0
endTime = 0.0

@app.route('/health', methods=['GET'])
def health():
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

def notifyStart():
    global startTime
    payload = {"start_time": startTime}
    headers = {'content-type': 'application/json'}
    try:
        s = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        resp = s.post("http://starterbuttonpi/start", data=json.dumps(payload), headers=headers)
        if response.status_code != requests.codes.ok:
            print "Error notifying start"
    except:
        print "Error exception occurred notifying start"

def notifyDisplay():
    global startTime
    payload = {"start_time": startTime}
    headers = {'content-type': 'application/json'}
    try:
        s = requests.Session()
        retries = Retry(
            total=5,
            read=5,
            connect=5,
            backoff_factor=0.3,
            status_forcelist=[ 502, 503, 504 ])
        s.mount('http://', HTTPAdapter(max_retries=retries))
        resp = s.post("http://noisemakerpi/start", data=json.dumps(payload), headers=headers)
        if response.status_code != requests.codes.ok:
            print "Error notifying display"
    except:
        print "Error exception occurred notifying display"


def playBuzzer(lock):
    with lock:
        GPIO.output(BUZZER, True)
        time.sleep(3)
        GPIO.output(BUZZER, False)


def waitForStart():
    global STATE
    currState = -1
    while True:
        with stateLock:
            currState = STATE
        if currState == WAIT :
            time.sleep(0.1)
        elif currState == STARTED:
            time.sleep(0.1)
        elif currState == RESET:
            with stateLock:
                STATE = WAIT
        elif currState == STOP:
            # POST time?
            with stateLock:
                STATE = WAIT
        elif currState == DONE :
            t = threading.Thread(target=playBuzzer, args=(buzzerLock,))
            t.daemon = True
            t.start()

            d = threading.Thread(target=notifyDisplay)
            d.daemon = True
            f = threading.Thread(target=notifyStart)
            f.daemon = True
            n.start()
            d.start()
            # PSOT time?
            with stateLock:
                STATE = WAIT
            print "Finished one iteration"
        else:
            print "WARNING unknown state: " + currState

def waitForButtonPress():
    global stateLock, STATE, endTime
    prevState = True
    button_state = True
    buttonPushTime = 0.0
    while True:
        prevState = button_state
        button_state = GPIO.input(DOME)
        if button_state == False and prevState == True:
            # button pressed
            print "STOP button pressed"
            with stateLock:
                STATE = DONE
                endTime = time.time()
        elif button_state == True and prevState == False:
            # button released
            print "STOP button released"

        time.sleep(.2)

if __name__ == '__main__':
    try:
        s = threading.Thread(target=waitForStart)
        s.daemon = True
        s.start()

        b = threading.Thread(target=waitForButtonPress)
        b.daemon = True
        b.start()

        #start flask server
        app.run(port=9080, debug=True)
    except (KeyboardInterrupt, SystemExit):
        print "caught keyboard interrupt"
    finally:
        GPIO.cleanup()
