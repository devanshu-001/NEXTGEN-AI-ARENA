"""
Pulse AI — FastAPI Backend
Run: uvicorn api:app --port 8000 
(Note: Removed --reload to prevent the massive AI model from reloading on every save!)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Literal
from health_engine import HealthEngine, UserInput
import torch
import pandas as pd # ⚡ IMPORT PANDAS FOR LIVE SEARCH ⚡
from unsloth import FastLanguageModel

app = FastAPI(title="Pulse AI Health Engine", version="1.0.0")

# Allow the HTML login page (served from any origin / file://) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 🧠 PULSE AI MODEL LOADING ───────────────────────────────────────────
print("Loading Pulse AI Brain...")
try:
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = "pulse_ai_lora_model", # Path to your saved Unsloth model
        max_seq_length = 2048,
        dtype = None,
        load_in_4bit = True,
    )
    print("Pulse AI Ready!")
except Exception as e:
    print(f"⚠️ Warning: Could not load the AI model. (Are you on a GPU?) Error: {e}")
    model, tokenizer = None, None


# ── 🛠️ AGENTIC TOOLS (Live Data Search) ───────────────────────────────────────
print("Loading Agent Databases...")
try:
    # Load your CSVs into memory for instant searching
    food_db = pd.read_csv("comprehensive_foods_usda.csv")
    gym_db = pd.read_csv("mega_gym_dataset.csv")
    print("Databases loaded successfully!")
except Exception as e:
    print(f"⚠️ Warning: Database missing: {e}. Ensure CSVs are in the same folder.")
    food_db, gym_db = None, None

def search_food_tool(query: str) -> str:
    """Searches the USDA database for exact macros of a food item."""
    if food_db is None: return ""
    
    # Simple keyword search
    keywords = query.lower().split()
    # Find foods that matcha the keywords
    matches = food_db[food_db['food_name'].str.lower().apply(lambda x: any(k in x for k in keywords))]
    
    if matches.empty: return ""
    
    # Take the top 3 best matches to feed to the AI
    top_matches = matches.head(3)
    food_context = "\n[LIVE FOOD DATABASE RESULTS]:\n"
    for _, row in top_matches.iterrows():
        food_context += f"- {row['food_name']}: {row['calories']} kcal, {row['protein_g']}g Protein, {row['carbs_g']}g Carbs, {row['fat_g']}g Fat per {row['serving_size']} {row['serving_unit']}\n"
    return food_context

def search_gym_tool(query: str, target_muscle: str = "") -> str:
    """Searches the Gym database for specific exercises."""
    if gym_db is None: return ""
    
    matches = gym_db[gym_db['BodyPart'].str.contains(target_muscle, case=False, na=False)] if target_muscle else gym_db
    
    # Get 3 random matching exercises
    if matches.empty: return ""
    top_matches = matches.sample(min(3, len(matches)))
    
    gym_context = "\n[LIVE GYM DATABASE RESULTS]:\n"
    for _, row in top_matches.iterrows():
        gym_context += f"- Exercise: {row['Title']} (Level: {row['Level']}, Equipment: {row['Equipment']}). How to do it: {row['Desc']}\n"
    return gym_context


# ── Request / Response models ─────────────────────────────────────────────────
class ProfileRequest(BaseModel):
    age:            int     = Field(..., ge=1, le=120, example=28)
    gender:         str     = Field(..., example="male")
    weight_kg:      float   = Field(..., gt=0, example=78.5)
    height_cm:      float   = Field(..., gt=0, example=178.0)
    activity_level: str     = Field(..., example="intermediate")

    @validator("gender")
    def gender_lower(cls, v):
        return v.strip().lower()

    @validator("activity_level")
    def activity_lower(cls, v):
        return v.strip().lower()

class HealthResponse(BaseModel):
    age:                   int
    gender:                str
    weight_kg:             float
    height_cm:             float
    activity_level:        str
    bmi:                   float
    bmi_category:          str
    bmr:                   float
    tdee:                  float
    body_fat_pct:          float
    ideal_weight_min_kg:   float
    ideal_weight_max_kg:   float
    calories_maintain:     float
    calories_lose_half_kg: float
    calories_gain_half_kg: float
    ai_summary:            str

class ChatRequest(BaseModel):
    user_message: str
    user_context: str


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "Pulse AI Engine Online ⚡"}

@app.post("/calculate", response_model=HealthResponse)
def calculate(req: ProfileRequest):
    try:
        user    = UserInput(**req.dict())
        metrics = HealthEngine.calculate(user)
        return HealthResponse(**metrics.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

# ⚡ UPDATED CHAT ENDPOINT WITH AGENTIC ROUTING ⚡
@app.post("/chat")
def chat_with_pulse(req: ChatRequest):
    if model is None or tokenizer is None:
        raise HTTPException(status_code=500, detail="AI model is not loaded. Ensure GPU is active.")

    user_msg_lower = req.user_message.lower()
    live_data_context = ""

    # 🤖 AGENTIC ROUTING: Does the AI need to use its tools?
    if any(word in user_msg_lower for word in ["food", "meal", "eat", "protein", "calories", "breakfast", "lunch", "dinner", "snack"]):
        print("⚡ Agent Triggered: Food Search Tool")
        live_data_context += search_food_tool(user_msg_lower)
        
    if any(word in user_msg_lower for word in ["workout", "exercise", "chest", "back", "legs", "arms", "gym", "train", "abs", "core"]):
        print("⚡ Agent Triggered: Gym Search Tool")
        # Try to extract a body part if they mentioned one
        muscle = ""
        for m in ["chest", "back", "legs", "shoulders", "arms", "abdominals", "core", "abs"]:
            if m in user_msg_lower: 
                muscle = m
                if muscle in ["core", "abs"]: muscle = "abdominals" # map to dataset term
        live_data_context += search_gym_tool(user_msg_lower, target_muscle=muscle)

    # Combine the user's specific context, LIVE tool data, and their question
    final_context = req.user_context + "\n" + live_data_context

    alpaca_prompt = f"""Below is an instruction that describes a task, paired with user context. Write a response that appropriately completes the request based on the user's specific health data and any live database results provided.

### Context:
{final_context}

### Instruction:
{req.user_message}

### Response:
"""
    # 1. Format the text for the model
    inputs = tokenizer([alpaca_prompt], return_tensors = "pt").to("cuda")

    # 2. Generate the answer (Increased max_new_tokens for longer, detailed plans)
    outputs = model.generate(**inputs, max_new_tokens = 350, use_cache = False)
    
    # 3. Decode from token IDs back to human text
    response_text = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
    
    # 4. Extract just the newly generated response
    final_answer = response_text.split("### Response:\n")[-1]

    return {"ai_response": final_answer.strip()}