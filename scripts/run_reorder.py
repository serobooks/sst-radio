# -*- coding: utf-8 -*-
import os
import sys

# 프로젝트 루트 디렉토리를 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.reorder_helper import reorder_advice_ids_text

def main():
    """실제 api/advice_data.py 파일을 읽어서 id를 순차적으로 재정렬하고 덮어씁니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    target_file_path = os.path.join(project_root, "api", "advice_data.py")
    
    print(f"[정보] 대상 파일 경로: {target_file_path}")
    
    if not os.path.exists(target_file_path):
        print(f"[오류] 대상을 찾을 수 없습니다: {target_file_path}")
        sys.exit(1)
        
    # 1. 원본 파일 읽기
    with open(target_file_path, "r", encoding="utf-8") as f:
        original_content = f.read()
        
    # 2. 텍스트 치환 수행
    updated_content = reorder_advice_ids_text(original_content)
    
    # 3. 변경 사항 저장
    with open(target_file_path, "w", encoding="utf-8") as f:
        f.write(updated_content)
        
    print("[성공] api/advice_data.py 파일의 모든 ID 일련번호가 빈 번호 없이 연속되도록 재정렬되었습니다.")

if __name__ == "__main__":
    main()
