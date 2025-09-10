#!/usr/bin/env python3
"""
Test script to validate Gemini API key configuration.
"""
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def test_api_key():
    """Test if the Gemini API key is working."""
    print("🔍 Testing Gemini API Key Configuration...")
    print("=" * 50)
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Get API key
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            print("❌ ERROR: GEMINI_API_KEY not found in environment variables")
            print("💡 Make sure you have a .env file with GEMINI_API_KEY=your_actual_key")
            return False
        
        if api_key == "your_gemini_api_key_here":
            print("❌ ERROR: GEMINI_API_KEY is still set to placeholder value")
            print("💡 Please update your .env file with your actual Gemini API key")
            print("📝 Get your API key from: https://aistudio.google.com/app/apikey")
            return False
        
        print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}")
        
        # Test API connection
        print("\n🌐 Testing Gemini API connection...")
        
        import google.generativeai as genai
        
        # Configure the API
        genai.configure(api_key=api_key)
        
        # Test with a simple request
        model = genai.GenerativeModel('gemini-pro')
        
        print("📡 Sending test request to Gemini API...")
        test_prompt = "Say 'Hello from Gemini!' and nothing else."
        
        response = model.generate_content(test_prompt)
        
        if response and response.text:
            print(f"✅ API Response: {response.text.strip()}")
            print("\n🎉 SUCCESS: Gemini API key is working correctly!")
            
            # Test with a more complex request
            print("\n🧪 Testing with educational content generation...")
            edu_prompt = "Explain what 2+2 equals in exactly one sentence."
            edu_response = model.generate_content(edu_prompt)
            
            if edu_response and edu_response.text:
                print(f"✅ Educational Response: {edu_response.text.strip()}")
                print("\n🎓 SUCCESS: API is ready for educational content generation!")
                return True
            else:
                print("⚠️  WARNING: API responded but educational test failed")
                return False
        else:
            print("❌ ERROR: API responded but no content received")
            return False
            
    except ImportError as e:
        print(f"❌ ERROR: Missing required package: {e}")
        print("💡 Run: pip install google-generativeai python-dotenv")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: API test failed: {e}")
        
        # Provide specific error guidance
        error_str = str(e).lower()
        if "api_key" in error_str or "authentication" in error_str:
            print("💡 This looks like an API key issue. Please check:")
            print("   1. Your API key is correct")
            print("   2. Your API key has the necessary permissions")
            print("   3. Your API key hasn't expired")
            print("   4. Get a new key from: https://aistudio.google.com/app/apikey")
        elif "quota" in error_str or "limit" in error_str:
            print("💡 This looks like a quota/rate limit issue:")
            print("   1. You may have exceeded your API quota")
            print("   2. Wait a moment and try again")
            print("   3. Check your quota at: https://aistudio.google.com/app/apikey")
        elif "network" in error_str or "connection" in error_str:
            print("💡 This looks like a network issue:")
            print("   1. Check your internet connection")
            print("   2. Try again in a moment")
        
        return False

def show_env_status():
    """Show current environment file status."""
    print("\n📁 Environment File Status:")
    print("=" * 30)
    
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file exists")
        with open(env_file, 'r') as f:
            content = f.read()
            if "GEMINI_API_KEY=" in content:
                # Extract just the line with the API key
                for line in content.split('\n'):
                    if line.startswith('GEMINI_API_KEY='):
                        key_value = line.split('=', 1)[1]
                        if key_value == "your_gemini_api_key_here":
                            print("⚠️  API key is still set to placeholder")
                        elif len(key_value) > 10:
                            print(f"✅ API key configured: {key_value[:10]}...{key_value[-4:]}")
                        else:
                            print("❌ API key appears to be too short")
                        break
            else:
                print("❌ GEMINI_API_KEY not found in .env file")
    else:
        print("❌ .env file not found")
        print("💡 Run: cp env.example .env")

if __name__ == "__main__":
    print("🧪 Gemini API Key Validator")
    print("🤖 AI Tutor Backend")
    print("\n")
    
    show_env_status()
    
    # Pause for user to update if needed
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            if "your_gemini_api_key_here" in f.read():
                print("\n" + "="*50)
                print("⚠️  ACTION REQUIRED:")
                print("Please update your .env file with your actual Gemini API key")
                print("1. Open the .env file")
                print("2. Replace 'your_gemini_api_key_here' with your actual API key")
                print("3. Save the file")
                print("4. Run this script again")
                print("="*50)
                sys.exit(1)
    
    print("\n")
    success = test_api_key()
    
    if success:
        print("\n" + "="*50)
        print("🎉 ALL TESTS PASSED!")
        print("Your Gemini API key is working correctly.")
        print("You can now start the AI Tutor backend server.")
        print("="*50)
        sys.exit(0)
    else:
        print("\n" + "="*50)
        print("❌ TESTS FAILED!")
        print("Please fix the issues above and try again.")
        print("="*50)
        sys.exit(1)


