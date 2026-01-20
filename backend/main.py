from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from transformers import pipeline
from PIL import Image
import io
import google.generativeai as genai
import os

# ============ CONFIGURATION ============
# 🚨 SECURITY: Environment variable se API key lo
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY environment variable missing!")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-flash-latest')

# FastAPI app
app = FastAPI(
    title="AI Waste Segregation Assistant",
    description="Waste classify + Gemini guidance",
    version="3.1.0"
)

# Serve frontend files
app.mount("/static", StaticFiles(directory="../frontend"), name="static")
app.mount("/backend", StaticFiles(directory="."), name="backend")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model variable
classifier = None

def load_clip_model():
    """Load CLIP model globally"""
    global classifier
    print("🔄 Loading CLIP model...")
    try:
        classifier = pipeline(
            "zero-shot-image-classification",
            model="openai/clip-vit-base-patch32"
        )
        print("✅ CLIP Model loaded!")
        return True
    except Exception as e:
        print(f"❌ CLIP Model failed: {e}")
        return False

# Load model at startup (Gunicorn ke liye)
load_clip_model()

# Waste categories
WASTE_CATEGORIES = [
    "dry recyclable waste such as plastic bottles paper cardboard metal cans glass containers",
    "wet organic biodegradable waste such as food scraps fruit peels vegetable waste leaves",
    "electronic waste such as mobile phones laptops computers batteries chargers cables",
    "hazardous waste such as medicines chemicals light bulbs batteries syringes"
]

CATEGORY_MAPPING = {
    "dry recyclable waste such as plastic bottles paper cardboard metal cans glass containers": "dry",
    "wet organic biodegradable waste such as food scraps fruit peels vegetable waste leaves": "wet",
    "electronic waste such as mobile phones laptops computers batteries chargers cables": "e-waste",
    "hazardous waste such as medicines chemicals light bulbs batteries syringes": "hazardous"
}

DUSTBIN_INFO = {
    "dry": {
        "color": "🔵 BLUE",
        "hindi": "सूखा कचरा",
        "bin": "Blue Dustbin",
        "examples": "Plastic bottles, paper, cardboard, glass"
    },
    "wet": {
        "color": "🟢 GREEN", 
        "hindi": "गीला कचरा",
        "bin": "Green Dustbin",
        "examples": "Food waste, fruit peels, vegetables, leaves"
    },
    "e-waste": {
        "color": "⚫ BLACK/GREY",
        "hindi": "इलेक्ट्रॉनिक कचरा", 
        "bin": "E-waste Collection Center",
        "examples": "Phones, laptops, batteries, chargers"
    },
    "hazardous": {
        "color": "🔴 RED",
        "hindi": "खतरनाक कचरा",
        "bin": "Hazardous Waste Bin",
        "examples": "Medicines, chemicals, bulbs, batteries"
    }
}

def get_waste_guidance(category, detected_object):
    """Gemini se guidance lo"""
    prompt = f"""
You are an expert waste management advisor. A waste item has been classified as **{category.upper()} WASTE**.

Provide guidance in this EXACT format (keep it concise and clear):

**WHY this is {category.upper()} waste:**
[2-3 sentences explaining why this item belongs to this category]

**HOW to dispose safely:**
[3-4 bullet points with practical disposal steps]

**ECO TIP:**
[1 creative eco-friendly tip or interesting fact]

Keep the tone friendly and educational. Use simple language (mix of English and Hindi is fine).
"""
    
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return f"""
**WHY this is {category.upper()} waste:**
This item is classified as {category} waste based on its material composition and decomposition properties.

**HOW to dispose safely:**
• Separate this waste from other types
• Place it in the designated {category} waste bin
• Follow local waste management guidelines
• Contact your municipal corporation for collection schedule

**ECO TIP:**
Remember: Proper segregation at source makes recycling more effective and helps protect our environment! 🌱
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve frontend"""
    try:
        with open("../frontend/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except:
        return HTMLResponse(content="Frontend not found. Use /docs for API.")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "clip_model": classifier is not None,
        "gemini_api": GEMINI_API_KEY is not None
    }

@app.post("/classify")
async def classify_waste(file: UploadFile = File(...)):
    """Waste classification with guidance"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files allowed")
    
    if classifier is None:
        raise HTTPException(500, "Model not loaded. Please wait.")
    
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        print(f"📷 Processing image: {file.filename}")
        
        predictions = classifier(image, candidate_labels=WASTE_CATEGORIES)
        best_prediction = predictions[0]
        best_category_label = best_prediction['label']
        best_score = best_prediction['score']
        category = CATEGORY_MAPPING[best_category_label]
        
        print(f"🤖 Getting guidance for {category} waste...")
        guidance = get_waste_guidance(category, best_category_label)
        
        response = {
            "success": True,
            "detected_object": f"{category.upper()} waste detected",
            "confidence": f"{best_score*100:.1f}%",
            "waste_category": category.upper(),
            "dustbin": {
                "color": DUSTBIN_INFO[category]["color"],
                "type": DUSTBIN_INFO[category]["bin"],
                "hindi_name": DUSTBIN_INFO[category]["hindi"]
            },
            "examples": DUSTBIN_INFO[category]["examples"],
            "ai_guidance": guidance,
            "all_predictions": [
                {
                    "label": CATEGORY_MAPPING[p["label"]].upper() + " WASTE",
                    "score": f"{p['score']*100:.1f}%"
                } 
                for p in predictions
            ]
        }
        
        return response
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(500, f"Classification failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
