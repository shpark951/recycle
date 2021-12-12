import RPi.GPIO as GPIO
import Keypad       #import module Keypad
import json
from gpiozero import MotionSensor
from signal import pause
from datetime import datetime
from picamera import PiCamera,camera
import requests
import os
import boto3
import time
import sounddevice as sd
import soundfile as sf
import io
from pydub import AudioSegment
from pydub.playback import play
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
import json
#음성인식==========
kakao_speech_url = "https://kakaoi-newtone-openapi.kakao.com/v1/recognize"
rest_api_key = '6385680a2e5a1e52b773855f6be739d8'
headers = {
"Content-Type": "application/octet-stream",
"X-DSS-Service": "DICTATION",
"Authorization": "KakaoAK " + rest_api_key,
}
URL = "https://kakaoi-newtone-openapi.kakao.com/v1/synthesize" 
HEADERS = {
    "Content-Type" : "application/xml",
    "Authorization" : "KakaoAK 6385680a2e5a1e52b773855f6be739d8"
}
#음성인식==========
f=open("pet.jpg", "rb") #3.7kiB in same folder
fileContent = f.read()
byteArr = bytearray(fileContent)

GPIO.setmode(GPIO.BOARD)

GPIO.setup(8, GPIO.OUT)
servo = GPIO.PWM(8,50)  # 플라스틱 서보모터

GPIO.setup(26, GPIO.OUT)
servo2 = GPIO.PWM(26,50)  # 유리병 서보모터
#==카메라설정
camera =PiCamera() 
camera.resolution =(224, 224)
camera.rotation =180
#==카메라설정

MQTT_SERVER = "52.196.223.192"  #Write Server IP Address
MQTT_PATH = "Image" #topic
channel =50
item = "Default"
result = "Default"
plastic_cnt =0
glass_cnt =0
point_sum =0
pir = MotionSensor(12)  #모션센서

def calculate_point(plastic_cnt,glass_cnt):
    global point_sum
    point_sum = plastic_cnt*30 + glass_cnt*60


def on_connect(client, userdata, flags, rc):
    global byteArr
    client.subscribe("Result")

    client.publish(MQTT_PATH, byteArr)
    time.sleep(2)
def on_message(client, userdata, msg):
    global item, result

    payload =json.loads(msg.payload)
    item = payload['type'] # 인식결과 plastic or glass
    result = payload['result']
def move_angle_servo(angle) :
    dc =angle *0.055 +2.5
    print(f'각도 :{angle}')
    servo.ChangeDutyCycle(dc)
def move_angle_servo2(angle) :
    dc =angle *0.055 +2.5
    print(f'각도 :{angle}')
    servo2.ChangeDutyCycle(dc)
def capture():
    DATA = """<speak> 재활용품을 카메라에 스캔해주세요</speak>"""
    res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
    sound = io.BytesIO(res.content)
    song = AudioSegment.from_mp3(sound)
    play(song)
    time.sleep(2)
    now =datetime.now()
    file_name =now.strftime('%Y%m%d_%H%M%S.jpg')
    file_path =os.path.join('./images', file_name)
    camera.capture(file_path, use_video_port=True)
    print('capture.....', file_path)
    return file_name, file_path

def upload_snapshot():
    global byteArr,item,result,servo,SERVO_PIN,plastic_cnt,glass_cnt,channel
    file_name, file_path =capture()

    #MQTT PUBLISH 이미지 전송
    f=open(file_path, "rb") 
    fileContent = f.read()
    byteArr = bytearray(fileContent)
    #MQTT JSON 결과값 수신
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_SERVER, 5555, 60)
    client.loop_start()
    while True:
        if item is not "Default" and result is not "Default":
            if item == 'plastic' and result =='PASS':     
                DATA = """<speak>인식이 완료되었습니다. 플라스틱을 넣어주세요</speak>"""
                res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
                sound = io.BytesIO(res.content)
                song = AudioSegment.from_mp3(sound)
                play(song)
                servo.start(0)
                move_angle_servo(180)#열림
                time.sleep(1)  
                move_angle_servo(80)#정지
                time.sleep(2)
                move_angle_servo(30)#닫힘
                time.sleep(1)
                move_angle_servo(80) #멈춤
                item = "Default"
                result ="Default"
                plastic_cnt = plastic_cnt+1
                print('넣은 플라스틱 갯수 :', plastic_cnt, '개')
                print('넣은 유리병 갯수 :',glass_cnt ,'개')
                break
            elif item == 'glass' and result =='PASS' :
                DATA = """<speak>인식이 완료되었습니다. 유리병을 넣어주세요</speak>"""
                res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
                sound = io.BytesIO(res.content)
                song = AudioSegment.from_mp3(sound)
                play(song)
                print(channel)
                servo2.start(0)
                move_angle_servo2(180)#열림
                time.sleep(1)  
                move_angle_servo2(80)#정지
                time.sleep(2)
                move_angle_servo2(30)#닫힘
                time.sleep(1)
                move_angle_servo2(80) # 멈춤
                item = "Default"
                result ="Default"
                glass_cnt = glass_cnt+1
                print('넣은 플라스틱 갯수 :', plastic_cnt, '개')
                print('넣은 유리병 갯수 :',glass_cnt ,'개')
                break
            elif item == 'plastic' and result =='FAIL':
                DATA = """<speak>인식이 실패하였습니다. 메뉴얼을 확인해주시고 다시 인식시켜주세요!</speak>"""
                res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
                sound = io.BytesIO(res.content)
                song = AudioSegment.from_mp3(sound)
                play(song)
                item = "Default"
                result ="Default"                
                upload_snapshot()
            elif item == 'glass' and result =='FAIL':
                DATA = """<speak>인식이 실패하였습니다. 메뉴얼을 확인해주시고 다시 인식시켜주세요!</speak>"""
                res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
                sound = io.BytesIO(res.content)
                song = AudioSegment.from_mp3(sound)
                play(song)
                item = "Default"
                result ="Default"
                upload_snapshot()
            break    
    DATA = """<speak>분리배출할 재활용품이 더 있으신가요? 있다면 있어요, 없으면 없어요라고 대답해주세요</speak>"""
    res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
    sound = io.BytesIO(res.content)
    song = AudioSegment.from_mp3(sound)
    play(song)
    start_record()


#KEYPAD


ROWS = 4        # number of rows of the Keypad
COLS = 4        #number of columns of the Keypad
keys =  [   '1','2','3','A',    #key code
            '4','5','6','B',
            '7','8','9','C',
            '*','0','#','D'     ]
rowsPins = [12,16,18,22]        #connect to the row pinouts of the keypad
colsPins = [19,15,13,11]        #connect to the column pinouts of the keypad
sinput = ""
bInput = False
c =True
def recoginize(audio):
    res =requests.post(kakao_speech_url, headers=headers, data=audio)
    try:
        result_json_string =res.text[
            res.text.index('{"type":"finalResult"'):res.text.rindex('}')+1
        ]
        result = json.loads(result_json_string)
        value =result['value']
    except:
        value =None
    
    return value

def record(seconds=3, fs=16000, channels=1):
    data =sd.rec(int(seconds *fs), samplerate =fs, channels=1)
    sd.wait()
    audio =io.BytesIO()
    sf.write(audio,data,fs,format="wav")
    audio.seek(0)
    print("record end")
    return audio
    
def start_record():
    global plastic_cnt,glass_cnt  #카운트된 갯수
    global sinput
    print("record start")
    audio =record()
    value =recoginize(audio)
    print('[인식결과]',value)
    if value == '예' or value =='네' or value =='맞습니다':
        DATA = f"""<speak>적립이 성공적으로 완료되었습니다! 참여해주셔서 감사합니다</speak>"""
        res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
        sound = io.BytesIO(res.content)
        song = AudioSegment.from_mp3(sound)
        play(song)


        # REST API 전송 시작
        rest_url ="http://44.193.234.185:8000/user/first"
        rest_datas={
            "phone_number" : str(sinput),
            "point" : plastic_cnt*30 + glass_cnt*70
        }
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json'
        }
        response =requests.post(rest_url,headers=headers, json=rest_datas)
        print(response.text) #REST API 전송 결과

        # SNS 전송 시작
        datas ={
	        "phone_number" : str(sinput),
	        "point" : plastic_cnt*30 + glass_cnt*70,
            "sum_points":response.text.split(':')[-1]
        }
        print(sinput)
        url ="https://scxzrpxtp4.execute-api.us-east-1.amazonaws.com/v1/message"

        response =requests.post(url,headers=headers, json=datas)
        print(response)
        print('대기중')
        time.sleep(5)
    elif value == '아니오' or value =='아니요' or value== '아닙니다':
        
        sinput = ""
        loop()
    elif value == '있습니다' or value =='있어요':
        time.sleep(1) #대사 시간
        upload_snapshot()
    elif value ==None:
        DATA = """<speak>분리배출할 재활용품이 더 있으신가요? 있다면,, 있어요라고 대답해주세요</speak>"""
        res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
        sound = io.BytesIO(res.content)
        song = AudioSegment.from_mp3(sound)
        play(song)
        start_record()
    elif value =='없어요' or value =='없습니다':
        loop()


def loop():
    DATA = f"""<speak>입력 버튼을 누르고 , 번호를 입력해주세요</speak>"""
    res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
    sound = io.BytesIO(res.content)
    song = AudioSegment.from_mp3(sound)
    play(song)
    keypad = Keypad.Keypad(keys,rowsPins,colsPins,ROWS,COLS)    #create Keypad object
    keypad.setDebounceTime(50)      #set the debounce time
    while(True):
        global bInput,sinput
        key = keypad.getKey()       #obtain the state of keys
        if(key == '*' and bInput ==False):     #if there is key pressed, print its key code.
            
            bInput =True
            print ("번호입력중... 입력후 #을 눌러주세요")
        elif key =='#':
             bInput =False
             DATA = f"""<speak>입력하신 번호가, <say-as interpret-as="digits"> {sinput} </say-as>,,, 맞나요?</speak>"""
             res = requests.post(URL, headers = HEADERS, data = DATA.encode('utf-8'))        
             sound = io.BytesIO(res.content)
             song = AudioSegment.from_mp3(sound)
             play(song)
             start_record()
             break
        elif bInput ==True and ('0' <= key <= '9'):
             sinput = sinput + key

pir.when_motion = upload_snapshot
pause()