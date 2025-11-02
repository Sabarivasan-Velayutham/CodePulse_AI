import google.generativeai as genai
import os
from dotenv import load_dotenv 

# 1. Load variables from the .env file into os.environ
load_dotenv() 

# 2. The configure() function will now automatically find the 
#    GEMINI_API_KEY or GOOGLE_API_KEY in the environment variables (os.environ).
#    You no longer need to pass the key explicitly.
genai.configure() 

model = genai.GenerativeModel('gemini-2.5-flash')
response = model.generate_content("Say hello!")
print(response.text)