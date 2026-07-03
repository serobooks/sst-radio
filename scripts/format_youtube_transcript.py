# -*- coding: utf-8 -*-
import re
import sys
import argparse

def parse_time_to_seconds(time_str):
    """'MM:SS' 또는 'HH:MM:SS' 형식의 타임코드를 초 단위 정수로 변환합니다."""
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def parse_korean_time_to_seconds(korean_str):
    """'X시간 Y분 Z초' 같은 한글 시간 표현을 초 단위 정수로 변환합니다."""
    korean_str = korean_str.strip()
    pattern = r'^(?:(\d+)\s*시간)?\s*(?:(\d+)\s*분)?\s*(?:(\d+)\s*초)?$'
    match = re.match(pattern, korean_str)
    if not match:
        return None
    
    hours, minutes, seconds = match.groups()
    total = 0
    has_any = False
    if hours:
        total += int(hours) * 3600
        has_any = True
    if minutes:
        total += int(minutes) * 60
        has_any = True
    if seconds:
        total += int(seconds)
        has_any = True
        
    return total if has_any else None

def clean_korean_timecode(line):
    """줄 시작 부분의 타임코드와 중복된 한글 시간 표현을 정제합니다.
    
    예: '0:077초두 손모음.' -> (7, '두 손모음.')
    """
    line = line.strip()
    timecode_match = re.match(r'^(\d{1,2}:\d{2}(?::\d{2})?)', line)
    if not timecode_match:
        return (0, line)
        
    time_str = timecode_match.group(1)
    seconds_from_code = parse_time_to_seconds(time_str)
    
    remaining = line[len(time_str):].strip()
    
    # 시간, 분, 초 한글 표현 매칭 (최대한 매칭)
    korean_match = re.match(r'^(?:(\d+)\s*시간)?\s*(?:(\d+)\s*분)?\s*(?:(\d+)\s*초)?', remaining)
    if korean_match:
        matched_str = korean_match.group(0).strip()
        if matched_str and any(unit in matched_str for unit in ['시간', '분', '초']):
            seconds_from_korean = parse_korean_time_to_seconds(matched_str)
            if seconds_from_korean == seconds_from_code:
                # 타임코드와 한글 시간 값이 완벽히 일치하면 제거
                remaining = remaining[len(korean_match.group(0)):].strip()
                
    return (seconds_from_code, remaining)

def format_seconds(seconds):
    """초 단위 정수를 '(MM:SS)' 또는 '(HH:MM:SS)' 형식으로 포맷팅합니다."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"({hours:02d}:{minutes:02d}:{secs:02d})"
    else:
        return f"({minutes:02d}:{secs:02d})"

def merge_transcripts(parsed_lines, min_seconds=20, min_chars=80):
    """시간과 글자 수 임계값에 따라 촘촘한 라인들을 병합합니다."""
    if not parsed_lines:
        return []
        
    merged = []
    current_time = parsed_lines[0][0]
    current_texts = [parsed_lines[0][1]]
    
    for sec, text in parsed_lines[1:]:
        combined_text = " ".join(current_texts)
        time_diff = sec - current_time
        
        # 지정된 간격과 최소 글자 수를 모두 만족하면 새 행으로 분리
        if time_diff >= min_seconds and len(combined_text) >= min_chars:
            merged.append(f"{format_seconds(current_time)} {combined_text}")
            current_time = sec
            current_texts = [text]
        else:
            current_texts.append(text)
            
    if current_texts:
        merged.append(f"{format_seconds(current_time)} {' '.join(current_texts)}")
        
    return merged

def process_file(file_path, min_seconds=20, min_chars=80):
    """지정된 파일을 읽어 포맷 정제 및 병합을 수행한 뒤 덮어씁니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    if not lines:
        print(f"Error: 파일이 비어 있습니다. ({file_path})")
        return
        
    title_line = lines[0].strip()
    
    # 두 번째 라인이 빈 줄이거나 내용이 있으면, 세 번째 라인부터 스크립트 본문으로 간주
    script_start_idx = 1
    for idx, l in enumerate(lines[1:], start=1):
        if l.strip() and not re.match(r'^\d{1,2}:\d{2}', l.strip()):
            # [LIVE] 제목 줄이나 빈 줄, 혹은 Transcripts: 같은 헤더 건너뛰기
            continue
        else:
            script_start_idx = idx
            break
            
    parsed_lines = []
    for l in lines[script_start_idx:]:
        clean_l = l.strip()
        if not clean_l:
            continue
        # 타임코드로 시작하는 행만 정제 대상
        if re.match(r'^\d{1,2}:\d{2}', clean_l):
            sec, text = clean_korean_timecode(clean_l)
            if text:  # 빈 대사가 아니면 보존
                parsed_lines.append((sec, text))
        else:
            # 혹시 타임코드 없이 대사만 있는 줄이 섞여있다면 마지막 타임코드에 붙임
            if parsed_lines:
                last_sec, last_text = parsed_lines[-1]
                parsed_lines[-1] = (last_sec, f"{last_text} {clean_l}")
                
    # 병합 수행
    merged_lines = merge_transcripts(parsed_lines, min_seconds, min_chars)
    
    # 덮어쓰기 출력
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(f"{title_line}\n\n")
        f.write("Transcripts:\n")
        for ml in merged_lines:
            f.write(f"{ml}\n")
            
    print(f"Success: {file_path} 변환이 완료되었습니다. (총 {len(merged_lines)}개 타임라인)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="유튜브 자체 스크립트 표시 복사 텍스트를 아카이브 표준 포맷으로 변환 및 병합합니다.")
    parser.add_argument("file_path", help="변환할 스크립트 텍스트 파일 경로")
    parser.add_argument("--min-seconds", type=int, default=20, help="병합 최소 시간 간격 (초 단위, 기본값: 20)")
    parser.add_argument("--min-chars", type=int, default=80, help="병합 최소 글자 수 (기본값: 80)")
    
    args = parser.parse_args()
    process_file(args.file_path, args.min_seconds, args.min_chars)
