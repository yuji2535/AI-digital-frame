import base64
import io
import json
import os
from typing import Union

from PIL import Image

import openai
import requests
import whisper
from audiocraft.data.audio import audio_write
from audiocraft.models import MusicGen
import logging
logging.basicConfig(level=logging.INFO)

CONFIG_FILE = './config.json'

with open(CONFIG_FILE, 'r') as f:
    config: dict = json.loads(f.read())

music_model = MusicGen.get_pretrained(config['music_model'])
music_model.set_generation_params(duration=config['BGM_duration'])
whisper_model = whisper.load_model(config['whisper_model'])

openai.api_key = config['openai']['api_key'] if config['openai']['api_key'] is None else os.getenv("OPENAI_API_KEY")

async def music_gen_pipline(prompt: str):
    """
    Generate music by prompt.
    :param prompt: the prompt generated by GPT4.
    :return: the BGM generated by musicgen. the music will be warped by raw base64 text
    """
    logging.info('Music generation start')
    wav = music_model.generate([prompt])
    audio_write('./BGM_OUTPUT', wav.cpu()[0], music_model.sample_rate, strategy="loudness", loudness_compressor=True)
    with open('./BGM_OUTPUT.wav', 'rb') as f:
        tmp = f.read()
    logging.info('Music generated done.')

    return base64.b64encode(tmp).decode('utf8')

def GPT4_pipline(img: str, voice_prompt: str=None):
    """
    Use GPT4 to generate img & music prompt or image's comment and description.
    :param img: base64 raw text. let GPT4 to generate.
    :param voice_prompt: if this is None, GPT4 will generate image's comment and description, else it will generate prompts.
    :return: prompts or image's comment and description.
    """
    # TODO: 我去翻了openai的doc，我沒看到gpt4 with vision的api,所以我需要有人幫我找找這vision版具體怎麼用
    # 他好像是要先花錢排隊，等openai寄信給你你才能用的樣子
    openai_config = config['openai']

    if voice_prompt is not None: # use image and voice to generate prompt
        response_message = None
        for i in range(2):
            if response_message is None:
                response = openai.ChatCompletion.create(
                    model=openai_config['model'],
                    messages=[{"role": "user", "content": openai_config['img_and_voice_to_prompt'] + voice_prompt}],
                    functions=openai_config['functions_prompt']
                )
                response_message = response["choices"][0]["message"]

            if response_message.get("function_call"):
                try:
                    return json.loads(response_message["function_call"]["arguments"])
                except json.decoder.JSONDecodeError:
                    response = openai.ChatCompletion.create(
                        model=openai_config['model'],
                        messages=[{"role": "user", "content": openai_config['json_fix_prompt'] + response_message["function_call"]["arguments"]}]
                    )
                    response_message = response["choices"][0]["message"]
                    try:
                        return json.loads(response_message["function_call"]["arguments"])
                    except json.decoder.JSONDecodeError:
                        continue

        raise RuntimeError(f"GPT4 didn't generate legal prompt. prompt: {response_message['function_call']}")
    else: # give img comment
        return openai.ChatCompletion.create(
            model=openai_config['model'],
            messages=[{"role": "user", "content": openai_config['img_to_comment']}],
        )["choices"][0]["message"]['content']

async def stable_diffusion_pipline(prompt: str, img: str):
    """
    Generate img by sd.
    :param prompt: sd prompt.
    :param img: base img which warp by raw base64 text
    :return: generated img warp by raw base64 text
    """
    logging.info('Image generation start')
    url = "http://127.0.0.1:7860"
    sd_payload = config['sd_payload']
    sd_payload['prompt'] = sd_payload['prompt'] + prompt
    sd_payload['init_images'].append(img)

    response = requests.post(url=f'{url}/sdapi/v1/img2img', json=sd_payload)

    r = response.json()
    logging.info('Image generated done.')
    Image.open(io.BytesIO(base64.b64decode(r['images'][0]))).save('./IMAGE_OUTPUT.png')

    return r['images'][0]

def save_config(key: Union[str, dict], value=None):
    """
    save config and reload model if necessary
    :param key: `dict` or `str`. `dict` will update config by `dict`, `str` will update config by key-value pair
    :param value: only work if `key` is `str`
    """
    global music_model, whisper_model
    if isinstance(key, str):
        if isinstance(value, dict) and isinstance(config[key], dict):
            config[key].update(value)
        else:
            config[key] = value
    else:
        for k, v in key.items():
            if isinstance(v , dict):
                config[k].update(v)
            else:
                config[k] = v

    with open(CONFIG_FILE, 'w') as f:
        f.write(json.dumps(config, indent=2))

    if key == 'music_model':
        music_model = MusicGen.get_pretrained(config[key])

    if key == 'BGM_duration':
        music_model.set_generation_params(duration=config[key])

    if key == 'whisper_model':
        whisper_model = whisper.load_model(config[key])

    if key == 'openai':
        openai.api_key = config['openai']['api_key']