"""
Advanced Background Remover API
A Flask-based API for removing backgrounds from images using AI models.
Supports multiple image formats and can be used from any website.
"""

import os
import io
import base64
import logging
from typing import Optional, Tuple
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from PIL import Image
import numpy as np
from rembg import remove, new_session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure CORS to allow requests from any website
CORS(app, origins="*", 
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "OPTIONS"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 10 * 1024 * 1024))  # 10MB default
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}
REMBG_MODELS = ['u2net', 'u2netp', 'u2net_human_seg', 'u2net_cloth_seg', 'isnet-general-use']

class BackgroundRemover:
    """Advanced background removal class with multiple model support"""
    
    def __init__(self):
        self.sessions = {}
        self._load_default_session()
    
    def _load_default_session(self):
        """Load the default rembg session"""
        try:
            self.sessions['default'] = new_session('u2net')
            logger.info("Default rembg session loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load default session: {e}")
            raise
    
    def get_session(self, model_name: str = 'u2net'):
        """Get or create a rembg session for the specified model"""
        if model_name not in self.sessions:
            try:
                self.sessions[model_name] = new_session(model_name)
                logger.info(f"Created new session for model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to create session for model {model_name}: {e}")
                # Fallback to default session
                return self.sessions.get('default')
        return self.sessions[model_name]
    
    def remove_background(self, image: Image.Image, model: str = 'u2net') -> Image.Image:
        """Remove background from PIL Image using specified model"""
        try:
            # Convert image to RGB if it's not already
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert PIL image to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Get appropriate session
            session = self.get_session(model)
            
            # Remove background
            output = remove(img_byte_arr, session=session)
            
            # Convert back to PIL Image
            result_image = Image.open(io.BytesIO(output))
            
            logger.info(f"Background removed successfully using model: {model}")
            return result_image
            
        except Exception as e:
            logger.error(f"Error removing background: {e}")
            raise

# Initialize background remover
bg_remover = BackgroundRemover()

def validate_image(file_data: bytes) -> Tuple[bool, str]:
    """Validate uploaded image file"""
    try:
        # Check file size
        if len(file_data) > MAX_FILE_SIZE:
            return False, f"File size exceeds maximum limit of {MAX_FILE_SIZE/1024/1024:.1f}MB"
        
        # Try to open image with PIL
        image = Image.open(io.BytesIO(file_data))
        
        # Check image format
        if image.format.lower() not in ['png', 'jpeg', 'jpg', 'webp', 'bmp', 'tiff']:
            return False, "Unsupported image format"
        
        # Check image dimensions (reasonable limits)
        if image.width > 4000 or image.height > 4000:
            return False, "Image dimensions too large (max 4000x4000)"
        
        if image.width < 10 or image.height < 10:
            return False, "Image dimensions too small (min 10x10)"
        
        return True, "Valid image"
        
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"

@app.route('/', methods=['GET'])
def home():
    """API information endpoint"""
    return jsonify({
        "message": "Advanced Background Remover API",
        "version": "1.0.0",
        "endpoints": {
            "/": "API information",
            "/remove-background": "POST - Remove background from image",
            "/models": "GET - List available models",
            "/health": "GET - Health check",
            "/demo": "GET - Demo page"
        },
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": MAX_FILE_SIZE / 1024 / 1024
    })

@app.route('/demo', methods=['GET'])
def demo():
    """Serve the demo page"""
    try:
        with open('demo.html', 'r') as f:
            return f.read(), 200, {'Content-Type': 'text/html'}
    except FileNotFoundError:
        return jsonify({"error": "Demo page not found"}), 404

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Background Remover API is running"
    })

@app.route('/models', methods=['GET'])
def get_models():
    """Get list of available background removal models"""
    return jsonify({
        "models": REMBG_MODELS,
        "default": "u2net",
        "descriptions": {
            "u2net": "General purpose background removal",
            "u2netp": "Lightweight version of u2net",
            "u2net_human_seg": "Optimized for human subjects",
            "u2net_cloth_seg": "Optimized for clothing items",
            "isnet-general-use": "High accuracy general use model"
        }
    })

@app.route('/remove-background', methods=['POST', 'OPTIONS'])
def remove_background():
    """Remove background from uploaded image"""
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    try:
        # Check if file is present
        if 'image' not in request.files and 'image_data' not in request.form:
            return jsonify({
                "error": "No image provided",
                "message": "Please provide an image file via 'image' parameter or base64 data via 'image_data'"
            }), 400
        
        # Get model parameter
        model = request.form.get('model', 'u2net')
        if model not in REMBG_MODELS:
            return jsonify({
                "error": "Invalid model",
                "message": f"Model must be one of: {REMBG_MODELS}"
            }), 400
        
        # Get output format
        output_format = request.form.get('format', 'png').lower()
        if output_format not in ['png', 'jpg', 'jpeg', 'webp']:
            return jsonify({
                "error": "Invalid output format",
                "message": "Output format must be one of: png, jpg, jpeg, webp"
            }), 400
        
        # Handle file upload or base64 data
        image_data = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
            image_data = file.read()
        elif 'image_data' in request.form:
            try:
                # Decode base64 image data
                base64_data = request.form['image_data']
                if base64_data.startswith('data:image'):
                    # Remove data URL prefix
                    base64_data = base64_data.split(',')[1]
                image_data = base64.b64decode(base64_data)
            except Exception as e:
                return jsonify({
                    "error": "Invalid base64 data",
                    "message": str(e)
                }), 400
        
        # Validate image
        is_valid, message = validate_image(image_data)
        if not is_valid:
            return jsonify({"error": message}), 400
        
        # Load and process image
        input_image = Image.open(io.BytesIO(image_data))
        logger.info(f"Processing image: {input_image.size}, mode: {input_image.mode}")
        
        # Remove background
        result_image = bg_remover.remove_background(input_image, model)
        
        # Prepare output
        output_buffer = io.BytesIO()
        
        # Convert output format
        if output_format in ['jpg', 'jpeg']:
            # JPEG doesn't support transparency, so add white background
            background = Image.new('RGB', result_image.size, (255, 255, 255))
            if result_image.mode == 'RGBA':
                background.paste(result_image, mask=result_image.split()[-1])
                result_image = background
            result_image.save(output_buffer, format='JPEG', quality=95)
            mimetype = 'image/jpeg'
        elif output_format == 'webp':
            result_image.save(output_buffer, format='WEBP', quality=95)
            mimetype = 'image/webp'
        else:  # PNG (default)
            result_image.save(output_buffer, format='PNG')
            mimetype = 'image/png'
        
        output_buffer.seek(0)
        
        # Check if client wants base64 response
        if request.form.get('return_base64', '').lower() == 'true':
            base64_data = base64.b64encode(output_buffer.getvalue()).decode()
            return jsonify({
                "success": True,
                "image_data": f"data:{mimetype};base64,{base64_data}",
                "format": output_format,
                "model_used": model,
                "original_size": list(input_image.size),
                "output_size": list(result_image.size)
            })
        
        # Return file directly
        return send_file(
            output_buffer,
            mimetype=mimetype,
            as_attachment=True,
            download_name=f"background_removed.{output_format}"
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({
            "error": "Processing failed",
            "message": str(e)
        }), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error"""
    return jsonify({
        "error": "File too large",
        "message": f"Maximum file size is {MAX_FILE_SIZE/1024/1024:.1f}MB"
    }), 413

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors"""
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Background Remover API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)