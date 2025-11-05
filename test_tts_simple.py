#!/usr/bin/env python3
"""
간단한 TTS 테스트 - API 키가 정상 작동하는지 확인
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드 (override=True로 환경변수 덮어쓰기)
load_dotenv(override=True)

# 직접 httpx로 테스트
import httpx

api_key = os.getenv("ELEVENLABS_API_KEY")
print(f"API 키: {api_key[:15]}...{api_key[-10:]}")

client = httpx.Client(
    headers={"xi-api-key": api_key},
    timeout=30.0
)

# TTS 요청
response = client.post(
    "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
    json={
        "text": "안녕하세요! 테스트입니다.",
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
)

print(f"상태 코드: {response.status_code}")

if response.status_code == 200:
    print(f"✅ 성공! 응답 크기: {len(response.content)} 바이트")

    # 저장
    output_file = Path("backend/app/data/tts_test/simple_test.mp3")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(response.content)
    print(f"저장 위치: {output_file}")
else:
    print(f"❌ 실패: {response.text}")
