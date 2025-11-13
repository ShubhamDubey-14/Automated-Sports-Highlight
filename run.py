#!/usr/bin/env python3
"""
Sports Highlights Generator - Startup Script
Run this script to start the backend server
"""

import subprocess
import sys
import os
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import flask
        import cv2
        import numpy
        import librosa
        import moviepy
        import scipy
        import sklearn
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ['uploads', 'outputs']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print("✅ Directories created")

def start_server():
    """Start the Flask server"""
    print("🚀 Starting Sports Highlights Generator...")
    print("📡 Backend server will run on: http://localhost:5000")
    print("🌐 Frontend will be available at: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Start Flask server
        subprocess.run([sys.executable, "app.py"])
    except KeyboardInterrupt:
        print("\n👋 Server stopped. Goodbye!")

def main():
    print("🏆 Sports Highlights Generator")
    print("=" * 40)
    
    # Check requirements
    if not check_requirements():
        return
    
    # Create directories
    create_directories()
    
    # Start server
    start_server()

if __name__ == "__main__":
    main()
