#!/usr/bin/env python3
"""
Simple script to run the AI Tutor backend server.
Usage: python run_server.py
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app
import uvicorn
from app.config import config

if __name__ == "__main__":
    print("Starting AI Tutor Backend Server...")
    try:
        uvicorn.run(
            app,
            host=config.HOST,
            port=config.PORT,
            reload=config.DEBUG,
            log_level=config.LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

