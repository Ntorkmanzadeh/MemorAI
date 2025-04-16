import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
import uuid

# Set up logging
logger = logging.getLogger(__name__)

# Create data directory if it doesn't exist
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Database file path
DB_PATH = data_dir / "flashcards.db"

def init_db():
    """Initialize the database with required tables."""
    logger.info("Initializing database")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create decks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS decks (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Create flashcards table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS flashcards (
        id TEXT PRIMARY KEY,
        deck_id TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (deck_id) REFERENCES decks (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def get_user(user_id):
    """Get a user by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "name": user[1],
            "created_at": user[2]
        }
    return None

def create_user(name):
    """Create a new user."""
    user_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()
    logger.info(f"Created new user: {name} (ID: {user_id})")
    return user_id

def get_decks(user_id):
    """Get all decks for a user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, created_at, updated_at FROM decks WHERE user_id = ?", (user_id,))
    decks = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": deck[0],
            "name": deck[1],
            "description": deck[2],
            "created_at": deck[3],
            "updated_at": deck[4]
        }
        for deck in decks
    ]

def create_deck(user_id, name, description=""):
    """Create a new deck for a user."""
    deck_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO decks (id, user_id, name, description) VALUES (?, ?, ?, ?)",
        (deck_id, user_id, name, description)
    )
    conn.commit()
    conn.close()
    logger.info(f"Created new deck: {name} (ID: {deck_id}) for user: {user_id}")
    return deck_id

def update_deck(deck_id, name, description):
    """Update a deck."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE decks SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (name, description, deck_id)
    )
    conn.commit()
    conn.close()
    logger.info(f"Updated deck: {deck_id}")

def delete_deck(deck_id):
    """Delete a deck and all its flashcards."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Delete all flashcards in the deck
    cursor.execute("DELETE FROM flashcards WHERE deck_id = ?", (deck_id,))
    
    # Delete the deck
    cursor.execute("DELETE FROM decks WHERE id = ?", (deck_id,))
    
    conn.commit()
    conn.close()
    logger.info(f"Deleted deck: {deck_id}")

def get_flashcards(deck_id):
    """Get all flashcards in a deck."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, answer, created_at, updated_at FROM flashcards WHERE deck_id = ?", (deck_id,))
    cards = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": card[0],
            "question": card[1],
            "answer": card[2],
            "created_at": card[3],
            "updated_at": card[4]
        }
        for card in cards
    ]

def create_flashcard(deck_id, question, answer):
    """Create a new flashcard in a deck."""
    card_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO flashcards (id, deck_id, question, answer) VALUES (?, ?, ?, ?)",
        (card_id, deck_id, question, answer)
    )
    conn.commit()
    conn.close()
    logger.info(f"Created new flashcard in deck: {deck_id}")
    return card_id

def update_flashcard(card_id, question, answer):
    """Update a flashcard."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE flashcards SET question = ?, answer = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (question, answer, card_id)
    )
    conn.commit()
    conn.close()
    logger.info(f"Updated flashcard: {card_id}")

def delete_flashcard(card_id):
    """Delete a flashcard."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    logger.info(f"Deleted flashcard: {card_id}")

def import_flashcards(deck_id, flashcards):
    """Import multiple flashcards into a deck."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for card in flashcards:
        card_id = str(uuid.uuid4())
        cursor.execute(
            "INSERT INTO flashcards (id, deck_id, question, answer) VALUES (?, ?, ?, ?)",
            (card_id, deck_id, card["question"], card["answer"])
        )
    
    conn.commit()
    conn.close()
    logger.info(f"Imported {len(flashcards)} flashcards into deck: {deck_id}")

def get_user_by_name(name):
    """Get a user by name."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, created_at FROM users WHERE name = ?", (name,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            "id": user[0],
            "name": user[1],
            "created_at": user[2]
        }
    return None

# Initialize the database when the module is imported
init_db() 