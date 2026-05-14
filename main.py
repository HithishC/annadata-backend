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

    language_name = LANGUAGE_MAP.get(req.language, "English")

    def try_generate():
        prompt = f"""
You are an expert Indian agricultural scientist. Generate a 20-week farming calendar for:
- Crop: {req.cropType}
- Variety: {req.variety or 'standard'}
- Sowing Date: {req.sowingDate}
- Location: {req.location}, India
- Output Language: {language_name}

Return ONLY a valid JSON array with exactly 20 objects. Each object:
{{
  "weekNum": 1,
  "startDate": "YYYY-MM-DD",
  "endDate": "YYYY-MM-DD",
  "tasks": [
    {{
      "type": "water|fertilize|pest|harvest|prepare",
      "title": "Task title in English",
      "desc": "Description in English",
      "translatedTitle": "Task title in {language_name}",
      "translatedDesc": "Description in {language_name}"
    }}
  ]
}}

Rules:
- Calculate dates from {req.sowingDate}
- Each week has 1-3 tasks specific to {req.cropType} in {req.location}
- If language is English, translatedTitle = title
- Return ONLY the JSON array, no markdown, no extra text
"""
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
            temperature=0.3,
        )

        raw = response.choices[0].message.content.strip()

        # Clean markdown if present
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    raw = part
                    break

        raw = raw.strip()
        return json.loads(raw)

    # Try up to 3 times
    last_error = None
    for attempt in range(3):
        try:
            calendar = try_generate()
            return {
                "success": True,
                "cropType": req.cropType,
                "location": req.location,
                "language": req.language,
                "languageName": language_name,
                "totalWeeks": len(calendar),
                "calendar": calendar
            }
        except json.JSONDecodeError as e:
            last_error = str(e)
            continue
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"API error: {str(e)}")

    raise HTTPException(
        status_code=500,
        detail=f"AI returned invalid JSON after 3 attempts. Please try again."
    )