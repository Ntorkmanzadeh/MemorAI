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
from typing import List, Tuple
import base64
import asyncio

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

    logger.info("Pulling llama3.2 model...")
    subprocess.run(["ollama", "pull", "llama3.2"], check=True)
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

@app.function(image=image, timeout=300, gpu="A10G")
def process_single_image(img_data: bytes, page_num: int, total_pages: int) -> Tuple[int, str]:
    """Process a single image and return its page number and response."""
    server_process = None
    try:
        # Start Ollama in the background
        logger.info(f"Starting Ollama server for page {page_num}...")
        server_process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)  # Wait for server to start
        
        # Check if server is ready
        for i in range(3):
            try:
                response = requests.get("http://localhost:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Ollama server is ready for page {page_num}")
                    break
            except:
                logger.info(f"Waiting for Ollama server to be ready for page {page_num} (attempt {i+1}/3)...")
                time.sleep(5)
        
        # Convert image to base64
        base64_image = base64.b64encode(img_data).decode('utf-8')
        
        # Use a fixed prompt for image analysis
        page_prompt = f"Analyze this image (page {page_num} of {total_pages}). Provide a detailed summary of the content."
        logger.info(f"Page {page_num} prompt: {page_prompt}")
        
        # Make the request with timeout
        logger.info(f"Sending request to Ollama for page {page_num}")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2-vision",
                "prompt": page_prompt,
                "images": [base64_image],
                "stream": False,
                "context_window": 4096,
                "temperature": 0.7,
                "num_predict": 1024
            },
            timeout=240
        )
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        vision_response = result.get("response", "")
        logger.info(f"=== Vision Model Response for Page {page_num} ===")
        logger.info(vision_response)
        logger.info("=" * 50)
        
        return page_num, vision_response
        
    except Exception as e:
        logger.error(f"Error processing image {page_num}: {str(e)}")
        return page_num, f"Error processing page {page_num}: {str(e)}"
    finally:
        if server_process:
            logger.info(f"Stopping Ollama server for page {page_num}...")
            server_process.terminate()
            server_process.wait()
            logger.info(f"Ollama server stopped for page {page_num}")

def split_into_chunks(summaries, max_words=1024):
    chunks = []
    current_chunk = []
    current_word_count = 0

    for summary in summaries:
        word_count = len(summary.split())
        if current_word_count + word_count > max_words:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = []
            current_word_count = 0

        current_chunk.append(summary)
        current_word_count += word_count

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks

@app.function(image=image, timeout=600, gpu="A10G")
def process_multiple_images_with_llama(images: List[bytes], message: str) -> str:
    """Process multiple images with llama3.2-vision model using Modal's map() for parallel execution."""
    try:
        # Process images in parallel using Modal's map()
        total_pages = len(images)
        logger.info(f"Processing {total_pages} images in parallel using Modal's map()...")
        
        # Create a list of argument tuples for starmap
        args_list = [(img_data, i+1, total_pages) for i, img_data in enumerate(images)]
        
        all_responses = list(process_single_image.starmap(args_list))
        sorted_responses = sorted(all_responses, key=lambda x: x[0])
        formatted_responses = [f"=== Page {page_num} ===\n{response}\n" for page_num, response in sorted_responses]
        
        # Split the combined summaries into chunks
        chunks = split_into_chunks(formatted_responses)

        final_flashcards = []
        for chunk in chunks:
            logger.info("Processing chunk:")
            logger.info(chunk)
            final_prompt = f"{message}\n\nPage Summaries:\n{chunk}"
            server_process = subprocess.Popen(["ollama", "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(5)

            for i in range(3):
                try:
                    response = requests.get("http://localhost:11434/api/tags", timeout=5)
                    if response.status_code == 200:
                        break
                except:
                    time.sleep(5)

            final_response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": final_prompt,
                    "stream": False,
                    "context_window": 32768,
                    "temperature": 0.7,
                    "num_predict": 32768
                },
                timeout=240
            )
            final_response.raise_for_status()
            final_result = final_response.json()
            flashcards = final_result.get("response", "")
            logger.info("Response for chunk:")
            logger.info(flashcards)
            final_flashcards.append(flashcards)

            server_process.terminate()
            server_process.wait()

        return "\n\n".join(final_flashcards)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}"

def convert_pdf_to_images(pdf_content: bytes) -> List[Image.Image]:
    """Convert PDF content to a list of PIL Images."""
    return convert_from_bytes(pdf_content)

if __name__ == "__main__":
    with app.run():
        prompt = "What is the capital of France?"
        response = run_ollama_prompt.remote(prompt)
        print(f"Prompt: {prompt}")
        print(f"Response: {response}") 