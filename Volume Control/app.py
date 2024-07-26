from flask import Flask, render_template, Response, request
import cv2
import mediapipe as mp
from math import hypot
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import numpy as np

app = Flask(__name__)

global cap
cap = None

mpHands = mp.solutions.hands
hands = mpHands.Hands()
mpDraw = mp.solutions.drawing_utils

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))

volMin, volMax = volume.GetVolumeRange()[:2]

stop_stream_flag = False

def generate_frames():
    global stop_stream_flag, cap
    if cap is None:
        cap = cv2.VideoCapture(0)
    while True:
        if stop_stream_flag:
            break

        success, img = cap.read()
        if not success:
            break
        else:
            imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(imgRGB)

            lmList = []
            if results.multi_hand_landmarks:
                for handlandmark in results.multi_hand_landmarks:
                    for id, lm in enumerate(handlandmark.landmark):
                        h, w, _ = img.shape
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        lmList.append([id, cx, cy])
                    mpDraw.draw_landmarks(img, handlandmark, mpHands.HAND_CONNECTIONS)

            if lmList:
                x1, y1 = lmList[4][1], lmList[4][2]
                x2, y2 = lmList[8][1], lmList[8][2]

                cv2.circle(img, (x1, y1), 4, (255, 0, 0), cv2.FILLED)
                cv2.circle(img, (x2, y2), 4, (255, 0, 0), cv2.FILLED)
                cv2.line(img, (x1, y1), (x2, y2), (255, 0, 0), 3)

                length = hypot(x2 - x1, y2 - y1)

                vol = np.interp(length, [15, 220], [volMin, volMax])
                volume.SetMasterVolumeLevel(vol, None)

            ret, buffer = cv2.imencode('.jpg', img)
            img = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')

    if cap is not None:
        cap.release()
        cap = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    global stop_stream_flag
    stop_stream_flag = False
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    global stop_stream_flag
    stop_stream_flag = True
    if stop_stream_flag is True:
        cap.release()
        stop_stream_flag=~(stop_stream_flag)
    return '', 204

if __name__ == '__main__':
    app.run(debug=True)
