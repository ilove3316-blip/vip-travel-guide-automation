from datetime import datetime

def format_pickup_info(flight_dt, pickup_service, pickup_location=None):
    """
    Formats the pickup information based on the service option.
    - pickup_service: '유' or '무'
    """
    if pickup_service == '유' and pickup_location:
         # logic: 4 hours before flight
        pickup_dt = flight_dt.replace(hour=flight_dt.hour - 4) # Simple subtract, better to use timedelta in real logic if crossing date
        # (Assuming the logical layer passes a valid datetime object, or simple hour math for now)
        # Actually passed as strings usually in this specific template function, let's assume we handle text generation mainly.
        # But if we need calculation, we should do it before.
        # Let's placeholder this: "Calculated externally" or passed as arg.
        
        # User format: (차량 서비스 유: [픽업시간] [픽업장소] 출발합니다...)
        # We will assume 'pickup_time_str' is passed or calculated in the calling function.
        pass
    return "" 
    # Logic moved to main render function for cohesion

def render_travel_guide(user_inputs, scraped_data):
    """
    Renders the Korean travel guide based on user inputs and scraped data.
    
    user_inputs: {
        "url": str,
        "pickup_service": "유" / "무",
        "pickup_location": str (optional),
        "pickup_time": str (optional, if calculated),
        "manager_name": str,
        "room_count": int
    }
    
    scraped_data: JSON object from Gemini
    """
    
    # 1. Prepare Data Handling (Fallbacks)
    data = scraped_data if scraped_data else {}
    
    tour_title = data.get("tour_title", "[상품명]")
    
    # Flight Dep
    f_dep = data.get("flight_dep", {})
    dep_str = f"{f_dep.get('flight_num', '')} {f_dep.get('date', '')} {f_dep.get('time', '')} -> {f_dep.get('arrival_time', '')}"
    
    # Flight Arr
    f_arr = data.get("flight_arr", {})
    arr_str = f"{f_arr.get('flight_num', '')} {f_arr.get('date', '')} {f_arr.get('time', '')} -> {f_arr.get('arrival_time', '')}"

    # Meeting Info logic
    meeting_info = data.get("meeting_info", "공항 미팅 정보 없음")
    
    # Pickup Logic append
    pickup_text = ""
    if user_inputs.get("pickup_service") == '유':
        pickup_time = user_inputs.get("pickup_time", "[시간미정]")
        pickup_loc = user_inputs.get("pickup_location", "[장소미정]")
        pickup_text = f"\n★ {pickup_time} {pickup_loc} 출발합니다. 출발장소 한곳 정해주면 차량 배차하도록 하겠습니다."
    
    # Special Notes logic
    notes_list = data.get("special_notes", [])
    if isinstance(notes_list, list):
        notes_str = "\n".join([f"- {note}" for note in notes_list])
    else:
        notes_str = str(notes_list)

    # Room count for tipping calculation (User input)
    room_count = user_inputs.get("room_count", 1)
    
    # Template
    template = f"""안녕하십니까.
여행 준비사항 송부하여 드립니다.
불편함 없는 여행이 될 수 있도록 꼼꼼히 확인 후 준비하기 바랍니다.

▶ [출발일] {tour_title}
: {user_inputs.get('url', '')}

① 공항미팅 : {meeting_info}{pickup_text}

② 항공 : {f_dep.get('flight_num', '항공사이름')}
-출발 : {dep_str}
-도착 : {arr_str}
※ 항공권 발권 후 여행사에서 보내드립니다. 
※ 발권 후 항공사 홈페이지에서 출발 48시간 전부터 체크인하고 좌석 배정 받으면 됩니다.

③ 숙소 : {data.get('hotel_info', '호텔 정보 확인 필요')}
④ 미팅보드 : {data.get('agency', '여행사')}
⑤ 버스 : [버스정보 확인필요]
⑥ 날씨 : {data.get('weather_info', '날씨 정보')}
※ 더울 날씨이나 버스 김서림 방지를 위해 에어컨을 틀어 추울 수 있으니 추위를 타는 분들은 얇은 긴팔옷을 준비하시기 바랍니다.
⑦ 환전 : {data.get('currency', '환전 정보')}
⑧ 전압 : {data.get('voltage', '전압 정보')}
⑨ 시차 : [시차정보]
⑩ 팁 : {data.get('tips_info', '팁 정보')}
⑪ 음식 : 소주, 라면, 김, 밑반찬 등 준비
⑫ 쇼핑 : {data.get('shopping_info', '쇼핑 정보')}
⑬ 비자 : {data.get('visa_info', '비자 정보')}
⑭ 수하물 : {data.get('luggage_info', '수하물 정보')}
  ※ 휴대폰 베터리, 전자담배, 라이터, 리튬 배터리 전자 제품 등은 수하물이 아닌 기내 휴대를 해야 합니다.
⑮ 상비약 : 감기약, 해열제, 소화제, 지사제, 멀미약, 두통약, 밴드, 변비약 등
⑯ 특이사항 :
{notes_str}

★ 입국 준비 사항
[국가별 규정 확인 필요]
"""
    return template
