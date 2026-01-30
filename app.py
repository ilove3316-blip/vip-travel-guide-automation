import streamlit as st
from datetime import datetime, time
import guide_logic
import scraper_llm

# ---------------------------------------------------------
# 페이지 설정 및 디자인
# ---------------------------------------------------------
st.set_page_config(
    page_title="VIP Global Journey Guide Generator",
    page_icon="✈️",
    layout="centered"
)

# UI 직관성을 높이기 위한 커스텀 CSS 적용
st.markdown("""
    <style>
   .main-header {
        font-size: 2.2rem;
        color: #0f4c81; /* Classic Blue for Trust */
        font-weight: 700;
        text-align: center;
        margin-bottom: 25px;
    }
   .section-header {
        color: #333333;
        font-weight: 600;
        margin-top: 20px;
        margin-bottom: 10px;
    }
   .info-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #0f4c81;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# [Header] 타이틀 및 개요
# ---------------------------------------------------------
st.markdown('<div class="main-header">VIP Journey Master Guide Generator</div>', unsafe_allow_html=True)
st.markdown("""
이 시스템은 **VIP 여행센터 전용 안내문 자동 생성 도구**입니다.
아래 4가지 핵심 정보를 입력하면, 고객 맞춤형 가이드가 즉시 생성됩니다.

**Tip:** 최신 여행사 사이트(하나투어 등)는 보안 문제로 자동 읽기가 어려울 수 있습니다. **일정표 스크린샷**을 업로드하면 정확도가 획기적으로 높아집니다.
""")
st.divider()

# ---------------------------------------------------------
# 사용자 입력 폼
# ---------------------------------------------------------
with st.form("guide_input_form"):
    st.markdown('<div class="section-header">1. 기본 정보 입력</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)

    with col1:
        manager_name = st.text_input("담당자 이름/직함", placeholder="예: 김이름 팀장")
        # flight_date input removed as per user request
    with col2:
        tour_url = st.text_input("여행 일정표 URL", placeholder="https://...")
        room_count = st.number_input("객실 수 (Room Count)", min_value=1, value=1, help="호텔 매너팁 계산에 사용됩니다.")

    st.markdown('<div class="section-header">2. 여행 일정표(스크린샷) 업로드 (권장 📸)</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("URL만으로 내용이 안 나올 경우, 일정표 화면을 캡쳐해서 올려주세요. (PDF 지원)", type=['png', 'jpg', 'jpeg', 'pdf'])

    st.markdown('<div class="section-header">3. 차량 서비스 설정 (Incheon Airport Service)</div>', unsafe_allow_html=True)
    
    # 차량 서비스 유무 선택
    pickup_service_option = st.radio(
        "인천공항 왕복 차량 서비스 제공 여부",
        ('제공함 (유)', '제공 안 함 (무)'),
        index=0,
        horizontal=True
    )

    # 조건부 입력을 위한 안내
    st.info("💡 '제공함' 선택 시, 아래 비행시간을 기준으로 픽업 시간이 자동 계산(-4시간)됩니다.")

    col3, col4 = st.columns(2)
    with col3:
        flight_time_input = st.time_input("비행기 출발 시간 (24h)", time(10, 0))
    with col4:
        pickup_location_input = st.text_input("픽업 장소 (고객 요청지)", placeholder="예: 강남구 도곡동 타워팰리스 정문")

    # 제출 버튼
    submit_button = st.form_submit_button("✨ 안내문 생성하기 (Generate Guide)")

# ---------------------------------------------------------
# 데이터 처리 및 텍스트 생성
# ---------------------------------------------------------
if submit_button:
    # 0. 데이터 추출 (URL or Image)
    with st.spinner("AI가 여행 정보를 분석 중입니다... (약 10~20초 소요)"):
        top_image_bytes = uploaded_file.getvalue() if uploaded_file else None
        
        # Call Scraper logic
        scraped_data = scraper_llm.analyze_content(
            url=tour_url,
            image_bytes=top_image_bytes,
            mime_type=uploaded_file.type if uploaded_file else "image/jpeg"
        )
        
        if "error" in scraped_data:
            st.warning(f"데이터 분석 중 경고가 발생했습니다: {scraped_data['error']}")
            # But proceed with empty data if needed
    
    # 1. 날짜 파싱 (Extracted from LLM)
    extracted_date_str = scraped_data.get('flight_dep', {}).get('date', '')
    flight_date_obj = datetime.now() # Default
    
    if extracted_date_str:
        import re
        # Regex to find YYYY.MM.DD or YYYY-MM-DD
        match = re.search(r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})', str(extracted_date_str))
        if match:
            try:
                year, month, day = map(int, match.groups())
                flight_date_obj = datetime(year, month, day)
            except ValueError:
                 st.warning(f"날짜 형식이 올바르지 않아 오늘 날짜로 대체합니다. ({extracted_date_str})")
        else:
             st.warning(f"날짜 형식이 인식되지 않아 오늘 날짜로 대체합니다. ({extracted_date_str})")
    
    # 2. 픽업 섹션 생성
    is_pickup_provided = (pickup_service_option == '제공함 (유)')
    
    # Try to combine parsed date + user input time
    flight_dt = datetime.combine(flight_date_obj.date(), flight_time_input)
    
    pickup_section_text = guide_logic.generate_pickup_section(
        is_pickup_provided, 
        flight_dt, 
        pickup_location_input
    )

    # 3. 전체 안내문 생성
    # Map scraped data to variables
    # Priority: Scraped Title -> URL -> Default
    tour_title = scraped_data.get('tour_title', '여행 제목 (일정표 확인 필요)')
    
    full_guide_text = guide_logic.generate_full_guide(
        manager_name, 
        flight_date_obj,  # Pass result object
        tour_title,
        tour_url, 
        room_count, 
        pickup_section_text,
        scraped_data
    )


    # 3. 결과 출력
    st.success("✅ 고객 맞춤형 안내문 생성이 완료되었습니다!")
    
    st.subheader("📄 생성된 안내문 (복사하여 사용)")
    st.text_area("아래 내용을 전체 선택(Ctrl+A) 후 복사(Ctrl+C)하여 카카오톡이나 메일로 발송하세요.", full_guide_text, height=600)
    
    st.divider()
    st.markdown('<div class="section-header">🌐 고객 전달용 HTML 파일 생성</div>', unsafe_allow_html=True)
    st.info("아래 버튼을 누르면 고객에게 전달할 수 있는 HTML 파일이 생성됩니다. 이 파일을 웹 서버에 올리거나 파일 자체를 전달하세요.")
    
    # Simple HTML Wrapper
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{tour_title} - 여행 준비사항</title>
        <style>
            body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; background-color: #f9f9f9; }}
            .container {{ background-color: #ffffff; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h1 {{ color: #0f4c81; border-bottom: 2px solid #0f4c81; padding-bottom: 10px; }}
            h2 {{ color: #333; margin-top: 30px; border-left: 5px solid #0f4c81; padding-left: 10px; }}
            pre {{ white-space: pre-wrap; font-family: inherit; background: transparent; border: none; }}
            .footer {{ margin-top: 40px; text-align: center; font-size: 0.8em; color: #777; }}
            .btn {{ display: inline-block; padding: 10px 20px; background-color: #0f4c81; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <pre>{full_guide_text}</pre>
            <div style="text-align: center; margin-top: 30px;">
                <a href="{tour_url}" class="btn" target="_blank">📅 일정표 보러가기</a>
            </div>
        </div>
        <div class="footer">
            VIP 여행센터 | Global Journey Master
        </div>
    </body>
    </html>
    """
    
    # Download Button
    st.download_button(
        label="📥 HTML 파일 다운로드 (고객 전달용)",
        data=html_content,
        file_name="travel_guide.html",
        mime="text/html"
    )
    
else:
    st.info("👈 왼쪽 정보를 입력하고 '생성하기' 버튼을 눌러주세요.")
