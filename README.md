# Flashcard Generator

A web application for generating and managing flashcards from PDF and PPTX files using AI.

## Features

- **User Management**: Create and manage user accounts (no password required)
- **Deck Organization**: Organize flashcards into different decks (e.g., "Algebra 1 Test 2", "Spelling Mid-term")
- **Flashcard Generation**: Upload PDF or PPTX files to automatically generate flashcards
- **Flashcard Editing**: Edit, add, and delete flashcards within decks
- **Persistence**: Flashcards persist across application restarts
- **Logging**: Comprehensive logging for debugging and monitoring

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set up Modal:
   ```
   modal token new
   ```

3. Start the server:
   ```
   uvicorn main:app --reload
   ```

## API Endpoints

### User Management
- `POST /users`: Create a new user
- `GET /users/{user_id}`: Get user information

### Deck Management
- `POST /decks`: Create a new deck
- `GET /decks`: Get all decks for a user
- `PUT /decks/{deck_id}`: Update a deck
- `DELETE /decks/{deck_id}`: Delete a deck

### Flashcard Management
- `GET /decks/{deck_id}/flashcards`: Get all flashcards in a deck
- `POST /decks/{deck_id}/flashcards`: Create a new flashcard in a deck
- `PUT /flashcards/{card_id}`: Update a flashcard
- `DELETE /flashcards/{card_id}`: Delete a flashcard

### File Processing
- `POST /process-file`: Process a file or text and add flashcards to a deck

## Data Storage

The application uses SQLite for data storage. The database file is located at `data/flashcards.db`.

## Logging

Logs are stored in the `logs` directory:
- Application logs: `flashcard_generator_YYYYMMDD_HHMMSS.log`
- Model responses: `model_response_YYYYMMDD_HHMMSS.txt`

## Technologies Used

- FastAPI: Web framework
- Modal: Cloud GPU hosting and parallelization
- Ollama: LLM management and inference
- SQLite: Database
- PyPDF2: PDF processing
- python-pptx: PPTX processing 
