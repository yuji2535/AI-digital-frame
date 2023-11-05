import base64

import requests

with open("./TEST.png", 'rb') as f:
    img = base64.b64encode(f.read()).decode('utf8')

with open("./TEST.wav", 'rb') as f:
    voice = base64.b64encode(f.read()).decode('utf8')

response = requests.post('URL', headers={'ngrok-skip-browser-warning':
                                             'use it to skip ngrok warning. this value can be anything.'},
                                    json={
                                        'img': img,
                                        'voice': voice # Optional
}).json()

img = response['img']
img_comment = response['img_comment']
bgm = response['bgm']

with open('./TEST_OUTPUT.png', 'wb') as f:
    f.write(base64.b64decode(img))

with open('./TEST_OUTPUT.wav', 'wb') as f:
    f.write(base64.b64decode(bgm))

print(img_comment)