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

import base64
from selenium.webdriver.common.print_page_options import PrintOptions

def capture_pdf_from_url(url: str) -> Optional[bytes]:
    """
    Captures the webpage as a PDF using Selenium (Chrome DevTools).
    This is superior to screenshots because it preserves text data even if fonts are missing.
    """
    print(f"[Selenium] Accessing URL to generate PDF: {url}")
    
    # Configure Chrome Options
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Stealth settings
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Stealth
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        driver.set_page_load_timeout(60) # Increased timeout for PDF rendering
        driver.get(url)
        
        # Explicit wait + interaction to trigger lazy loading
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);") # Top
        time.sleep(2) # Wait for rendering
        
        # Print to PDF
        print_options = PrintOptions()
        print_options.background = True # Include background graphics
        
        pdf_b64 = driver.print_page(print_options)
        
        print("[Success] PDF generated successfully.")
        return base64.b64decode(pdf_b64)
        
    except Exception as e:
        print(f"[Error] Error generating PDF: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def analyze_content(url=None, image_bytes=None, mime_type="image/jpeg"):
    """
    Analyzes content.
    1. If user uploads an image/PDF, use it.
    2. If user provides a URL, AUTO-GENERATE a PDF using Selenium, then use that.
    """
    client = genai.Client(api_key=API_KEY)
    
    content_parts = []
    
    # Validation
    if not url and not image_bytes:
        return {"error": "URL이나 이미지를 입력해주세요."}

    # 1. User Uploaded File
    if image_bytes:
        print(f"Processing User Uploaded File ({mime_type})...")
        content_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
        content_parts.append("This is a travel itinerary document provided by the user.")

    # 2. URL Logic (Auto-PDF)
    elif url:
        print(f"Processing URL with Auto-PDF: {url}")
        
        # 🚀 Generate PDF automatically
        auto_pdf = capture_pdf_from_url(url)
        
        if auto_pdf:
            # Use application/pdf for Gemini
            content_parts.append(types.Part.from_bytes(data=auto_pdf, mime_type="application/pdf"))
            content_parts.append(f"This is a PDF version of the web page at {url}. Analyze the text and layout.")
        else:
            return {"error": "자동 PDF 생성에 실패했습니다. (보안 설정이 강화된 사이트일 수 있습니다. 직접 파일을 업로드해주세요.)"}

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
    - **TIPPING/COSTS (CRITICAL)**: 
        1. First, look for "가이드/기사 경비" under '포함내역' (Included) or '불포함내역' (Excluded).
        2. IF it appears in '포함내역' OR if you see "가이드&기사경비 포함" (or similar) ANYWHERE in the image -> Output: "상품가 포함 (현지 지불 없음)".
        3. IF it appears in '불포함내역' -> Output: "1인 [금액] [통화] (현지 지불)" (e.g. "1인 100유로 현지 지불").
        4. Be careful: Sometimes '가이드/기사' header exists in BOTH sections. Read the text below it carefully.
    - **FLIGHTS**: Look for '항공 스케줄' or '교통편'. Flight numbers look like 'KE901', 'OZ501'. Times are 'HH:MM'.
    - **VISUAL PROCESSING**: The information might be in a tabular format (grid). Read rows/columns carefully.
    - If the date is 2026, ensure you extract it correctly.
    - **DATE FORMAT**: Look for dates like '2026.07.12(일)'. Extract ONLY the numeric part '2026.07.12'.
    - **IMPORTANT**: If the month or day is not found, return empty string "". NEVER return "2026.00.00" or similar placeholders.
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
