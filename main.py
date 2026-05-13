from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

app = FastAPI(title="Annadata API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Language map
LANGUAGE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "te": "Telugu",
    "ta": "Tamil",
    "mr": "Marathi",
    "ml": "Malayalam",
    "bn": "Bengali",
    "pa": "Punjabi",
}

class CropRequest(BaseModel):
    cropType: str
    sowingDate: str
    location: str
    variety: str = ""
    language: str = "en"

@app.get("/")
def root():
    return {"status": "Annadata API is running 🌾"}

@app.get("/languages")
def get_languages():
    return {"languages": LANGUAGE_MAP}

@app.post("/generate-calendar")
def generate_calendar(req: CropRequest):
    if not req.cropType or len(req.cropType) < 2:
        raise HTTPException(status_code=400, detail="Invalid crop type")

    # Get full language name
    language_name = LANGUAGE_MAP.get(req.language, "English")

    try:
        prompt = f"""
You are an expert Indian agricultural scientist. Generate a detailed 20-week farming calendar for:
- Crop: {req.cropType}
- Variety: {req.variety or 'standard'}
- Sowing Date: {req.sowingDate}
- Location: {req.location}, India
- Output Language: {language_name}

Return ONLY a JSON array with exactly 20 objects. Each object must have:
{{
  "weekNum": 1,
  "startDate": "YYYY-MM-DD",
  "endDate": "YYYY-MM-DD",
  "tasks": [
    {{
      "type": "water|fertilize|pest|harvest|prepare",
      "title": "Task title in English",
      "desc": "Detailed description in English",
      "translatedTitle": "Task title in {language_name}",
      "translatedDesc": "Task description in {language_name}"
    }}
  ]
}}

Important rules:
- Calculate all dates starting from {req.sowingDate}
- Each week must have 1-3 relevant tasks
- Tasks must be specific to {req.cropType} farming in {req.location}, India
- translatedTitle and translatedDesc must be in {language_name} script
- If language is English, translatedTitle = title and translatedDesc = desc
- Return ONLY the JSON array, absolutely no other text
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.3,
        )

        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        calendar = json.loads(raw)

        return {
            "success": True,
            "cropType": req.cropType,
            "location": req.location,
            "language": req.language,
            "languageName": language_name,
            "totalWeeks": len(calendar),
            "calendar": calendar
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="AI returned invalid JSON. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"API error: {str(e)}"
        )