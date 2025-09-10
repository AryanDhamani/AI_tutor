"""
Configuration module for the AI Tutor backend.
Centralizes all environment variable management.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration from environment variables."""
    
    # Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # CORS Configuration  
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
    
    # Manim Rendering Configuration
    MANIM_QUALITY: str = os.getenv("MANIM_QUALITY", "L")  # L, M, or H
    RENDER_TIMEOUT_SEC: int = int(os.getenv("RENDER_TIMEOUT_SEC", "180"))
    
    # Optional: Data Directory
    DATA_DIR: Optional[str] = os.getenv("DATA_DIR")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Development Settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required configuration is present."""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required but not set")
        
        if cls.MANIM_QUALITY not in ["L", "M", "H"]:
            raise ValueError("MANIM_QUALITY must be L, M, or H")
            
        if cls.RENDER_TIMEOUT_SEC <= 0:
            raise ValueError("RENDER_TIMEOUT_SEC must be positive")
            
        return True

# Global config instance
config = Config()

