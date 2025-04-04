from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from typing import Optional, List, Dict, Any
import PyPDF2
from pptx import Presentation
import io
import logging
import os
from datetime import datetime
from pathlib import Path
import database as db
import modal
import re
import asyncio

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Set up logging
log_file = logs_dir / f"flashcard_generator_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get reference to the deployed Modal function
run_ollama_prompt = modal.Function.from_name("flashcard-generator", "run_ollama_prompt")

# User dependency
async def get_current_user(user_id: str = Form(...)):
    """Get the current user from the user_id form field."""
    try:
        user = db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"id": user_id, "name": user["name"]}
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting user: {str(e)}")

def extract_text_from_pdf(file_content: bytes) -> str:
    logger.info("Extracting text from PDF")
    pdf_file = io.BytesIO(file_content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    logger.info(f"Extracted {len(text)} characters from PDF")
    return text

def extract_text_from_pptx(file_content: bytes) -> str:
    logger.info("Extracting text from PPTX")
    pptx_file = io.BytesIO(file_content)
    prs = Presentation(pptx_file)
    text = ""
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    logger.info(f"Extracted {len(text)} characters from PPTX")
    return text

async def generate_flashcards(text: str, num_cards: int = 10) -> List[Dict[str, str]]:
    """Generate flashcards from text using Ollama."""
    logging.info(f"Starting flashcard generation for text of length {len(text)}")
    logging.info(f"Requesting {num_cards} flashcards")
    
    prompt = f"""Generate {num_cards} flashcards from the following text. Return ONLY a JSON array of objects with 'question' and 'answer' fields.
Example format:
[
    {{"question": "What is X?", "answer": "X is Y"}},
    {{"question": "Who discovered Z?", "answer": "Z was discovered by W"}}
]

Text to generate flashcards from:
{text}

Remember to return ONLY the JSON array with no additional text or formatting."""

    try:
        logging.info("Calling Modal function run_ollama_prompt...")
        # Call the Modal function directly
        response = await run_ollama_prompt.remote.aio(prompt)
        logging.info("Received response from Modal function")
        logging.info("Complete model response:")
        logging.info(response)
        
        if not response:
            logging.error("Received empty response from Modal app")
            return generate_fallback_cards(num_cards)
        
        # Try to find a JSON array in the response
        try:
            # First try to parse the entire response as JSON
            try:
                cards = json.loads(response)
                if isinstance(cards, list):
                    logging.info(f"Successfully parsed JSON array with {len(cards)} cards")
                    return cards
            except json.JSONDecodeError:
                # If that fails, try to extract JSON from the response
                logging.info("Failed to parse entire response as JSON, trying to extract JSON array")
            
            # Look for text between square brackets
            match = re.search(r'\[(.*?)\]', response, re.DOTALL)
            if match:
                json_str = f"[{match.group(1)}]"
                cards = json.loads(json_str)
                logging.info(f"Successfully extracted JSON array with {len(cards)} cards")
                return cards
            else:
                logging.warning("No JSON array found in response")
                return generate_fallback_cards(num_cards)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON from response: {e}")
            return generate_fallback_cards(num_cards)
            
    except Exception as e:
        logging.error(f"Error generating flashcards: {str(e)}")
        logging.error(f"Error type: {type(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return generate_fallback_cards(num_cards)

def generate_fallback_cards(num_cards: int) -> List[Dict[str, str]]:
    """Generate fallback flashcards when the AI service fails."""
    logging.info(f"Generating {num_cards} fallback flashcards")
    cards = []
    for i in range(num_cards):
        cards.append({
            "question": f"Sample question {i+1}?",
            "answer": f"This is a sample answer {i+1}. The actual AI service is currently unavailable."
        })
    return cards

# User management endpoints
@app.post("/users")
async def create_user(name: str = Form(...)):
    """Create a new user."""
    try:
        user_id = db.create_user(name)
        return {"user_id": user_id, "name": name}
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    """Get a user by ID."""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Deck management endpoints
@app.post("/decks")
async def create_deck(user: Dict[str, Any] = Depends(get_current_user), name: str = Form(...), description: str = Form("")):
    """Create a new deck for a user."""
    try:
        deck_id = db.create_deck(user["id"], name, description)
        return {
            "deck_id": deck_id,
            "name": name,
            "description": description,
            "user_id": user["id"]
        }
    except Exception as e:
        logger.error(f"Error creating deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating deck: {str(e)}")

@app.get("/decks")
async def get_decks(user: Dict[str, Any] = Depends(get_current_user)):
    """Get all decks for a user."""
    try:
        decks = db.get_decks(user["id"])
        return {"decks": decks}
    except Exception as e:
        logger.error(f"Error getting decks: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting decks: {str(e)}")

@app.put("/decks/{deck_id}")
async def update_deck(deck_id: str, name: str = Form(...), description: str = Form("")):
    """Update a deck."""
    try:
        db.update_deck(deck_id, name, description)
        return {"deck_id": deck_id, "name": name, "description": description}
    except Exception as e:
        logger.error(f"Error updating deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating deck: {str(e)}")

@app.delete("/decks/{deck_id}")
async def delete_deck(deck_id: str):
    """Delete a deck."""
    try:
        db.delete_deck(deck_id)
        return {"message": "Deck deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting deck: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting deck: {str(e)}")

# Flashcard management endpoints
@app.get("/decks/{deck_id}/flashcards")
async def get_flashcards(deck_id: str):
    """Get all flashcards in a deck."""
    try:
        flashcards = db.get_flashcards(deck_id)
        return {"flashcards": flashcards}
    except Exception as e:
        logger.error(f"Error getting flashcards: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting flashcards: {str(e)}")

@app.post("/decks/{deck_id}/flashcards")
async def create_flashcard(deck_id: str, question: str = Form(...), answer: str = Form(...)):
    """Create a new flashcard in a deck."""
    try:
        card_id = db.create_flashcard(deck_id, question, answer)
        return {"card_id": card_id, "question": question, "answer": answer}
    except Exception as e:
        logger.error(f"Error creating flashcard: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating flashcard: {str(e)}")

@app.put("/flashcards/{card_id}")
async def update_flashcard(card_id: str, question: str = Form(...), answer: str = Form(...)):
    """Update a flashcard."""
    try:
        db.update_flashcard(card_id, question, answer)
        return {"card_id": card_id, "question": question, "answer": answer}
    except Exception as e:
        logger.error(f"Error updating flashcard: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating flashcard: {str(e)}")

@app.delete("/flashcards/{card_id}")
async def delete_flashcard(card_id: str):
    """Delete a flashcard."""
    try:
        db.delete_flashcard(card_id)
        return {"message": "Flashcard deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting flashcard: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting flashcard: {str(e)}")

@app.post("/process-file")
async def process_file(
    user: Dict[str, Any] = Depends(get_current_user),
    deck_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
):
    """Process a file or text and add flashcards to a deck."""
    try:
        content_text = ""
        
        if file:
            logger.info(f"Processing file: {file.filename}")
            file_content = await file.read()
            if file.filename.endswith('.pdf'):
                content_text = extract_text_from_pdf(file_content)
            elif file.filename.endswith('.pptx'):
                content_text = extract_text_from_pptx(file_content)
            else:
                logger.warning(f"Unsupported file format: {file.filename}")
                return JSONResponse(
                    status_code=400,
                    content={"error": "Unsupported file format. Please upload PDF or PPTX files."}
                )
        elif text:
            logger.info("Processing text input")
            content_text = text
        else:
            logger.warning("No file or text provided")
            return JSONResponse(
                status_code=400,
                content={"error": "No file or text provided"}
            )
        
        if not content_text.strip():
            logger.warning("No content extracted from input")
            return JSONResponse(
                status_code=400,
                content={"error": "No content could be extracted from the input"}
            )
        
        flashcards = await generate_flashcards(content_text)
        logger.info(f"Generated {len(flashcards)} flashcards")
        
        # Import flashcards into the deck
        db.import_flashcards(deck_id, flashcards)
        
        return {"message": f"Successfully added {len(flashcards)} flashcards to deck", "flashcards": flashcards}
    
    except Exception as e:
        logger.error(f"Error processing content: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing content: {str(e)}"}
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 