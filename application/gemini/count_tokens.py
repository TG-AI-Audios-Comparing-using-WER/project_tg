from google import genai
from pathlib import Path
from dotenv import load_dotenv
import os
# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY)
model = 'gemini-2.0-flash'

# Call `count_tokens` to get the input token count (`total_tokens`).

directory = Path('../../Datasets_Audios_Medicos/Transcriptions/ai_transcriptions/transcription_gemini')
for text_file in directory.iterdir(): 
    if text_file.is_file():
        with open(text_file, 'r', encoding='utf-8') as f:
            content = f.read()
            total_tokens = client.models.count_tokens(
                model='gemini-2.0-flash',
                contents=content,
            )
            print(f"total_tokens for {text_file.name}: ", total_tokens)
    




# print("total_tokens: ", model.count_tokens())
# ( total_tokens: 10 )



# On the response for `generate_content`, use `usage_metadata`
# to get separate input and output token counts
# (`prompt_token_count` and `candidates_token_count`, respectively),
# as well as the combined token count (`total_token_count`).
# print(response.usage_metadata)
# ( prompt_token_count: 11, candidates_token_count: 73, total_token_count: 84 )