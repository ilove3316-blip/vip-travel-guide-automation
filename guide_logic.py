from datetime import datetime, timedelta

def calculate_pickup_time(flight_dt):
    """
    Calculates the pickup time based on the flight departure time.
    Rule: 4 hours before flight time.
    """
    return flight_dt - timedelta(hours=4)

def generate_pickup_section(is_provided, flight_dt, location):
    """
    Generates the text section for airport pickup service matching the specific user template.
    """
    if not is_provided:
        return ""

    pickup_dt = calculate_pickup_time(flight_dt)
    pickup_time_str = pickup_dt.strftime("%m월 %d일 %H:%M")
    
    # Fallback if location not provided
    final_loc = location if location and location.strip() else "[고객 요청 장소]"

    return f"""
인천공항 왕복 의전: 저희 VIP 여행센터는 고객님의 편안한 시작을 위해 인천공항 왕복 프리미엄 밴 서비스를 무상으로 제공해 드리고 있습니다.
픽업 안내: {pickup_time_str}에 고객님께서 지정하신 {final_loc}에서 기사가 대기합니다.
Note: 출발 장소는 자택, 회사 등 고객님께서 원하시는 곳으로 담당자에게 사전에 말씀해 주시면 배차에 반영됩니다.
"""

def generate_full_guide(manager_name, flight_date, tour_title, tour_url, room_count, pickup_section_text, scraped_data):
    """
    Assembles the full travel guide text using the USER'S exact template.
    """
    data = scraped_data if scraped_data else {}
    

    # Parse extracted date for display if specific format is found
    # If the flight_date argument was a dummy, we might need to parse extracted date.
    # However, for this function, we will respect the input argument as the primary, 
    # IF the caller passes a real date. If caller removed the input, app.py must pass the extracted date.
    
    formatted_date = flight_date.strftime('%Y년 %m월 %d일 (%a)')
    
    # Extract Data
    flight_dep = data.get('flight_dep', {})
    flight_arr = data.get('flight_arr', {})
    
    # helper for clean flight string
    def fmt_flight(f_data):
        if not f_data or not f_data.get('flight_num'):
            return "항공편 정보 확인 필요 ✈️"
            
        # Data validation to prevent placeholders like YYYY.MM.DD
        d = f_data.get('date', '')
        if "YYYY" in d or "확인" in d:
             return "항공편 정보 AI 추출 실패 (일정표 확인 필요) ✈️"
             
        return f"{f_data.get('date','')} {f_data.get('time','')} 출발 → {f_data.get('arrival_date','')} {f_data.get('arrival_time','')} 도착 ({f_data.get('flight_num','')})"

    dep_str = fmt_flight(flight_dep)
    arr_str = fmt_flight(flight_arr)
    
    agency_name = data.get('agency_name', '여행사')
    
    # Formatting Special Notes
    # Formatting Special Notes
    raw_notes = data.get('special_notes', [])
    if isinstance(raw_notes, list):
        # Filter out unwanted notes
        filtered_notes = []
        for n in raw_notes:
            if "유류할증료" in n or "1인 객실" in n:
                continue
            filtered_notes.append(n)
        if not filtered_notes:
            notes_str = "특이사항 없음"
        else:
            notes_str = "\n".join([f"• {n}" for n in filtered_notes])
    else:
        # String case check
        if "유류할증료" in raw_notes or "1인 객실" in raw_notes:
             notes_str = "특이사항 없음"
        else:
            notes_str = f"• {raw_notes}"

    # Visual Separators
    HR = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Template
    template = f"""
[VIP 여행센터] 고객님만을 위한 글로벌 여정 마스터 가이드 (Package Plus)

안녕하십니까. {manager_name}입니다.
여행 관련 준비사항 등을 송부하여 드리니, 만족할 수 있는 여행이 될 수 있도록 꼼꼼히 확인 후 준비해 주시기 바랍니다^^

{HR}

# 1️⃣ 여정 개요 (Trip Overview)
🚩 출발 일자: {formatted_date}
🗺️ 여행 테마: {tour_title}
⏱️ 시차 정보: {data.get('timezone_diff', '현지 시차 확인 필요')}
🔗 디지털 일정표: {tour_url}

> Tip: 일정표 내의 호텔명이나 식당명을 클릭하시면 구글 맵과 연동되어 실시간 위치 및 주변 정보를 확인하실 수 있습니다.

{HR}

# 2️⃣ 항공 및 공항 서비스 (Aviation & Concierge)
🛫 출발편 (Departure):
{dep_str}

🛬 귀국편 (Return):
{arr_str}

💺 좌석 및 체크인: 
항공권 발권 후 고객님께 가장 먼저 문자 및 카톡으로 공지가 됩니다. 
원하시는 좌석 배정을 위해 발권 안내를 받으시는 즉시 개별적으로 좌석 지정을 진행해 주시기 바랍니다.

🔗 항공사별 체크인 안내: 
저희 VIP 여행센터에서 운영하는 블로그를 통해 대한항공 체크인 및 수하물 정보를 상세히 확인하실 수 있습니다. (URL: https://blog.naver.com/myevertour/223721451477)

👋 공항 VIP 의전 (Meet & Greet):
미팅 장소: 인천공항 미팅 장소 도착 후 [{agency_name}] 피켓을 찾아주세요.
Fast-track: 전용 통로를 통해 입국 심사를 신속히 마치고, 수하물 수취 후 전용 차량까지 에스코트해 드립니다.
{pickup_section_text}

{HR}

# 3️⃣ 가이드/기사 경비 및 매너팁 (Tipping Etiquette)
단체 여행의 품격을 유지하기 위한 팁 가이드라인입니다.

💵 가이드/기사 경비 (Official Type): 
{data.get('tips_info', '📌 상품 포함/불포함 여부를 일정표에서 꼭 확인해주세요.')}
(현지에서 지불하시거나, 상품가에 이미 포함되어 있을 수 있습니다.)

🛌 호텔 매너팁 (Etiquette):
포터 (짐 운반): 가방 1개당 $1~2
하우스키핑 (객실 청소): 1박당 $1~2 (총 {room_count}개 객실 기준)

{HR}

# 4️⃣ 현지 통신 및 필수 준비 (Connectivity & Prep)
📱 데이터 통신:
해외 로밍 (추천): 한국 번호 그대로 사용, 통신사 앱에서 신청.
이심 (eSIM): 유심 교체 없이 QR 스캔 (최신 기종).
와이파이 도시락: 일행 공유용, 충전 및 휴대 필요.

🔌 전압 및 어댑터:
{data.get('voltage', '멀티어댑터 준비를 권장합니다.')}

💶 환전 가이드:
{data.get('currency', '현지 통화 환전 필요')}
(유럽연합 유로(EUR) 사용. 소액권 현금 및 해외 사용 가능한 신용카드 준비 외에, 수수료가 적은 트래블 카드나 현지 결제 환경에 최적화된 모바일 페이 정보를 미리 확인해 주시면 더욱 편리합니다.)

{HR}

# 5️⃣ 짐 꾸리기 및 수하물 (Luggage & Packing)
🧳 위탁 수하물:
{data.get('luggage_info', '1인당 23kg (이용하시는 항공사 규정을 꼭 확인하세요)')}

🚫 주의사항:
보조배터리, 라이터, 전자담배는 반드시 기내 휴대 가방에 넣으셔야 합니다.

🧠 스마트 짐싸기 Tip:
옷은 지퍼백/압축백에 나누어 담으시면 부피가 줄어듭니다.
여권 사본과 항공권 이미지는 휴대폰에 별도 저장해 두세요.

{HR}

# 6️⃣ 국가별 규정 및 꿀팁 (Compliance & Tips)
🛂 입국 서류 및 비자:
{data.get('visa_info', '방문국 비자 필요 여부 확인')}

☁️ 현지 날씨:
{data.get('weather_info', '평균 기온 및 강수 정보 확인')}

👗 드레스 코드:
관광 시: 편안한 워킹슈즈, 겹쳐 입을 얇은 옷.
정찬/행사: 일부 레스토랑은 스마트 캐주얼 권장.

💡 VIP 여행 꿀팁:
{data.get('pro_tips', '현지 문화를 존중하는 매너있는 여행 되세요.')}

🏥 안전 및 건강:
비상약(소화제, 진통제, 개인 처방약)은 넉넉히 준비해 주세요.
포함 보험: {data.get('insurance_info', '여행자 보험 가입 여부 확인')}

{HR}

⚠️ 특별 유의사항 (Special Notes)
{notes_str}

본 맞춤형 안내문은 고객님의 편의를 위해 온라인 링크 형태로 제공되며, 휴대폰이나 PC로 언제든 쉽게 확인하실 수 있습니다.

행복하고 특별한 여행 되시길 바랍니다.
- VIP여행센터 드림 -
"""
    return template
    return template
