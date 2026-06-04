# -*- coding: utf-8 -*-
import re

def reorder_advice_ids_text(text: str) -> str:
    """텍스트 내의 모든 'id': 숫자 형식을 찾아 1부터 순차적으로 치환하는 헬퍼 함수.
    
    또한 리스트 요소 사이의 누락된 콤마(,)도 정밀하게 자동 보정합니다.
    기존 들여쓰기와 주석 등 서식을 완벽히 유지하기 위해 정규표현식 치환을 사용합니다.
    """
    # 1. 닫는 중괄호 '}' 뒤에 콤마가 누락된 경우를 찾아 보정 (뒤에 주석을 건너뛰고 '{'가 나오는 경우)
    comma_pattern = r'\}(?!\s*,)(\s*(?:#.*?\n\s*)*)\{'
    text = re.sub(comma_pattern, r'},\1{', text)

    # 2. ID 일련번호 재배열 수행
    counter = 1
    
    def replacer(match):
        nonlocal counter
        # 매칭된 텍스트에서 따옴표의 종류를 유지하기 위해 매칭된 접두사('id' 또는 "id")를 동적으로 구성
        matched_prefix = match.group(0).split(':')[0]
        result = f"{matched_prefix}: {counter}"
        counter += 1
        return result

    # 따옴표 종류("id" 또는 'id') 및 콜론 이후 공백에 구애받지 않도록 정규식 구성
    pattern = r'["\']id["\']\s*:\s*\d+'
    return re.sub(pattern, replacer, text)

