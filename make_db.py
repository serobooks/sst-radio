# -*- coding: utf-8 -*-
import re
import json
import os
import functools

# target_words.json 로드
target_words_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target_words.json")
if os.path.exists(target_words_path):
    with open(target_words_path, "r", encoding="utf-8") as f:
        TARGET_WORDS = json.load(f)
else:
    TARGET_WORDS = []

# keywords.json 로드
keywords_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords.json")
if os.path.exists(keywords_path):
    with open(keywords_path, "r", encoding="utf-8") as f:
        KEYWORDS_MAP = json.load(f)
else:
    KEYWORDS_MAP = {}

# corrections.json 로드
corrections_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corrections.json")
if os.path.exists(corrections_path):
    with open(corrections_path, "r", encoding="utf-8") as f:
        MANUAL_CORRECTIONS = json.load(f)
else:
    MANUAL_CORRECTIONS = {}

@functools.lru_cache(maxsize=10240)
def disassemble_korean(text):
    """한글 음절을 초성, 중성, 종성 자소로 분해합니다."""
    CHOSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    JUNGSUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
    JONGSUNG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    result = []
    for char in text:
        if '가' <= char <= '힣':
            char_code = ord(char) - 0xAC00
            cho = char_code // 588
            jung = (char_code % 588) // 28
            jong = char_code % 28
            result.append(CHOSUNG[cho])
            result.append(JUNGSUNG[jung])
            if JONGSUNG[jong] != '':
                result.append(JONGSUNG[jong])
        else:
            result.append(char)
    return "".join(result)

@functools.lru_cache(maxsize=10240)
def levenshtein_distance(s1, s2):
    """두 자소 문자열 간의 Levenshtein 편집 거리를 계산합니다."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


@functools.lru_cache(maxsize=10240)
def _correct_single_word(word, target_words_tuple):
    for target in target_words_tuple:
        target_len = len(target)
        if len(word) >= target_len:
            prefix = word[:target_len]
            suffix = word[target_len:]
            
            target_dis = disassemble_korean(target)
            prefix_dis = disassemble_korean(prefix)
            dist = levenshtein_distance(target_dis, prefix_dis)
            
            surnames = ('김', '이', '박', '최', '신', '임', '조', '강', '윤', '장', '한', '오', '서', '안', '황', '송', '전', '홍', '유')
            is_short_name = target_len == 3 and target.startswith(surnames)
            threshold = 1 if (target_len <= 2 or is_short_name) else 2
            if dist <= threshold:
                return target + suffix
    return word

def correct_spelling_fuzzy(text, target_words):
    """target_words의 기준 명칭과 유사한 텍스트 상의 오타를 자소 유사도 비교를 통해 자동으로 교정합니다."""
    if not text or not target_words:
        return text

    # 원본 공백을 완벽히 보존하며 단어 단위로 쪼갬
    tokens = re.split(r'(\s+)', text)
    target_words_tuple = tuple(target_words)
    
    for i in range(len(tokens)):
        # 공백이나 특수 문자가 아닌 일반 단어 부분만 교정 시도
        if i % 2 == 0 and tokens[i]:
            tokens[i] = _correct_single_word(tokens[i], target_words_tuple)
                        
    return "".join(tokens)


# 1. 삭제 로그 파일 열기
log_file = open("deleted_log.txt", "w", encoding="utf-8")

def time_to_seconds(time_str):
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2: return parts[0] * 60 + parts[1]
    elif len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def is_dj_talk(text):
    """DJ 대사 패턴 판별"""
    dj_endings = ["입니다", "했어요", "오셨습니다", "되겠네요", "어때요", "했죠", "좋아요", "가요", "까요", "하세요", "합니다"]
    return any(ending in text for ending in dj_endings)

def clean_text_smart(text):
    # 1:1 수동 오타 사전 교정 선적용 (자소 유사도로 잡지 못하는 축약/특이 변형 오타 전처리)
    for wrong, right in MANUAL_CORRECTIONS.items():
        text = text.replace(wrong, right)

    # 정규식을 이용해 대괄호로 둘러싸인 모든 형태의 효과음 태그([음악], [헉 소리], [한숨] 등) 일괄 제거
    temp_cleaned = re.sub(r'\[.*?\]', '', text)
    temp_cleaned = temp_cleaned.replace(">>", "").strip()
    
    # 1. [음악] 태그가 원래 포함되어 있으면서 대사가 아니고 짧은 문장 = 노래 가사로 간주하고 삭제 후 로그 저장
    if "[음악]" in text and not is_dj_talk(text) and len(temp_cleaned) < 40:
        log_file.write(f"삭제된 구간: {text}\n")
        return ""
    
    # 2. 노래 가사가 아닌 정상 대사는 태그가 지워진 텍스트를 최종 대사로 사용
    cleaned = temp_cleaned
    
    # 3. 자소 기반 유사도 오타 교정
    cleaned = correct_spelling_fuzzy(cleaned, TARGET_WORDS)
    
    # 4. 연속된 모든 공백(띄어쓰기 2번 이상 등)을 1번의 공백으로 압축 치환
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned

def auto_detect_keywords(text):
    """keywords.json 규칙에 따라 텍스트에서 키워드를 자동 매칭하여 추출합니다."""
    detected = set()
    for key, words in KEYWORDS_MAP.items():
        for word in words:
            if word in text:
                detected.add(key)
    return list(detected)

def parse_single_file(file_path, file_name):
    with open(file_path, 'r', encoding='utf-8') as f:
        full_content = f.read()
        
    title_match = re.search(r'\[LIVE\] (.*?)입니다', full_content)
    title = title_match.group(0) if title_match else f"오늘따라 신승태 {file_name}"
    
    date_match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', full_content)
    if date_match:
        year, month, day = date_match.groups()
        date = f"{year}-{int(month):02d}-{int(day):02d}"
    else:
        date = "2026-05-29"
    
    # [source: 숫자] 형식 제거
    cleaned_content = re.sub(r'\[source:\s*\d+\]', '', full_content)
    
    timeline_blocks = re.split(r'\((\d{1,2}:\d{2}(?::\d{2})?)\)', cleaned_content)
    
    timeline_list = []
    all_episode_text = ""
    
    for i in range(1, len(timeline_blocks), 2):
        time_str = timeline_blocks[i].strip()
        text_content = clean_text_smart(timeline_blocks[i+1])
        
        if text_content:
            timeline_list.append({"time": time_to_seconds(time_str), "text": text_content})
            all_episode_text += " " + text_content

    episode_num = "".join(filter(str.isdigit, file_name))
    v_id = f"YOUTUBE_ID_{episode_num}"

    return {
        "episode": int(episode_num),
        "video_id": v_id,
        "title": title,
        "date": date,
        "keywords": auto_detect_keywords(all_episode_text),
        "timeline": timeline_list
    }

if __name__ == "__main__":
    folder_path = "./scripts"
    all_radio_data = []
    
    file_list = sorted(os.listdir(folder_path))
    for filename in file_list:
        if filename.endswith(".txt"):
            print(f"변환 중: {filename}")
            all_radio_data.append(parse_single_file(os.path.join(folder_path, filename), filename))
            
    with open("data.py", "w", encoding="utf-8") as out_file:
        out_file.write("RADIO_DATA = " + json.dumps(all_radio_data, ensure_ascii=False, indent=4))
        
    log_file.close() # 로그 파일 닫기
    print("완료! 'data.py'와 'deleted_log.txt'가 생성되었습니다.")