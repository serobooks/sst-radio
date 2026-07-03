# -*- coding: utf-8 -*-
import pytest
from scripts.format_youtube_transcript import (
    parse_time_to_seconds,
    parse_korean_time_to_seconds,
    clean_korean_timecode,
    merge_transcripts
)

def test_parse_time_to_seconds():
    # 타임코드 문자열을 초 단위로 올바르게 변환하는지 테스트
    assert parse_time_to_seconds("0:00") == 0
    assert parse_time_to_seconds("0:07") == 7
    assert parse_time_to_seconds("1:01") == 61
    assert parse_time_to_seconds("10:07") == 607
    assert parse_time_to_seconds("1:02:15") == 3735

def test_parse_korean_time_to_seconds():
    # 한글 시간 표현을 초 단위로 올바르게 변환하는지 테스트
    assert parse_korean_time_to_seconds("7초") == 7
    assert parse_korean_time_to_seconds("17초") == 17
    assert parse_korean_time_to_seconds("1분 1초") == 61
    assert parse_korean_time_to_seconds("9분") == 540
    assert parse_korean_time_to_seconds("10분 7초") == 607
    assert parse_korean_time_to_seconds("1시간 2분 15초") == 3735
    assert parse_korean_time_to_seconds("아무텍스트") is None

def test_clean_korean_timecode():
    # 한글 시간 중복 표현이 제거되고 표준 형식으로 포맷팅되는지 테스트
    assert clean_korean_timecode("0:00동참해 주세요.") == (0, "동참해 주세요.")
    assert clean_korean_timecode("0:077초두 손모음.") == (7, "두 손모음.")
    assert clean_korean_timecode("1:011분 1초오늘은 조금") == (61, "오늘은 조금")
    assert clean_korean_timecode("9:009분그랬어요") == (540, "그랬어요")
    assert clean_korean_timecode("10:0710분 7초그럴 수도") == (607, "그럴 수도")
    # 시간 값이 불일치할 때는 제거하지 않음 (대사가 숫자로 시작하는 경우 등)
    assert clean_korean_timecode("1:012분 5초오늘") == (61, "2분 5초오늘")

def test_merge_transcripts():
    # 촘촘한 타임라인이 기준(min_seconds, min_chars)에 따라 잘 병합되는지 테스트
    parsed_lines = [
        (0, "동참해 주세요."),
        (7, "안녕하세요."),
        (17, "가수 오유진입니다."),
        (22, "말을 하다 보면 상처가 될까 조심스러질 때가 있습니다."),
        (45, "그래서 말을 안 하죠.")
    ]
    
    # min_seconds=20, min_chars=50 기준으로 병합
    # 1. (0, "동참해 주세요.") -> 누적글자수 8자, 누적시간 0초
    # 2. (7, "안녕하세요.") -> 시간차 7초(<20), 누적글자수 8자(<50)이므로 병합 -> 누적글자수 15자 ("동참해 주세요. 안녕하세요.")
    # 3. (17, "가수 오유진입니다.") -> 시간차 17초(<20), 누적글자수 15자(<50)이므로 병합 -> 누적글자수 26자
    # 4. (22, "말을 하다 보면...") -> 시간차 22초(>=20), 누적글자수 26자(<50)이므로 병합 -> 누적글자수 59자
    # 5. (45, "그래서 말을 안 하죠.") -> 이전 타임코드가 0초이므로 0초 기준 시간차 45초(>=20), 누적글자수 59자(>=50)이므로 새로운 타임코드 분리!
    
    merged = merge_transcripts(parsed_lines, min_seconds=20, min_chars=50)
    
    assert len(merged) == 2
    assert merged[0] == "(00:00) 동참해 주세요. 안녕하세요. 가수 오유진입니다. 말을 하다 보면 상처가 될까 조심스러질 때가 있습니다."
    assert merged[1] == "(00:45) 그래서 말을 안 하죠."
