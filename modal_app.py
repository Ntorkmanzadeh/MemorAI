import modal
import requests
import json
import logging
import time
import subprocess
from requests.exceptions import Timeout, RequestException
from PIL import Image
import io
from pdf2image import convert_from_bytes
import os
from typing import List
import base64

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
    logger.info("Pulling llama3.2-vision model...")
    subprocess.run(["ollama", "pull", "llama3.2-vision"], check=True)
    logger.info("Model pulled successfully")
    
    # Stop Ollama server
    server_process.terminate()
    server_process.wait()
    logger.info("Ollama server stopped")

# Create container image with Ollama
image = (
    modal.Image.debian_slim()
    .apt_install("curl", "poppler-utils")
    .pip_install("requests", "Pillow", "pdf2image")
    .run_function(setup_ollama)
)

@app.function(image=image, timeout=300, gpu="A10G")  # Request A10G GPU
async def run_ollama_prompt(prompt: str, model: str = "llama3.2-vision") -> str:
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

@app.function(image=image, timeout=300, gpu="A10G")
async def process_image_with_llama(image_data: bytes, message: str) -> str:
    """Process an image using llama3.2-vision to generate flashcards."""
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

        # Convert bytes to base64 for API
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Make the request with timeout
        logger.info("Sending request to Ollama with vision model...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2-vision",
                "prompt": message,
                "images": [image_base64],
                "stream": False,
                "context_window": 2048,
                "temperature": 0.7,
                "num_predict": 1024
            },
            timeout=240  # 4 minute timeout
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

@app.function(image=image, timeout=300, gpu="A10G")  # Request A10G GPU
async def process_multiple_images_with_llama(images: List[bytes], message: str) -> str:
    """Process multiple images with llama3.2-vision model, one at a time within a single Ollama session."""
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
        
        # Process each image individually
        all_responses = []
        for i, img_data in enumerate(images, 1):
            logger.info(f"Processing image {i} of {len(images)}")
            
            # Convert image to base64
            base64_image = base64.b64encode(img_data).decode('utf-8')
            
            # Use a fixed prompt for image analysis
            page_prompt = f"Analyze this image (page {i} of {len(images)}). Provide a detailed summary of the content."
            
            # Make the request with timeout
            logger.info(f"Sending request to Ollama for page {i}")
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2-vision",
                    "prompt": page_prompt,
                    "images": [base64_image],  # Changed to match process_image_with_llama format
                    "stream": False,
                    "context_window": 4096,
                    "temperature": 0.7,
                    "num_predict": 2048
                },
                timeout=240  # 4 minute timeout
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            page_response = result.get("response", "")
            
            # Add page demarcation
            all_responses.append(f"=== Page {i} ===\n{page_response}\n")
        
        # Now process all the page summaries together to generate flashcards
        logger.info("Generating flashcards from all page summaries")
        combined_summaries = "\n\n".join(all_responses)
        
        # Use the provided message for the final flashcard generation
        final_prompt = f"{message}\n\nPage Summaries:\n{combined_summaries}"
        
        final_response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2-vision",
                "prompt": final_prompt,
                "stream": False,
                "context_window": 4096,
                "temperature": 0.7,
                "num_predict": 2048
            },
            timeout=240
        )
        final_response.raise_for_status()
        
        # Get the final flashcards
        final_result = final_response.json()
        flashcards = final_result.get("response", "")
        
        return flashcards
        
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

def convert_pdf_to_images(pdf_content: bytes) -> List[Image.Image]:
    """Convert PDF content to a list of PIL Images."""
    return convert_from_bytes(pdf_content)

if __name__ == "__main__":
    with app.run():
        prompt = "What is the capital of France?"
        response = run_ollama_prompt.remote(prompt)
        print(f"Prompt: {prompt}")
        print(f"Response: {response}") 