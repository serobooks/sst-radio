# -*- coding: utf-8 -*-
import pytest
from fastapi.testclient import TestClient
import sys
import os

# 테스트 대상인 api 패키지를 임포트하기 위해 sys.path에 api 상위 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.index import app

client = TestClient(app)

def test_search_without_query():
    """쿼리 파라미터 q 없이 검색을 요청하면 400 에러를 반환해야 한다."""
    response = client.get("/api/search")
    assert response.status_code == 400
    assert "detail" in response.json()

def test_search_with_query():
    """검색 쿼리가 있는 경우, 200 OK와 함께 검색 결과를 리스트로 반환해야 한다."""
    response = client.get("/api/search?q=국악")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    if len(results) > 0:
        item = results[0]
        assert "video_id" in item
        assert "title" in item
        assert "date" in item
        assert "time" in item
        assert "text" in item

def test_search_no_results():
    """매칭되지 않는 검색어인 경우, 빈 리스트를 반환해야 한다."""
    response = client.get("/api/search?q=존재하지않는검색어임이확실한텍스트")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 0

def test_advice_endpoint():
    """조언 요청 시 200 OK와 함께 조언 문장 객체를 무작위로 하나 반환해야 한다."""
    response = client.get("/api/advice")
    assert response.status_code == 200
    data = response.json()
    assert "episode" in data
    assert "video_id" in data
    assert "text" in data
    assert isinstance(data["text"], str)
    assert len(data["text"]) > 0

def test_search_precision():
    """특정 키워드 검색 시 단일 에피소드의 전체 타임라인이 도배되지 않고 정밀 검색되어야 한다."""
    response = client.get("/api/search?q=국악")
    assert response.status_code == 200
    results = response.json()
    
    # 단일 에피소드가 결과를 도배하는 버그 검증
    episodes_in_results = [item["episode"] for item in results]
    if len(episodes_in_results) > 0:
        from collections import Counter
        count = Counter(episodes_in_results)
        most_common_ep, most_common_count = count.most_common(1)[0]
        # 버그 상태에서는 1회 에피소드의 대사 100여 개가 통째로 출력되어 도배되므로 실패(RED)하게 됨
        assert most_common_count < 30, f"에피소드 {most_common_ep}회가 결과 {most_common_count}건으로 도배되었습니다."

def test_search_no_metadata_noise():
    """검색 결과의 모든 대사 본문에 검색어 키워드가 반드시 포함되어야 하며, 00:00 같은 노이즈 대사가 없어야 한다."""
    response = client.get("/api/search?q=국악")
    assert response.status_code == 200
    results = response.json()
    
    for item in results:
        # 본문(text) 또는 타이틀에 검색어가 직접 들어있는지 검증
        has_query = "국악" in item["text"].lower() or "국악" in item["title"].lower()
        assert has_query, f"에피소드 {item['episode']}회 {item['time']}초 결과 대사에는 검색어 '국악'이 포함되어 있지 않습니다."

def test_search_exact_only():
    """'국악' 검색 시 자동 확장이 배제되어, 연관 단어만 들어간 대사는 포함되지 않아야 한다."""
    response = client.get("/api/search?q=국악")
    assert response.status_code == 200
    results = response.json()
    
    for item in results:
        # 대사 본문에 '국악' 단어 자체가 확실히 존재해야 함
        assert "국악" in item["text"].lower() or "국악" in item["title"].lower()

def test_search_janggu_exception():
    """'장구' 검색 시 '승승장구' 또는 '승승 장구' 멘트가 노이즈로 섞여 나오지 않아야 한다."""
    response = client.get("/api/search?q=장구")
    assert response.status_code == 200
    results = response.json()
    
    for item in results:
        text = item["text"].lower().replace(" ", "")
        # 결과에 '승승장구'가 포함되어 있지 않아야 함
        assert "승승장구" not in text, f"에피소드 {item['episode']}회에 '승승장구' 노이즈 대사가 노출되었습니다: {item['text']}"

def test_search_duplicate_proximity_filtering():
    """검색 API가 window 파라미터를 기반으로 인접 시간대의 동일 검색어 결과를 정상적으로 필터링(중복 제거)하는지 검증한다."""
    # 1. window=300(기본값)으로 요청했을 때 동일 에피소드 내 시간차가 300초 이상이어야 함
    response_filtered = client.get("/api/search?q=다이어트&window=300")
    assert response_filtered.status_code == 200
    results_filtered = response_filtered.json()
    
    # 에피소드별로 시간 간격 검사
    episodes_time_map = {}
    for item in results_filtered:
        ep = item["episode"]
        t = item["time"]
        if ep not in episodes_time_map:
            episodes_time_map[ep] = []
        episodes_time_map[ep].append(t)
        
    for ep, times in episodes_time_map.items():
        # 시간순 정렬
        sorted_times = sorted(times)
        for i in range(len(sorted_times) - 1):
            diff = sorted_times[i+1] - sorted_times[i]
            assert diff > 300, f"에피소드 {ep}회에서 {sorted_times[i]}초와 {sorted_times[i+1]}초 결과 간격이 300초 이하({diff}초)입니다."
            
    # 2. window=0(필터 비활성화)로 요청했을 때의 결과 건수가 window=300(필터 활성화)일 때보다 많아야 함
    response_raw = client.get("/api/search?q=다이어트&window=0")
    assert response_raw.status_code == 200
    results_raw = response_raw.json()
    
    assert len(results_raw) > len(results_filtered), f"필터 비활성화 시 건수({len(results_raw)})가 필터 활성화 시 건수({len(results_filtered)})보다 많지 않습니다."


def test_fortune_cookie_images_exist():
    """신규 포춘쿠키 이미지 파일들이 존재해야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    closed_cookie = os.path.join(public_dir, "fortune_cookie_closed.png")
    open_cookie = os.path.join(public_dir, "fortune_cookie_open.png")
    assert os.path.exists(closed_cookie), "fortune_cookie_closed.png 파일이 존재하지 않습니다."
    assert os.path.exists(open_cookie), "fortune_cookie_open.png 파일이 존재하지 않습니다."


def test_index_html_uses_closed_cookie():
    """index.html에서 닫힌 포춘쿠키를 사용하고, 구버전 단일 포춘쿠키는 사용하지 않아야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # fortune_cookie_closed.png이 포함되어 있는지 확인
    assert "fortune_cookie_closed.png" in html_content, "index.html에 fortune_cookie_closed.png가 사용되지 않았습니다."
    # 구버전 fortune_cookie.png는 없어야 함
    assert "fortune_cookie.png" not in html_content, "index.html에 구버전 fortune_cookie.png가 여전히 남아있습니다."


def test_style_css_light_theme():
    """style.css에 솜사탕 파스텔 라이트 모드를 위한 색상 변수가 올바르게 설정되어야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    css_path = os.path.join(public_dir, "style.css")
    assert os.path.exists(css_path)
    
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
        
    # 파스텔 핑크 서브 컬러(--color-secondary)가 정의되어 있는지 확인
    assert "--color-secondary" in css_content, "style.css에 파스텔 핑크 서브 컬러(--color-secondary)가 정의되지 않았습니다."
    # 라이트모드 솜사탕 배경색(--color-bg) 변수가 정의되어 있는지 확인
    assert "--color-bg" in css_content, "style.css에 배경색(--color-bg) 변수가 정의되지 않았습니다."


def test_logo_text_is_changed():
    """상단 로고 영역에 'DEAR MASTER'가 아닌 '오따신 아카이브'가 적용되어야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert "DEAR MASTER" not in html_content, "여전히 DEAR MASTER 로고 텍스트가 남아있습니다."
    assert "오따신 아카이브" in html_content, "로고 텍스트가 '오따신 아카이브'로 수정되지 않았습니다."


def test_logo_letter_spacing_and_menu_text():
    """style.css의 로고 자간이 2px보다 작아져야 하고, index.html의 메뉴명이 '검색'이어야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    css_path = os.path.join(public_dir, "style.css")
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
        
    # 메뉴명 확인
    assert ">검색 엔진</a>" not in html_content, "메뉴 앵커 태그에 여전히 '검색 엔진'이 존재합니다."
    assert ">검색</a>" in html_content, "메뉴명이 '검색'으로 수정되지 않았습니다."
    
    # 자간 확인 (.logo-text 부분의 letter-spacing이 2px이 아니어야 함)
    assert "letter-spacing: 2px;" not in css_content, "style.css에 여전히 로고 자간 2px이 유지되고 있습니다."


def test_main_title_is_changed():
    """index.html의 메인 타이틀 텍스트가 변경되어야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert "오늘따라 신승태입니다" in html_content, "메인 타이틀에 '오늘따라 신승태입니다'가 존재하지 않습니다."
    assert "스크립트 아카이브" in html_content, "메인 타이틀에 '스크립트 아카이브'가 존재하지 않습니다."
    assert "라디오 타임라인 아카이브" not in html_content, "여전히 구버전 타이틀 '라디오 타임라인 아카이브'가 남아있습니다."


def test_badge_text_is_changed():
    """index.html의 배지 액센트 텍스트가 변경되어야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert "FAN-MADE MEMORY ARCHIVE" in html_content, "배지 텍스트에 'FAN-MADE MEMORY ARCHIVE'가 존재하지 않습니다."
    assert "BTNRADIO OFFICIAL DE덕 ARCHIVE" not in html_content, "여전히 구버전 배지 텍스트 'BTNRADIO OFFICIAL DE덕 ARCHIVE'가 남아있습니다."


def test_hero_desc_is_changed():
    """index.html의 히어로 설명글이 변경되어야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert "BTN라디오에서 목요일 저녁 7시부터 9시까지" in html_content, "설명글에 '매주'가 제거된 방송 정보가 존재하지 않습니다."
    assert "매주 목요일" not in html_content, "여전히 설명글에 '매주 목요일'이 남아있습니다."
    assert "라디오 속 소중한 순간들을 다시 만나보세요." in html_content, "설명글에 다시 만나보세요 권유글이 존재하지 않습니다."
    assert "2년의 여정" not in html_content, "여전히 구버전 설명글 '2년의 여정'이 남아있습니다."
    assert "스크립트를 정리한 웹사이트입니다. 궁금한 키워드" in html_content, "마침표 뒤에 올바른 띄어쓰기가 없거나 여전히 줄바꿈(<br>)이 남아있습니다."


def test_search_placeholder_is_changed():
    """index.html의 검색창 placeholder 텍스트가 변경되어야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert 'placeholder="다시 듣고 싶은 이야기의 키워드를 입력해 보세요(예: 녹음, 경기민요, 선글라스)"' in html_content, "검색창 placeholder가 변경되지 않았습니다."




def test_advice_section_desc_is_changed():
    """index.html의 마도사 조언 코너 설명 문구가 변경되어야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert "오따신의 명물 '야생마도사'의 조언을 담은 포춘쿠키입니다. 포춘쿠키를 터치해" in html_content, "마도사 조언 코너 설명 문구가 변경되지 않았습니다."
    assert "야생맛도사" not in html_content, "여전히 구버전 문구 '야생맛도사'가 남아있습니다."


def test_advice_spacing_and_button_text():
    """index.html, style.css, main.js에서 쿠키 간격 조정 및 '추천 영상 바로가기' 텍스트를 검증해야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    css_path = os.path.join(public_dir, "style.css")
    js_path = os.path.join(public_dir, "main.js")
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()
        
    # index.html 버튼 텍스트 확인
    assert "추천 영상 바로 가기" in html_content, "index.html에 '추천 영상 바로 가기'가 적용되지 않았습니다."
    assert "조언 영상 바로 가기" not in html_content, "index.html에 여전히 '조언 영상 바로 가기'가 남아있습니다."
    
    # main.js 버튼 텍스트 동적 렌더링 확인
    assert "추천 영상 바로 가기" in js_content, "main.js에 '추천 영상 바로 가기'가 적용되지 않았습니다."
    assert "조언 영상 바로 가기" not in js_content, "main.js에 여전히 '조언 영상 바로 가기'가 남아있습니다."
    
    # style.css 간격이 좁혀졌는지 확인
    assert "margin-top: 40px;" not in css_content, "style.css에 여전히 구버전 40px 마진이 적용되어 있어 간격이 넓습니다."
    assert "height: 300px;" in css_content, "style.css에 쿠키 랩퍼 높이가 300px로 정밀 좁혀지지 않았습니다."


def test_footer_contents_and_link():
    """index.html, style.css에서 푸터 텍스트 개편 및 제작자 유튜브 채널 링크 사양을 안전하게 검증해야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    css_path = os.path.join(public_dir, "style.css")
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
        
    # 푸터 텍스트 교체 확인
    assert "All Rights Reserved" in html_content, "푸터 저작권 텍스트 All Rights Reserved가 적용되지 않았습니다."
    assert "광고 수익을 창출하지 않습니다." in html_content, "푸터 안내글이 정상적으로 개편되지 않았습니다."
    
    # 제작자 유튜브 하이퍼링크 존재 여부 및 주소 확인
    assert "https://www.youtube.com/@%ED%95%9C%EC%9E%85%EC%98%A5%EC%88%98%EC%88%98_corn_bites" in html_content, "제작자 유튜브 주소가 index.html에 링크되지 않았습니다."
    assert "제작자(유튜브 한입옥수수 채널)" in html_content, "제작자(유튜브 한입옥수수 채널) 링크 텍스트가 적용되지 않았습니다."
    assert "공식 방송국이 아닌" in html_content, "방송국 정보 예외구가 변경되지 않았습니다."
    
    # style.css 푸터 링크 호버 스타일 (.footer-link) 정의 여부 확인
    assert ".footer-link" in css_content, "style.css에 .footer-link 선택자가 정의되지 않았습니다."


def test_logo_link_is_homepage():
    """상단 로고가 홈('/')으로 연결되는 앵커 태그인지 확인해야 한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # logo-area가 a 태그이며 href="/"를 포함하고 있는지 검사
    assert 'href="/"' in html_content, "로고 영역에 홈 링크 href='/'가 누락되었습니다."
    assert 'logo-area' in html_content, "로고 영역에 logo-area 클래스가 존재하지 않습니다."


def test_episode_dates_are_accurate():
    """스크립트 첫 줄에서 파싱된 방영 날짜가 1회는 '2024-01-04', 2회는 '2024-01-11' 등 정확한 YYYY-MM-DD 형식인지 검증해야 한다."""
    from data import RADIO_DATA
    
    # 1회 에피소드 찾기
    ep1 = next((ep for ep in RADIO_DATA if ep.get("episode") == 1), None)
    assert ep1 is not None, "1회 에피소드 데이터가 존재하지 않습니다."
    assert ep1.get("date") == "2024-01-04", f"1회 날짜가 {ep1.get('date')}로 잘못 파싱되었습니다. (기대값: 2024-01-04)"

    # 2회 에피소드 찾기
    ep2 = next((ep for ep in RADIO_DATA if ep.get("episode") == 2), None)
    assert ep2 is not None, "2회 에피소드 데이터가 존재하지 않습니다."
    assert ep2.get("date") == "2024-01-11", f"2회 날짜가 {ep2.get('date')}로 잘못 파싱되었습니다. (기대값: 2024-01-11)"


def test_advice_ids_are_sequential():
    """api/advice_data.py의 ADVICE_DATA의 모든 ID 번호가 1부터 누락 없이 순차적으로 연속되어야 한다."""
    from api.advice_data import ADVICE_DATA
    
    assert len(ADVICE_DATA) > 0, "조언 데이터가 비어있습니다."
    
    # id 번호 리스트 추출
    ids = [item["id"] for item in ADVICE_DATA]
    
    # 1부터 연속된 순차적 일련번호 검증 (빈 번호가 없어야 함)
    expected_ids = list(range(1, len(ids) + 1))
    assert ids == expected_ids, f"ID가 1부터 빈틈없이 순차적으로 연속되지 않습니다. 누락되거나 중복된 ID가 존재합니다."


def test_advice_data_contains_episodes_51_to_60():
    """사용자님이 직접 정비하신 51회~60회 방송 데이터(총 5개, ID 53, 54, 55, 56, 57)가 안전하게 보존되어 있어야 한다."""
    from api.advice_data import ADVICE_DATA
    
    target_data = [item for item in ADVICE_DATA if 51 <= item["episode"] <= 60]
    
    # 총 개수 검증 (5개)
    assert len(target_data) == 5, f"사용자 정비 후 51~60회 데이터 개수가 5개가 아닙니다. (실제 개수: {len(target_data)}개)"
    
    # ID 검증
    expected_ids = {54, 55, 56, 57, 58}
    actual_ids = {item["id"] for item in target_data}
    assert expected_ids == actual_ids, f"기대했던 ID 세트{expected_ids}와 실제 ID 세트{actual_ids}가 일치하지 않습니다."


def test_advice_data_contains_episodes_61_to_68():
    """사용자님이 직접 정비하신 61회~68회 방송 데이터(총 4개, ID 58, 59, 60, 61)가 안전하게 보존되어 있어야 한다."""
    from api.advice_data import ADVICE_DATA
    
    # 61회~68회에 해당하는 데이터 필터링
    target_data = [item for item in ADVICE_DATA if 61 <= item["episode"] <= 68]
    
    # 개수 검증 (4개)
    assert len(target_data) == 4, f"사용자 정비 후 61~68회 데이터 개수가 4개가 아닙니다. (실제 개수: {len(target_data)}개)"
    
    # ID 검증
    expected_ids = {59, 60, 61, 62}
    actual_ids = {item["id"] for item in target_data}
    assert expected_ids == actual_ids, f"기대했던 ID 세트{expected_ids}와 실제 ID 세트{actual_ids}가 일치하지 않습니다."


def test_advice_data_contains_episodes_72_to_80():
    """사용자님이 직접 정비하신 72회~80회 방송 데이터(총 4개, ID 62, 63, 64, 65)가 안전하게 보존되어 있어야 한다."""
    from api.advice_data import ADVICE_DATA
    
    # 72회~80회에 해당하는 데이터 필터링
    target_data = [item for item in ADVICE_DATA if 72 <= item["episode"] <= 80]
    
    # 개수 검증 (4개)
    assert len(target_data) == 4, f"사용자 정비 후 72~80회 데이터 개수가 4개가 아닙니다. (실제 개수: {len(target_data)}개)"
    
    # ID 검증
    expected_ids = {63, 64, 65, 66}
    actual_ids = {item["id"] for item in target_data}
    assert expected_ids == actual_ids, f"기대했던 ID 세트{expected_ids}와 실제 ID 세트{actual_ids}가 일치하지 않습니다."


def test_advice_data_contains_episodes_81_to_90():
    """사용자님이 직접 정비하신 81회~90회 방송 데이터(총 6개, ID 66, 67, 68, 69, 70, 71)가 안전하게 보존되어 있어야 한다."""
    from api.advice_data import ADVICE_DATA
    
    # 81회~90회에 해당하는 데이터 필터링
    target_data = [item for item in ADVICE_DATA if 81 <= item["episode"] <= 90]
    
    # 개수 검증 (총 6개여야 함)
    assert len(target_data) == 6, f"사용자 정비 후 81~90회 데이터 개수가 6개가 아닙니다. (실제 개수: {len(target_data)}개)"
    
    # ID 검증
    expected_ids = {67, 68, 69, 70, 71, 72}
    actual_ids = {item["id"] for item in target_data}
    assert expected_ids == actual_ids, f"기대했던 ID 세트 {expected_ids}와 실제 ID 세트 {actual_ids}가 일치하지 않습니다."


def test_advice_data_contains_episodes_96_to_100():
    """사용자님이 직접 정비하신 96회~100회 방송 데이터(총 4개, ID 72, 73, 74, 75)가 안전하게 보존되어 있어야 한다."""
    from api.advice_data import ADVICE_DATA
    
    # 96회~100회에 해당하는 데이터 필터링
    target_data = [item for item in ADVICE_DATA if 96 <= item["episode"] <= 100]
    
    # 개수 검증 (총 4개여야 함)
    assert len(target_data) == 4, f"사용자 정비 후 96~100회 데이터 개수가 4개가 아닙니다. (실제 개수: {len(target_data)}개)"
    
    # ID 검증
    expected_ids = {73, 74, 75, 76}
    actual_ids = {item["id"] for item in target_data}
    assert expected_ids == actual_ids, f"기대했던 ID 세트 {expected_ids}와 실제 ID 세트 {actual_ids}가 일치하지 않습니다."


def test_advice_data_contains_episodes_101_to_110():
    """사용자님이 직접 정비하신 101회~110회 방송 데이터(총 7개, ID 76, 77, 78, 79, 80, 81, 82)가 안전하게 보존되어 있어야 한다."""
    from api.advice_data import ADVICE_DATA
    
    # 101회~110회에 해당하는 데이터 필터링
    target_data = [item for item in ADVICE_DATA if 101 <= item["episode"] <= 110]
    
    # 개수 검증 (7개)
    assert len(target_data) == 7, f"101~110회 데이터 개수가 7개가 아닙니다. (실제 개수: {len(target_data)}개)"
    
    # ID 검증
    expected_ids = {77, 78, 79, 80, 81, 82, 83}
    actual_ids = {item["id"] for item in target_data}
    assert expected_ids == actual_ids, f"기대했던 ID 세트 {expected_ids}와 실제 ID 세트 {actual_ids}가 일치하지 않습니다."


def test_advice_data_contains_episodes_111_to_126():
    """사용자님이 직접 정비하신 111회부터 126회까지의 방송 데이터(총 9개, ID 83~91)가 누락 없이 포함되어 있어야 한다."""
    from api.advice_data import ADVICE_DATA
    
    # 111회~126회에 해당하는 데이터 필터링
    target_data = [item for item in ADVICE_DATA if 111 <= item["episode"] <= 126]
    
    # 개수 검증 (총 9개여야 함)
    assert len(target_data) == 9, f"111~126회 데이터 개수가 9개가 아닙니다. (실제 개수: {len(target_data)}개)"
    
    # ID 범위 검증 (84~92)
    expected_ids = set(range(84, 93))
    actual_ids = {item["id"] for item in target_data}
    assert expected_ids.issubset(actual_ids), f"기대했던 ID(83~91) 중 일부가 존재하지 않습니다. (실제 ID: {actual_ids})"


def test_new_advice_in_episode_16():
    """16회에 새 포춘쿠키 조언이 추가되었는지 확인한다."""
    from api.advice_data import ADVICE_DATA
    matching = [item for item in ADVICE_DATA if item["episode"] == 16]
    assert len(matching) == 2
    texts = [item["text"] for item in matching]
    assert any("말끝에 용" in text or "말끝에 '용'" in text for text in texts)


def test_main_js_randomizes_recommend_tags():
    """main.js에서 추천 태그를 4개로 제한하고 랜덤 셔플하는 코드가 구현되어 있는지 검증한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    js_path = os.path.join(public_dir, "main.js")
    assert os.path.exists(js_path)
    
    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()
        
    assert "slice(0, 4)" in js_content or "slice(0,4)" in js_content, "main.js에 추천 태그를 4개로 슬라이싱하는 코드가 포함되어야 합니다."
    assert "Math.random()" in js_content, "main.js에 무작위 정렬을 위해 Math.random()을 사용하는 코드가 포함되어야 합니다."


def test_overseas_performance_tag_exists():
    """index.html에 #해외_공연_에피소드 추천 태그가 매핑과 함께 존재하는지 검증한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    assert 'data-tag="static:21-5246-프랑스,31-455-사탄,40-1399-아비뇽,52-2550-베를린,55-454-몽골,86-1184-슬립노모어,89-2750-대사관,98-3796-프랑스"' in html_content, "해외 공연 에피소드의 정적 매핑 파라미터가 올바르지 않습니다."


def test_seo_elements_exist():
    """index.html에 JSON-LD 구조화 데이터, OG/Twitter 메타 태그가 존재하며, robots.txt와 sitemap.xml 파일이 루트 폴더에 존재하는지 검증한다."""
    public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
    html_path = os.path.join(public_dir, "index.html")
    robots_path = os.path.join(public_dir, "robots.txt")
    sitemap_path = os.path.join(public_dir, "sitemap.xml")
    
    assert os.path.exists(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Open Graph & Twitter Card 검증
    assert 'property="og:url"' in html_content
    assert 'name="twitter:card"' in html_content
    assert 'content="BTN라디오 \'오늘따라 신승태입니다\'의 스크립트를 정리한 웹사이트입니다. 키워드를 검색해 라디오 속 소중한 순간들을 다시 만나보세요."' in html_content
    # JSON-LD 구조화 데이터 검증
    assert 'type="application/ld+json"' in html_content
    assert '"@type": "WebSite"' in html_content
    
    # robots.txt & sitemap.xml 존재 여부 검증
    assert os.path.exists(robots_path), "public/robots.txt 파일이 존재하지 않습니다."
    assert os.path.exists(sitemap_path), "public/sitemap.xml 파일이 존재하지 않습니다."


def test_app_load_without_static_dir(monkeypatch):
    """static_dir이 존재하지 않는 환경(예: Vercel 서버리스 환경)에서 api.index 모듈 로드가 RuntimeError 없이 성공하는지 검증한다."""
    import importlib
    import sys
    import os
    
    # os.path.exists와 os.path.isdir이 public 디렉토리에 대해 False를 반환하도록 모킹
    original_exists = os.path.exists
    original_isdir = os.path.isdir
    
    def mock_exists(path):
        if "public" in str(path):
            return False
        return original_exists(path)
        
    def mock_isdir(path):
        if "public" in str(path):
            return False
        return original_isdir(path)
        
    monkeypatch.setattr(os.path, "exists", mock_exists)
    monkeypatch.setattr(os.path, "isdir", mock_isdir)
    
    # 모듈 리로드 시도
    # 수정 전 코드에서는 os.path.exists 검사 없이 무조건 StaticFiles를 마운트하므로
    # 존재하지 않는 디렉토리에 대해 RuntimeError: Directory '...' does not exist 가 발생해야 합니다.
    importlib.reload(sys.modules["api.index"])


def test_root_redirects_to_index_html():
    """루트 경로('/')로 접속 시 '/index.html'로 리다이렉트해야 한다."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (301, 302, 303, 307, 308)
    assert response.headers.get("location") == "/index.html"








