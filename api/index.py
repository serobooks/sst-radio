# -*- coding: utf-8 -*-
import os
import random
import re
import sys

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 기존 data.py 및 추출된 데이터, 매핑 딕셔너리 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import RADIO_DATA  # noqa: E402
from api.advice_data import ADVICE_DATA  # noqa: E402
from api.youtube_mapping import YOUTUBE_MAP  # noqa: E402

app = FastAPI(title="오늘따라 신승태 라디오 아카이브 API")

# 교차 출처 리소스 공유(CORS) 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def redirect_to_index():
    """루트 경로 접속 시 /index.html 정적 파일로 리다이렉트합니다."""
    return RedirectResponse(url="/index.html")

def format_clean_title(title_str: str, episode_num: int) -> str:
    """사용자에게 보여줄 정돈된 타이틀로 포맷합니다."""
    # 예: '오늘따라 신승태 001.txt' -> '오늘따라 신승태 1회'
    if episode_num > 0:
        return f"오늘따라 신승태 {episode_num}회"
    return title_str.replace(".txt", "")

@app.get("/api/search")
async def search_episodes(
    q: str = Query(None, description="검색할 키워드"),
    window: int = Query(300, description="중복 제거 시간 윈도우(초 단위, 기본값 5분, 0 입력 시 전체 출력)")
):
    """
    라디오 스크립트 검색 엔진 API
    키워드(q)를 받아 매칭되는 에피소드 및 정확한 타임라인 목록을 반환합니다.
    동일 에피소드 내에서 인접한 시간(window 초 이하)에 중복 검출될 경우 첫 멘트 시점만 남겨두고 배제합니다.
    """
    if not q or not q.strip():
        raise HTTPException(
            status_code=400, 
            detail="검색어(q)를 입력해주세요."
        )
        
    query = q.strip().lower()
    search_results = []
    
    # [수동 명장면 핀포인트 매핑 검색 분기]
    if query.startswith("static:"):
        # 형식 예: q=static:1-4047-스카이라운지,7-2031-로라,14-775-여장,125-512-고무신
        static_items = query.replace("static:", "").split(",")
        for item_str in static_items:
            parts = item_str.split("-")
            if len(parts) >= 2:
                try:
                    target_ep = int(parts[0])
                    target_time = int(parts[1])
                    highlight_word = parts[2] if len(parts) > 2 else ""
                except ValueError:
                    continue
                
                # RADIO_DATA에서 해당 에피소드 및 타임라인 탐색
                for episode in RADIO_DATA:
                    ep_num = episode.get("episode", 0)
                    if ep_num == target_ep:
                        timeline = episode.get("timeline", [])
                        title = episode.get("title", "")
                        date_str = episode.get("date", "")
                        video_id = YOUTUBE_MAP.get(ep_num, f"YOUTUBE_ID_OF_EPISODE_{ep_num:03d}")
                        clean_title = format_clean_title(title, ep_num)
                        
                        # 5초 내외의 타임라인 오차 허용으로 정확한 초 검색
                        for idx, time_item in enumerate(timeline):
                            time_sec = time_item.get("time", 0)
                            if abs(time_sec - target_time) <= 5:
                                prev_text = timeline[idx - 1].get("text", "") if idx > 0 else ""
                                next_text = timeline[idx + 1].get("text", "") if idx < len(timeline) - 1 else ""
                                combined_text = f"{prev_text} {time_item.get('text', '')} {next_text}".strip()
                                
                                search_results.append({
                                    "episode": ep_num,
                                    "video_id": video_id,
                                    "title": clean_title,
                                    "date": date_str,
                                    "time": time_sec,
                                    "text": combined_text,
                                    "keywords": [highlight_word] if highlight_word else []
                                })
                                break
        return search_results
    
    for episode in RADIO_DATA:
        title = episode.get("title", "")
        keywords = episode.get("keywords", [])
        timeline = episode.get("timeline", [])
        date_str = episode.get("date", "")
        ep_num = episode.get("episode", 0) # 새로 추가된 명시적인 회차 번호 사용
        
        video_id = YOUTUBE_MAP.get(ep_num, f"YOUTUBE_ID_OF_EPISODE_{ep_num:03d}")
        clean_title = format_clean_title(title, ep_num)
        
        # 같은 에피소드 내에서 직전에 매치된 타임라인 시간
        last_match_time = None
        
        # 대사 본문에서 정밀 매칭이 이루어지는 타임라인만 콕 집어 출력합니다.
        for i, item in enumerate(timeline):
            text = item.get("text", "")
            time_sec = item.get("time", 0)
            
            # 쉼표(,) 구분자를 기준으로 다중 검색어(OR 검색)를 처리합니다.
            sub_queries = [word.strip() for word in query.split(",") if word.strip()]
            if not sub_queries:
                continue
                
            text_match = False
            for sub_q in sub_queries:
                match_sub = sub_q in text.lower()
                
                # [버그 해결]: '장구' 검색 시 '승승장구' 또는 '승승 장구' 노이즈 멘트 필터 차단
                if match_sub and sub_q == "장구":
                    clean_text = text.lower().replace(" ", "")
                    if "승승장구" in clean_text:
                        match_sub = False
                
                if match_sub:
                    text_match = True
                    break # 하나라도 일치하면 매칭 성공
            
            if text_match:
                # 윈도우 기능이 활성화(window > 0)되어 있고, 직전 매칭 시간과의 간격이 윈도우 이하인 경우 중복 대화로 간주해 스킵
                if window > 0 and last_match_time is not None and (time_sec - last_match_time) <= window:
                    continue
                
                # 3단 샌드위치 텍스트 바인딩 (이전 멘트와 다음 멘트 결합)
                prev_text = timeline[i - 1].get("text", "") if i > 0 else ""
                next_text = timeline[i + 1].get("text", "") if i < len(timeline) - 1 else ""
                combined_text = f"{prev_text} {text} {next_text}".strip()
                
                search_results.append({
                    "episode": ep_num,
                    "video_id": video_id,
                    "title": clean_title,
                    "date": date_str,
                    "time": time_sec,
                    "text": combined_text,
                    "keywords": keywords
                })
                # 마지막 매치 시점 업데이트
                last_match_time = time_sec
                
    # 100건 잘림 해제 상태는 유지
    return search_results

@app.get("/api/advice")
async def get_random_advice():
    """
    '오늘 하루 마도사의 조언' API
    엄선된 촌철살인 조언 멘트와 매핑된 실제/가상 유튜브 영상 ID를 무작위로 반환합니다.
    """
    if not ADVICE_DATA:
        raise HTTPException(
            status_code=500,
            detail="조언 데이터가 구축되지 않았습니다."
        )
        
    advice = random.choice(ADVICE_DATA)
    ep_num = advice.get("episode", 0)
    
    # youtube_mapping 파일의 맵을 거쳐 실시간 연동
    video_id = YOUTUBE_MAP.get(ep_num, advice.get("video_id"))
    
    return {
        "id": advice.get("id"),
        "episode": ep_num,
        "video_id": video_id,
        "text": advice.get("text")
    }

# 로컬 단독 구동 시 정적 파일(HTML/CSS/JS)을 함께 서빙하기 위한 정적 파일 마운트
# Vercel 환경이 아니거나, 실제 static_dir이 존재하는 경우에만 마운트합니다.
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
if not os.environ.get("VERCEL") and os.path.exists(static_dir) and os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="public")

