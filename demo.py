from __future__ import annotations
from typing import Iterable
import gradio as gr
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes
import time


import os
from typing import List
import gradio as gr
from datetime import datetime
from PIL import Image, ImageEnhance, PngImagePlugin
from library.inference_util import WebUIApi, ControlNetUnit, QueuedTaskResult
from time import sleep, time
from gemini_handler import GeminiAPI
import pandas as pd
import numpy as np
from copy import deepcopy
from text_landering import create_image_with_text
import json 




gemini_generation_config = {
  "temperature": 0.1,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 512,
}

instance = [
            WebUIApi(baseurl="http://127.0.0.1:7777/sdapi/v1"),
            WebUIApi(baseurl="https://cbb40582386de38541.gradio.live/sdapi/v1"),
        ]
instance_num = 2

# 번역기 설정
geminiapi = GeminiAPI(generation_config = gemini_generation_config)

#set model
options = {}

CATEGORY_DICT={
    '디즈니' : 'disney',
    '웹툰/웹소설' : 'webtoon, webnovel',
    '게임' : 'game'
}

# style별로 dict를 다르게 설정할지 미정
STYLE_DICT={
    'RPG/FPS':'rpg',
    '캐주얼' :'casual',
    '레트로':'retro',
    '로맨스': 'romance',
    '판타지': 'fantasy',
    '일상': 'daily',
    '공주': 'princess',
    '가족': 'family',
    '픽사': 'pixar'
}

# prompt_generator = PersonVerbSplitter(spacy_model_name="en_core_web_md")

#set prompt
def set_prompt(keyword_box, prompt_0, prompt_1, synopsis_check, file_path) -> str:        
    if keyword_box == '':
        translated_prompt = ''
    elif synopsis_check:
        translated_prompt = geminiapi.synopsis_to_tags(keyword_box)
    else:
        translated_prompt = geminiapi.ko_en(keyword_box) 
        # remove Input: from translated prompt
        if 'Input:' in translated_prompt:
            translated_prompt = translated_prompt.replace('Input:','')
        elif 'Output:' in translated_prompt:
            translated_prompt = translated_prompt.replace('Output:','')

    print('translated prompt : ', translated_prompt )

    prompt_0 = prompt_0.replace("iom", translated_prompt)
    prompt_1 = prompt_1.replace("iom", translated_prompt)

    while ",," in prompt_0:
        prompt_0 = prompt_0.replace(",,", ",")
    while ",," in prompt_1:
        prompt_1 = prompt_1.replace(",,", ",")    
    
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write('translated prompt : '+ translated_prompt+'\n')
        file.write('final prompt_0 : '+prompt_0+'\n')
        file.write('final prompt_1 : '+prompt_1+'\n')
    
    return prompt_0, prompt_1


def generate(state:gr.State, keyword_box, category, style, text_box, synopsis_check, seed=False): 
    
    # 사용자 입력 로그 저장 일자별 폴더 생성
    folder_name = datetime.now().strftime("%Y-%m-%d")
    folder_name = os.path.join("./user_input_log", folder_name)
    os.makedirs(folder_name, exist_ok=True)
    
    # 현재 시간을 YYYY-MM-DD_HH-MM-SS 형식으로 파일 이름으로 사용
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"{current_time}.txt"
    # 파일 경로 생성
    txt_file_path = os.path.join(folder_name, file_name)
    user_input=f'{keyword_box},{category},{style},{text_box}'
    
    with open(txt_file_path, 'w', encoding='utf-8') as file:
        file.write("user input : "+ user_input+'\n')
    
    #set model 
    category_input = CATEGORY_DICT[category]
    style_input = STYLE_DICT[style]

    # style에 따라 다른 json 파일 import 
    with open(f'./setting/{style_input}_0.json','r') as f:
        style_setting_0 = json.load(f)
    with open(f'./setting/{style_input}_1.json','r') as f:
        style_setting_1 = json.load(f)

    # style별 font 이미지 랜더링
    file_name = f"{current_time}_{0}.png"
    file_path = os.path.join(folder_name, file_name)
    text_img_0 = create_image_with_text(text_box, style_setting_0['font'], style_setting_0['max_font_size'], (512,512), file_path) 
    file_name = f"{current_time}_{1}.png"
    file_path = os.path.join(folder_name, file_name)
    text_img_1 = create_image_with_text(text_box, style_setting_1['font'], style_setting_1['max_font_size'],(512,512), file_path) 
    
    seed_0 = style_setting_0['seed'] if not seed else int(time())
    seed_1 = style_setting_1['seed'] if not seed else int(time())

    #set prompt
    prompt_0, prompt_1 = set_prompt(keyword_box, style_setting_0["prompt"], style_setting_1["prompt"], synopsis_check, txt_file_path)


    controlnet_0 = ControlNetUnit(
                    input_image= text_img_0,
                    module=style_setting_0['controlnet']['module'],
                    model=style_setting_0['controlnet']['model'], 
                    weight = style_setting_0['controlnet']['weight'],
                    resize_mode=style_setting_0['controlnet']['resize_mode'],
                    pixel_perfect=style_setting_0['controlnet']['pixel_perfect'],
                    threshold_a=style_setting_0['controlnet']['threshold_a'],
                    threshold_b=style_setting_0['controlnet']['threshold_b'],
                    guidance_start=style_setting_0['controlnet']['guidance_start'],
                    guidance_end=style_setting_0['controlnet']['guidance_end'],
                    )
    controlnet_1 = ControlNetUnit(
                    input_image= text_img_1,
                    module=style_setting_1['controlnet']['module'],
                    model=style_setting_1['controlnet']['model'], 
                    weight = style_setting_1['controlnet']['weight'],
                    resize_mode=style_setting_1['controlnet']['resize_mode'],
                    pixel_perfect=style_setting_1['controlnet']['pixel_perfect'],
                    threshold_a=style_setting_1['controlnet']['threshold_a'],
                    threshold_b=style_setting_1['controlnet']['threshold_b'],
                    guidance_start=style_setting_1['controlnet']['guidance_start'],
                    guidance_end=style_setting_1['controlnet']['guidance_end'],
                    )



    #generate image
    result = []
    ogprompt = deepcopy(prompt_0)

    # for i in range(instance_num):
    #    options["sd_model_checkpoint"] = style_setting_0['checkpoint']
    #    instance[i].set_options(options)

    checkpoint=[
        style_setting_0['checkpoint'],
        style_setting_1['checkpoint']
    ]

    for i in range(instance_num):
        options["sd_model_checkpoint"] = checkpoint[i]
        instance[i].set_options(options)


    images = []
    
    images.append(
        instance[0].txt2img_task(
            prompt=prompt_0,
            negative_prompt= style_setting_0['negative_prompt'],
            sampler_name=style_setting_0['sampler_name'],
            steps=style_setting_0['steps'],
            override_settings={"CLIP_stop_at_last_layers":2},
            width=style_setting_0['width'],
            height=style_setting_0['height'],
            batch_size=style_setting_0['batch_size'],
            seed=seed_0,
            cfg_scale=style_setting_0['cfg_scale'],
            controlnet_units=[controlnet_0]
            ),
        )
    
   # image get
    # for i in range(instance_num):
    #    while True:
    #        try:
    #            image_ = images[i].get_images()[1:5]
    #            print('image_',image_)
    #        except Exception as e:
    #            # print(e)
    #            sleep(2)
    #            continue
    #        break
    #    result.extend(image_)

    # images = []
    # for i in range(instance_num):
    #    options["sd_model_checkpoint"] = style_setting_1['checkpoint']
    #    instance[i].set_options(options)
    
    images.append(
        instance[1].txt2img_task(
            prompt=prompt_1,
            negative_prompt= style_setting_1['negative_prompt'],
            sampler_name=style_setting_1['sampler_name'],
            steps=style_setting_1['steps'],
            override_settings={"CLIP_stop_at_last_layers":2},
            width=style_setting_1['width'],
            height=style_setting_1['height'],
            batch_size=style_setting_1['batch_size'],
            seed=seed_1,
            cfg_scale=style_setting_1['cfg_scale'],
            controlnet_units=[controlnet_1]
            ),
        )
    
    # image get
    for i in range(instance_num):
        while True:
            try:
                image_ = images[i].get_images()[1:5]
                print('image_',image_)
            except Exception as e:
                # print(e)
                sleep(2)
                continue
            break
        result.extend(image_)
    
    # 결과 이미지 저장
    for i in range(len(result)):   
        pnginfo = PngImagePlugin.PngInfo()
        # 원본 메타데이터를 새 PngInfo 객체에 추가
        for key, value in result[i].info.items():
        # 메타데이터의 key가 'parameters'인 경우, 해당 값을 그대로 추가
            pnginfo.add_text(key, value)
            
        file_name = f"{current_time}_output_{i}.png"
        file_path = os.path.join(folder_name, file_name)
        result[i].save(file_path)
        # image_[i].save(file_path,"PNG", pnginfo=pnginfo)
    
    # upscaling
    # result = instance[0].extra_batch_images(
    #     images = result,
    #     upscaler_1 = "R-ESRGAN 4x+ Anime6B",
    #     upscaling_resize = 4,
    #     )
    # result = result.get_images()
    
    state = list(result)
    
    text_state = f'[유저 프롬프트] : {keyword_box}\
        \n[생성 프롬프트] : {ogprompt}\''
        #\n[image size] : {width} x {height}'
        
    return state, state, text_state


# 바로 generate함수로 가게 수정???
def generate_wrap(state:gr.State, keyword_box, category, style, text_box,synopsis_check, seed=False):
    """
    Wrapper function for generating image
    if seed is true, use random seed
    """

    return generate(state, keyword_box, category, style, text_box, synopsis_check, seed=seed)


def style_change(category):
    if category == "디즈니":
        return gr.update(choices=['공주', '가족', '픽사'], visible=True)
    elif category == "웹툰/웹소설":
        return gr.update(choices=['로맨스', '판타지', '일상'], visible=True)
    elif category == "게임":
        return gr.update(choices=['RPG/FPS', '캐주얼', '레트로'], visible=True)
    else:
        return gr.update(visible=False) 

class Seafoam(Base):
    pass


seafoam = Seafoam()    


############## Gradio Things ##############
with gr.Blocks(theme=seafoam, css="#gallery .overflow-y-auto{height:2000px}") as demo:
    state = gr.State([])

    with gr.Row():
        gr.HTML(
            """<div style="text-align: center; max-width: 500px; margin: 0 auto;">
            <div>
            <h1>BRANT</h1>
            </div>
        </div>"""
        )
   

    with gr.Row():
        with gr.Column(scale=1, min_width=600):
            
            keyword_box = gr.Textbox(
                    elem_id="input",
                    label="키워드를 입력해주세요.",
                    show_label=True
                )
            synopsis_check = gr.Checkbox(label="시놉시스 적용", value=False)
            with gr.Row() : 
                category = gr.Radio(
                    ['디즈니', '웹툰/웹소설', '게임'],
                    label='카테고리'
                )
                style = gr.Radio(label='스타일', choices=[], visible=False)
            with gr.Row():
                text_box = gr.Textbox(
                    elem_id="input",
                    label="로고로 만들 텍스트를 입력해주세요.",
                    show_label=True
                )
            
            with gr.Row():
                gallery = gr.Gallery(
                    elem_id="gallery", 
                    label="results", 
                    show_label=True,
                    columns=[4], rows=[1]
                )

            with gr.Row():
                btn = gr.Button("생성", scale=False, variant='primary')
                regenerate_btn = gr.Button("재생성", scale=False)

    with gr.Row():
        gr.HTML(
            """<div style="text-align: center; max-width: 500px; margin: 0 auto;">
            <div>
                <h2>2024 Smilegate 위클리톤</h2>
            </div>
        </div>"""
        )

    bool_state = gr.Checkbox(value=True, label="empty", visible=False)  # Dummy input for regenerate_btn

    category.change(style_change, inputs=category, outputs=style)

    btn.click(generate_wrap, [state, keyword_box, category, style, text_box, synopsis_check], [state, gallery])
    regenerate_btn.click(generate_wrap, [state, keyword_box, category, style, text_box,synopsis_check, bool_state], [state, gallery])

demo.launch(share=True)