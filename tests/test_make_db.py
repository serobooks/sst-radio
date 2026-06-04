# -*- coding: utf-8 -*-
import pytest
import sys
import os

# scripts 및 상위 폴더 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from make_db import disassemble_korean, levenshtein_distance, correct_spelling_fuzzy, clean_text_smart, auto_detect_keywords

def test_clean_text_smart():
    """clean_text_smart 함수가 노래 가사를 필터링하고 일반 대사는 올바르게 오타 교정까지 적용하는지 검증한다."""
    # 1. 노래 가사로 판정되어 삭제되어야 하는 케이스 (대사 어미가 없고 짧으며 [음악] 포함)
    assert clean_text_smart("[음악] 사랑은 언제나 외로움뿐") == ""
    
    # 2. DJ 대사이므로 삭제되지 않고 효과음 태그만 제거된 뒤 오타가 교정되어야 하는 케이스
    # '테디' -> '태디' 교정 검증 포함
    assert clean_text_smart("[음악] 안녕하십니까 테디입니다.") == "안녕하십니까 태디입니다."
    assert clean_text_smart(">> 깽가리를 연주해보겠습니다 [웃음]") == "꽹과리를 연주해보겠습니다"
    
    # 3. 임의의 대괄호 효과음 태그들([헉 소리], [한숨], [기침] 등)이 모두 깨끗이 제거되는지 검증
    assert clean_text_smart("[헉 소리] [한숨] 안녕하세요 테디입니다 [목을 가다듬음]") == "안녕하세요 태디입니다"
    assert clean_text_smart("[기침] [콧방귀] 꽹과리를 연주해 봐요 [박수]") == "꽹과리를 연주해 봐요"
    
    # 4. 1:1 수동 오타 교정(corrections.json 기반)이 선적용되는지 검증
    assert clean_text_smart("현역강 무대는 대단했다.") == "현역가왕 무대는 대단했다."
    assert clean_text_smart("포천 농학 대회가 있었다.") == "포천 농악 대회가 있었다."


def test_disassemble_korean():
    """한글 단어가 초성, 중성, 종성으로 잘 분리되는지 검증한다."""
    assert disassemble_korean("최수호") == "ㅊㅚㅅㅜㅎㅗ"
    assert disassemble_korean("최스호") == "ㅊㅚㅅㅡㅎㅗ"
    assert disassemble_korean("태디") == "ㅌㅐㄷㅣ"
    assert disassemble_korean("테디") == "ㅌㅔㄷㅣ"
    assert disassemble_korean("깽가리") == "ㄲㅐㅇㄱㅏㄹㅣ"
    assert disassemble_korean("꽹과리") == "ㄲㅙㅇㄱㅘㄹㅣ"  # 유니코드 표준 중성 'ㅙ'로 올바르게 분리됨
    # 한글이 아닌 문자는 그대로 유지되는지 검증
    assert disassemble_korean("DJ태디!") == "DJㅌㅐㄷㅣ!"

def test_levenshtein_distance():
    """자소 단위의 편집 거리(Levenshtein Distance) 연산이 올바른지 검증한다."""
    # 1글자 교정 (ㅜ -> ㅡ)
    s1 = disassemble_korean("최수호")
    s2 = disassemble_korean("최스호")
    assert levenshtein_distance(s1, s2) == 1

    # 1글자 교정 (ㅚ -> ㅐ)
    s3 = disassemble_korean("채수호")
    assert levenshtein_distance(s1, s3) == 1

    # 1글자 교정 (ㅐ -> ㅔ)
    assert levenshtein_distance(disassemble_korean("태디"), disassemble_korean("테디")) == 1

    # 완전히 다른 단어는 거리가 멀어야 함
    assert levenshtein_distance(disassemble_korean("최수호"), disassemble_korean("신승태")) > 3

def test_correct_spelling_fuzzy():
    """올바른 기준 명칭 목록을 기반으로 텍스트 안의 다양한 오타가 정상 교정되는지 검증한다."""
    target_words = ["최수호", "신승태", "태디", "꽹과리", "야생마도사"]

    # 1. 고유명사 오타 교정 및 조사 보존 검증
    assert correct_spelling_fuzzy("채수호가 찾아왔다.", target_words) == "최수호가 찾아왔다."
    assert correct_spelling_fuzzy("최스호의 노래를 듣자.", target_words) == "최수호의 노래를 듣자."
    assert correct_spelling_fuzzy("신승태와 함께", target_words) == "신승태와 함께"
    assert correct_spelling_fuzzy("신승태가 아니라 신승태였나?", target_words) == "신승태가 아니라 신승태였나?"

    # 2. 맞춤법 및 DJ 별명 교정 검증
    assert correct_spelling_fuzzy("깽가리를 신나게 쳤다.", target_words) == "꽹과리를 신나게 쳤다."
    assert correct_spelling_fuzzy("테디는 최고의 DJ입니다.", target_words) == "태디는 최고의 DJ입니다."
    assert correct_spelling_fuzzy("야생맛도사가 추천하는 맛집", target_words) == "야생마도사가 추천하는 맛집"

    # 3. 교정 대상이 아닌 일반 단어가 오염되지 않는지 검증
    # '최고'는 '최수호'와 자소 편집 거리가 멀기 때문에 변환되지 않아야 함
    assert correct_spelling_fuzzy("최고의 선택이었습니다.", target_words) == "최고의 선택이었습니다."
    # '테이프'는 '태디'와 다르므로 변환되지 않아야 함
    assert correct_spelling_fuzzy("테이프를 재생합니다.", target_words) == "테이프를 재생합니다."
    
    # 4. 3글자 명사의 과교정(오염) 방지 검증 (임계값 1자소 제한 검증)
    # '김준수'가 등록되어 있어도 2자소 차이가 나는 '김민수'나 '이준수' 등 다른 청취자 이름은 오염되지 않아야 함
    assert correct_spelling_fuzzy("오늘 사연은 김민수 님이 보내주셨습니다.", target_words + ["김준수"]) == "오늘 사연은 김민수 님이 보내주셨습니다."
    assert correct_spelling_fuzzy("이준수 님이 신청하신 노래입니다.", target_words + ["김준수"]) == "이준수 님이 신청하신 노래입니다."
    # 단, 1자소 차이 오타(최스호 -> 최수호)는 여전히 완벽하게 교정되어야 함
    assert correct_spelling_fuzzy("최스호가 노래했다.", target_words + ["김준수"]) == "최수호가 노래했다."

def test_auto_detect_keywords():
    """auto_detect_keywords 함수가 keywords.json 설정을 기반으로 1:1 및 스마트 태깅을 올바르게 수행하는지 검증한다."""
    # 1. 1:1 정확한 매칭 검증
    # '맛집'이 포함되어 있으므로 '맛집'이 태깅되어야 함
    assert "맛집" in auto_detect_keywords("오늘 소개할 맛집은 이곳입니다.")
    
    # 2. 민요는 더이상 국악에 포함되지 않으므로 '국악' 태깅에서 제외되어야 함
    # 텍스트에 '국악'이 직접 언급되지 않고 '민요'만 있는 경우 '국악' 키워드가 없어야 함
    assert "국악" not in auto_detect_keywords("경기 민요를 감상해 봅시다.")
    
    # 3. 직접 '국악'이 언급된 경우는 당연히 '국악'이 태깅되어야 함
    assert "국악" in auto_detect_keywords("우리의 소중한 국악 예술")

    # 4. 현역가왕 스마트 매핑 검증
    # 프로그램명이 직접 언급되지 않고, 노래 제목 '빗물'이나 '사랑은 생명의 꽃'만 있어도 '현역가왕'이 태깅되어야 함
    assert "현역가왕" in auto_detect_keywords("오늘 부른 노래는 빗물입니다.")
    assert "현역가왕" in auto_detect_keywords("사랑은 생명의 꽃 무대는 정말 감동적이었어요.")
    assert "현역가왕" in auto_detect_keywords("하늘에서 빗물이 내린다.") # 단순 문자열 포함 매칭이므로 '빗물' 단어에 의해 매칭되는 것이 맞음

