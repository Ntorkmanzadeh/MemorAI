import modal
import requests
import json
import logging
import time
import subprocess
from requests.exceptions import Timeout, RequestException

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Modal app
app = modal.App("flashcard-generator")

# Define the image with Ollama installed
def setup_ollama():
    logger.info("Starting Ollama setup...")
    # Install Ollama
    subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
    logger.info("Ollama installed successfully")
    
    # Start Ollama server
    server_process = subprocess.Popen(["ollama", "serve"])
    time.sleep(5)  # Wait for server to start
    logger.info("Ollama server started")
    
    # Pull model
    logger.info("Pulling llama2 model...")
    subprocess.run(["ollama", "pull", "llama2"], check=True)
    logger.info("Model pulled successfully")
    
    # Stop Ollama server
    server_process.terminate()
    server_process.wait()
    logger.info("Ollama server stopped")

# Create container image with Ollama
image = (
    modal.Image.debian_slim()
    .apt_install("curl")
    .pip_install("requests")
    .run_function(setup_ollama)
)

@app.function(image=image, timeout=300, gpu="A10G")  # Request A10G GPU
async def run_ollama_prompt(prompt: str, model: str = "llama2") -> str:
    """Run a prompt through Ollama and return the response."""
    server_process = None
    try:
        # Start Ollama in the background
        logger.info("Starting Ollama server...")
        server_process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)  # Wait for server to start
        logger.info("Ollama server started, waiting for it to be ready...")
        
        # Check if server is ready
        for i in range(3):
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    logger.info("Ollama server is ready")
                    break
            except:
                logger.info(f"Waiting for Ollama server to be ready (attempt {i+1}/3)...")
                time.sleep(5)
        
        # Make the request with timeout
        logger.info(f"Sending request to Ollama with model {model}...")
        logger.info(f"Prompt length: {len(prompt)} characters")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "context_window": 2048,  # Limit context window
                "temperature": 0.7,      # Add some randomness but keep it focused
                "num_predict": 1024      # Limit response length
            },
            timeout=240  # 4 minute timeout for the request
        )
        response.raise_for_status()
        result = response.json()["response"]
        logger.info(f"Successfully received response from Ollama (length: {len(result)} characters)")
        return result
        
    except Timeout:
        logger.error("Request to Ollama timed out after 240 seconds")
        return "Error: Request timed out"
    except RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return f"Error: Request failed - {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"Error: {str(e)}"
    finally:
        if server_process:
            logger.info("Stopping Ollama server...")
            server_process.terminate()
            server_process.wait()
            logger.info("Ollama server stopped")

if __name__ == "__main__":
    with app.run():
        prompt = "What is the capital of France?"
        response = run_ollama_prompt.remote(prompt)
        print(f"Prompt: {prompt}")
        print(f"Response: {response}") 