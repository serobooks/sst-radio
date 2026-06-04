# -*- coding: utf-8 -*-
import pytest
import sys
import os

# scripts 폴더 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.reorder_helper import reorder_advice_ids_text
except ImportError:
    reorder_advice_ids_text = None

def test_reorder_advice_ids_text():
    """id 번호가 비어있고 쉼표가 누락된 텍스트 데이터를 입력받아 1부터 순차적으로 정렬하고 쉼표를 보정하는지 검증한다."""
    # 일부러 id 번호를 비워두고 쉼표를 누락시킨 텍스트 구성
    input_text = """ADVICE_DATA = [
    {
        "id": 10,
        "episode": 1,
        "video_id": "TEST_001",
        "text": "첫 번째 조언입니다."
    }
    # 중간 주석 테스트 (여기에 쉼표가 빠짐)
    {
        "id": 15,
        "episode": 1,
        "video_id": "TEST_001",
        "text": "두 번째 조언입니다."
    },
    {
        "id": 22,
        "episode": 2,
        "video_id": "TEST_002",
        "text": "세 번째 조언입니다."
    }
]"""

    expected_output = """ADVICE_DATA = [
    {
        "id": 1,
        "episode": 1,
        "video_id": "TEST_001",
        "text": "첫 번째 조언입니다."
    },
    # 중간 주석 테스트 (여기에 쉼표가 빠짐)
    {
        "id": 2,
        "episode": 1,
        "video_id": "TEST_001",
        "text": "두 번째 조언입니다."
    },
    {
        "id": 3,
        "episode": 2,
        "video_id": "TEST_002",
        "text": "세 번째 조언입니다."
    }
]"""

    assert reorder_advice_ids_text is not None, "reorder_helper 모듈에서 reorder_advice_ids_text 함수를 불러오지 못했습니다."
    actual_output = reorder_advice_ids_text(input_text)
    assert actual_output == expected_output

