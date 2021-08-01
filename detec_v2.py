import pickle               # store data in compressed format
import face_recognition     # 1. face location function and 2. face encoding function(128 d-vector)
import cv2                  # computer vision library for reading frames and converting to 2d-array
import numpy as np          # library for computation on array
import time                 # library for using system time and some of it's calculation
import requests             # for making HTTP requests
import json                 # python library for dealing with json structure
import RPi.GPIO as GPIO     # for controlling raspberry pins
from conf import *          # importing data from configuration file
import smtplib              # for mailing service (smtp port 465)
import imghdr               # for send image as attachment in mail
from email.message import EmailMessage 
from Adafruit_IO import Client, Feed, RequestError  # adafruit library

n = 1
n = 0
inp_key = ""
aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
try:  # if we have a 'digital' feed
    digital = aio.feeds('smart-door-io')
except RequestError:  # create a new digital feed
    feed = Feed(name="smart-door-io2")
    digital = aio.create_feed(feed)

# configuring raspi board pins
m = 'z'
GPIO.setmode(GPIO.BOARD)
GPIO.setup(16, GPIO.IN)  # input touch sensor
GPIO.setup(3, GPIO.OUT, initial=GPIO.HIGH)  # relay
GPIO.setup(5, GPIO.OUT, initial=GPIO.HIGH)  # buzzer
GPIO.setup(7, GPIO.OUT)  # start


print("LOADING.....................................................")

# telegram


def send_telegram_message(message):
    """Sends message via Telegram"""
    url = "https://api.telegram.org/" + telegram_bot_id + "/sendMessage"
    data = {
        "chat_id": telegram_chat_id,
        "text": message
    }
    try:
        response = requests.request("POST", url, params=data)
        print("This is the Telegram URL")
        print(url)
        print("This is the Telegram response")
        print(response.text)
        telegram_data = json.loads(response.text)
        return telegram_data["ok"]
    except Exception as e:
        print("An error occurred in sending the alert message via Telegram")
        print(e)
        return False
    finally:
        return 'done'


def detect():
    for x in range(0, 3):  # startup leds
        GPIO.output(7, True)
        time.sleep(1)
        GPIO.output(7, False)
        time.sleep(0.80)
    path_to_encoding = "encodings.pickle"
    start = time.time()
    print(time.time()-start)
    print("[INFO] loading encodings...")
    data = pickle.loads(open(path_to_encoding, "rb").read())
    print(time.time()-start)
    known_face_encodings = data["encodings"]
    known_face_names = data["names"]
    # Initialize some variables
    face_locations = []
    # face_encodings = []
    face_names = []
    process_this_frame = True

    # checking input coming from sensor/adafruit simultaneously in this loop
    while True:
        time.sleep(0.5)
        data = aio.receive(digital.key)
        inp_key = GPIO.input(16)  # defined i/p from touch sensor

        if int(data.value) == 1:  # data value receiving from adfruit - io to open
            print('received <- ON\n')
            GPIO.output(3, False)

        elif int(data.value) == 0:  # data value received from adafruit to close
            print(f'received <- OFF  {time.time()}\n')
            GPIO.output(3, True)

        if inp_key:  # taking input data from sensor to procress next step
            print("data")
            # video_capture = cv2.videocapture(0) camera setup
            video_capture = cv2.VideoCapture(0)
            ret, frame = video_capture.read()
            cv2.imwrite("image.jpg", frame)  # saving a frame from video
            video_capture.release()
            if ret:
                frame = cv2.flip(frame, 1)
                # Resize frame
                #  of video to 1/4 size for faster face recognition processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

                # Convert the image from BGR color (which OpenCV uses) to RGB color(which face_recognition uses)
                rgb_small_frame = small_frame[:, :, ::-1]

                # Find all the faces and face encodings in the current frame of video
                face_locations = face_recognition.face_locations(
                    rgb_small_frame, number_of_times_to_upsample=2)
                print(face_locations)
                print(type(face_locations))
                face_encodings = face_recognition.face_encodings(
                    rgb_small_frame, face_locations, num_jitters=2)
                face_names = []
                for face_encoding in face_encodings:

                    # See if the face is a match for the known face(s)
                    matches = face_recognition.compare_faces(
                        known_face_encodings, face_encoding, tolerance=0.5)
                    print(matches)
                    name = "Unknown"

                    # Use the known face with the smallest distaance to the new face
                    face_distances = face_recognition.face_distance(
                        known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    if matches[best_match_index]:
                        name = known_face_names[best_match_index]

                    face_names.append(name)

                print(face_names)

                # Display the results
                # checking both conditions
                for (top, right, bottom, left), name in zip(face_locations, face_names):
                    # Scale back up face locations since the frame we detected in w  as scaled to 1/4 size
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4

                    if(name == "Unknown"):    # for unknown faces
                       # Draw a box around the face
                        cv2.rectangle(frame, (left, top),
                                      (right, bottom), (0, 0, 255), 2)
                       # Draw a label with a name below the face
                        cv2.rectangle(frame, (left, bottom - 35),
                                      (right, bottom), (0, 0, 255), cv2.FILLED)
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(frame, name, (left + 6, bottom - 6),
                                    font, 1.0, (255, 255, 255), 1)
                        cv2.imshow('Video', frame)
                        GPIO.output(5, False)  # buzzer open/red led
                        time.sleep(2)  # for 2sec
                        GPIO.output(5, True)  # buzzer close /red led
                        # alert with telegram bot
                        send = m
                        send1 = (
                            send + "=>'  someone is trying to open door,please check! \n https://door-smart-io.web.app/ ,\n image.jpg")
                        print(send1)
                        message = (send1)
                        telegram_status = send_telegram_message(message)
                        print("This is the Telegram status:", telegram_status)
                        # sending mail to gmail + unknown person photo
                        Sender_Email = "@gmail.com"
                        Reciever_Email = "atulkumarzna1998@gmail.com"
                        Password = 'psswrd'
                        newMessage = EmailMessage()
                        newMessage['Subject'] = "Unauthorised Attempt"
                        newMessage['From'] = Sender_Email
                        newMessage['To'] = Reciever_Email
                        newMessage.set_content(
                            "'Someone is trying to open door please ,check!!!' \n 'Use this link to open door ----'  \n 'click here- https://door-smart-io.web.app/ '")
                        with open('image.jpg', 'rb') as f:
                            image_data = f.read()
                            image_type = imghdr.what(f.name)
                            image_name = f.name
                        newMessage.add_attachment(image_data, maintype='image',
                                                  subtype=image_type, filename=image_name)
                        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:

                            smtp.login(Sender_Email, Password)
                            smtp.send_message(newMessage)

                    else:         # for known_faces
                       # Draw a box around the face
                        cv2.rectangle(frame, (left, top),
                                      (right, bottom), (0, 255, 0), 2)
                       # Draw a label with a name below the face
                        cv2.rectangle(frame, (left, bottom - 35),
                                      (right, bottom), (0, 255, 0), cv2.FILLED)
                        font = cv2.FONT_HERSHEY_DUPLEX
                        cv2.putText(frame, name, (left + 6, bottom - 6),
                                    font, 1.0, (255, 255, 255), 1)
                        cv2.imshow('Video', frame)
                        # lock open # making gpio pins high
                        GPIO.output(3, False)
                        time.sleep(5)
                        GPIO.output(3, True)  # lock closed


detect()
GPIO.cleanup()  # to reset pins
