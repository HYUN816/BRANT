import google.generativeai as genai
import json

# JSON 파일에서 API 키를 불러오는 함수
def load_api_keys(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

API_KEYS_FILE_PATH = r'C:\Users\leehg\developer\brant_demo\gemini_handler\api_key.txt' ## TODO 상대경로로 
api_keys = load_api_keys(API_KEYS_FILE_PATH)

# Gemini API 키 설정
gemini_api_key = api_keys["gemini"]
genai.configure(api_key=gemini_api_key)

# Set up the model
generation_config = {
  "temperature": 0.1,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 512,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_NONE",
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_NONE",
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_NONE",
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_NONE",
  }
]

ko2en_inst = r'C:\Users\leehg\developer\brant_demo\gemini_handler\instructions\ko2en.txt' ## TODO 상대경로로 
synopsis_to_tags_inst = r'C:\Users\leehg\developer\brant_demo\gemini_handler\instructions\prompt_template.json'
class GeminiAPI:
    def __init__(self, 
                 generation_config = generation_config, model:str = "gemini-pro") -> None:
        self.model = genai.GenerativeModel(model_name=model,
                            generation_config=generation_config,
                            safety_settings=safety_settings)

    def ko_en(self, input_text:str):
        with open(ko2en_inst, 'r', encoding='UTF8') as f:
          lines = f.read()
        prompt_out = [lines]
      
        input_text = f'Input: {input_text},'
        prompt_out.append(input_text)
      
        g_output = self.model.generate_content(prompt_out)
        if 'block_reason' in g_output.prompt_feedback:
            output_text = 'blocked'
        else:
            output_text = g_output.text
        return output_text
    
    def synopsis_to_tags(self, input_text:str):
        with open(synopsis_to_tags_inst, 'r', encoding='utf-8') as f:
          json_query = json.load(f)
        json_query["input"]  = {"user_query": input_text}
        query = str(json_query)

        g_output = self.model.generate_content(query)
        if 'block_reason' in g_output.prompt_feedback:
            tags = 'blocked'
        else:
            tags = json.loads(g_output.text)["prompt"]
            tags = ", ".join(tags)
        return tags