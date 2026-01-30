import os
import json
import time
import sys
# Force UTF-8 encoding for stdout to verify logs in Windows terminals
sys.stdout.reconfigure(encoding='utf-8')
from google import genai
from google.genai import types
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import Optional

# Load environment variables
load_dotenv()

# Configure Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("CRITICAL: GEMINI_API_KEY is missing from .env file.")

# genai.configure(api_key=API_KEY) # Removed for new SDK

def capture_screenshot_with_selenium(url: str) -> Optional[bytes]:
    """
    Captures a full-page screenshot using Selenium (Chrome).
    Handles 'blinding' content by rendering javascript.
    """
    print(f"[Selenium] Accessing URL via automated browser (Selenium): {url}")
    
    # Configure Chrome Options
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Modern headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1280,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    try:
        # Initialize Driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        # Wait for lazy loading (simulate scroll)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2) 
        driver.execute_script("window.scrollTo(0, 0);") # Scroll back up
        time.sleep(1)
        
        # Take Screenshot
        # Selenium returns bytes directly, let's grab it
        png_data = driver.get_screenshot_as_png()
        
        print("[Success] Screenshot captured successfully.")
        return png_data
        
    except Exception as e:
        print(f"[Error] Error capturing screenshot: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def analyze_content(url=None, image_bytes=None, mime_type="image/jpeg"):
    """
    Analyzes content.
    1. If user uploads an image, use it.
    2. If user provides a URL, AUTO-CAPTURE a screenshot using Selenium, then use that.
    """
    client = genai.Client(api_key=API_KEY)
    
    content_parts = []
    
    # Validation
    if not url and not image_bytes:
        return {"error": "URL이나 이미지를 입력해주세요."}

    # 1. Image Logic (User Uploaded)
    if image_bytes:
        print("Processing User Uploaded Image...")
        content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
        content_parts.append("This is a screenshot of a travel itinerary provided by the user.")

    # 2. URL Logic (Auto-Screenshot)
    elif url:
        print(f"Processing URL with Auto-Screenshot: {url}")
        
        # 🚀 Capture Screenshot automatically
        auto_screenshot = capture_screenshot_with_selenium(url)
        
        if auto_screenshot:
            content_parts.append(types.Part.from_bytes(data=auto_screenshot, mime_type="image/png"))
            content_parts.append(f"This is a screenshot of the web page at {url}. Analyze the visual content directly. Resolve any blinded text.")
        else:
            return {"error": "자동 스크린샷 캡처에 실패했습니다. (보안 설정이 강화된 사이트일 수 있습니다. 직접 스크린샷을 찍어서 업로드해주세요.)"}

    # Prompt Engineering (Updated for Visual Analysis)
    prompt = """
    You are a professional travel agent assistant.
    Analyze the provided travel itinerary image (screenshot) or PDF document and extract the following information into a strict JSON format.
    
    Target JSON Structure:
    {
      "tour_title": "String (Product Name, e.g., '서유럽 3국 9일')",
      "agency_name": "String (Agency Name, e.g., '하나투어')",
      "flight_dep": {
        "date": "2026.05.14", 
        "time": "12:20", 
        "flight_num": "String (e.g., KE901)", 
        "arrival_date": "2026.05.14",
        "arrival_time": "15:00"
      },
      "flight_arr": {
        "date": "2026.05.19", 
        "time": "16:00", 
        "flight_num": "String (e.g., KE902)", 
        "arrival_date": "2026.05.19",
        "arrival_time": "19:55"
      },
      "meeting_info": "String (Specific meeting time/place. If not found, imply '출발 3시간 전 공항 미팅')",
      "hotel_info": "String (e.g., '호텔 이름')",
      "weather_info": "String (Predict AVERAGE weather for the destination/month)",
      "currency": "String (Currency name & recommendation)",
      "voltage": "String (e.g., '멀티어댑터 필수')",
      "tips_info": "String (Look for included/excluded listing. e.g., '가이드 경비 1인 40달러 현지 지불')",
      "shopping_info": "String (e.g., '쇼핑 3회')",
      "visa_info": "String (Entry requirements)",
      "luggage_info": "String (Weight limits)",
      "airline_checkin_url": "String (Airline URL)",
      "timezone_diff": "String (Time difference)",
      "pro_tips": "String (Travel tips)",
      "special_notes": ["String (Critical warnings)"]
    }

    Directives:
    - **CRITICAL**: The image is a long travel itinerary. You MUST look at the ENTIRE image.
    - **TIPPING/COSTS**: Look specifically for a section named '여행상품 핵심정보', '포함사항/불포함사항', or '참고사항'. Find the "가이드/기사 경비" (Guide/Driver Fee) - it is often a specific amount like '100유로' or '100달러'. It is almost ALWAYS in the text. Do not return 'Check URL' unless truly invisible.
    - **FLIGHTS**: Look for '항공 스케줄' or '교통편'. Flight numbers look like 'KE901', 'OZ501'. Times are 'HH:MM'.
    - **VISUAL PROCESSING**: The information might be in a tabular format (grid). Read rows/columns carefully.
    - If the date is 2026, ensure you extract it correctly.
    - Return ONLY valid JSON.
    """

    # Retry logic for Rate Limiting (429 Resource Exhausted)
    max_retries = 5
    base_delay = 10  # seconds

    # Explicitly set model to a stable version
    model_name = 'gemini-flash-latest' 

    import datetime

    for attempt in range(max_retries):
        try:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Sending request to Gemini ({model_name})...")
            response = client.models.generate_content(
                model=model_name,
                contents=[prompt] + content_parts
            )
            
            # Parse JSON
            result_text = response.text.strip()
            # Clean possible markdown block
            if result_text.startswith("```"):
                lines = result_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                result_text = "\n".join(lines).strip()
                
            return json.loads(result_text)
            
        except Exception as e:
            error_str = str(e)
            current_time = datetime.datetime.now().strftime('%H:%M:%S')
            print(f"[{current_time}] [Warning] Gemini API Error (Attempt {attempt + 1}/{max_retries}): {e}")
            
            # Check for Rate Limit (429)
            if "429" in error_str or "Resource has been exhausted" in error_str:
                if attempt < max_retries - 1:
                    wait_time = base_delay * (2 ** attempt)  # 10, 20, 40...
                    print(f"[{current_time}] [Wait] Rate limit hit. Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                     return {"error": f"API 할당량 초과로 인해 {max_retries}회 재시도 후에도 실패했습니다. 잠시 후(몇 분 뒤) 다시 시도해주세요. (Error: {e})"}
            else:
                # Non-retriable error
                return {"error": f"Non-retriable error: {str(e)}"}

if __name__ == "__main__":
    # Test logic
    test_url = "https://www.modetour.com/package/98949020?MLoc=99&Pnum=98949020&Sno=C112564&ANO=1221281&thru=crs"
    print(f"Testing auto-screenshot for: {test_url}")
    result = analyze_content(url=test_url)
    print(json.dumps(result, indent=2, ensure_ascii=False))
