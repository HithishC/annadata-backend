from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = FastAPI(title="Annadata API")

# CORS — allows mobile app to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class CropRequest(BaseModel):
    cropType: str
    sowingDate: str
    location: str
    variety: str = ""
    language: str = "en"

@app.get("/")
def root():
    return {"status": "Annadata API is running 🌾"}

@app.post("/generate-calendar")
def generate_calendar(req: CropRequest):
    prompt = f"""
You are an expert Indian agricultural scientist. Generate a detailed 20-week farming calendar for:
- Crop: {req.cropType}
- Variety: {req.variety or 'standard'}
- Sowing Date: {req.sowingDate}
- Location: {req.location}, India
- Language: {req.language}

Return ONLY a JSON array with exactly 20 objects. Each object must have:
{{
  "weekNum": 1,
  "startDate": "YYYY-MM-DD",
  "endDate": "YYYY-MM-DD",
  "tasks": [
    {{
      "type": "water|fertilize|pest|harvest|prepare",
      "title": "Task title in English",
      "desc": "Detailed description",
      "translatedTask": "Task title in {req.language}"
    }}
  ]
}}

Calculate dates starting from {req.sowingDate}.
Return ONLY the JSON array, no other text.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()

    # Clean up response
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    calendar = json.loads(raw)
    return {"success": True, "calendar": calendar}