from dotenv import load_dotenv
import os

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH")
DEBUG = os.getenv("DEBUG") == "True"
PORT = int(os.getenv("API_PORT", 8000))