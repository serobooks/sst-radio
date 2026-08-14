# -*- coding: utf-8 -*-
import os
import json
import argparse
import subprocess
import sys

def load_embargoes(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading embargoes.json: {e}")
            return []
    return []

def save_embargoes(filepath, data):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Success: embargoes.json 업데이트 완료")
    except Exception as e:
        print(f"Error saving embargoes.json: {e}")

def run_make_db():
    print("make_db.py를 실행하여 DB를 갱신합니다...")
    # 프로젝트 루트 디렉토리 찾기
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    make_db_script = os.path.join(project_root, "make_db.py")
    
    try:
        # python 실행
        result = subprocess.run([sys.executable, make_db_script], cwd=project_root, capture_output=True, text=True, encoding='utf-8')
        if result.returncode == 0:
            print("DB 빌드 성공!")
            print(result.stdout)
        else:
            print("DB 빌드 실패:")
            print(result.stderr)
    except Exception as e:
        print(f"DB 빌드 중 오류 발생: {e}")

def main():
    parser = argparse.ArgumentParser(description="라디오 아카이브의 엠바고(비공개) 구간을 설정하고 DB를 갱신합니다.")
    parser.add_argument("--episode", type=int, required=True, help="에피소드 번호 (예: 137)")
    parser.add_argument("--start", type=str, help="시작 타임코드 (예: '20:18')")
    parser.add_argument("--end", type=str, help="종료 타임코드 (예: '23:06')")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--lock", action="store_true", help="해당 구간에 엠바고를 설정(active: true)합니다.")
    group.add_argument("--release", action="store_true", help="엠바고를 해제(active: false)합니다.")
    
    args = parser.parse_args()
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    embargo_file = os.path.join(project_root, "embargoes.json")
    
    embargoes = load_embargoes(embargo_file)
    
    if args.lock:
        if not args.start or not args.end:
            parser.error("--lock 설정 시에는 --start와 --end 타임코드가 필수입니다.")
            
        # 기존에 동일한 규칙이 있는지 검사
        found = False
        for rule in embargoes:
            if rule.get("episode") == args.episode and rule.get("start_time") == args.start and rule.get("end_time") == args.end:
                rule["active"] = True
                found = True
                print(f"기존 엠바고 규칙 활성화: 에피소드 {args.episode} ({args.start} ~ {args.end})")
                break
                
        if not found:
            new_rule = {
                "episode": args.episode,
                "start_time": args.start,
                "end_time": args.end,
                "active": True
            }
            embargoes.append(new_rule)
            print(f"새로운 엠바고 규칙 추가: 에피소드 {args.episode} ({args.start} ~ {args.end})")
            
    elif args.release:
        # --start가 있으면 특정 규칙만 해제, 없으면 해당 에피소드의 모든 규칙 해제
        modified_count = 0
        for rule in embargoes:
            if rule.get("episode") == args.episode:
                if args.start:
                    if rule.get("start_time") == args.start:
                        rule["active"] = False
                        modified_count += 1
                        print(f"특정 엠바고 규칙 비활성화: 에피소드 {args.episode} ({rule.get('start_time')} ~ {rule.get('end_time')})")
                else:
                    rule["active"] = False
                    modified_count += 1
                    print(f"엠바고 규칙 비활성화: 에피소드 {args.episode} ({rule.get('start_time')} ~ {rule.get('end_time')})")
                    
        if modified_count == 0:
            print(f"해제할 수 있는 활성 엠바고 규칙을 찾지 못했습니다. (에피소드: {args.episode})")
            
    save_embargoes(embargo_file, embargoes)
    run_make_db()

if __name__ == "__main__":
    main()
