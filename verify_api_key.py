#!/usr/bin/env python3
"""
API 키 검증 스크립트 - .env 파일의 API 키가 제대로 로드되는지 확인
"""
import sys
from pathlib import Path

# Backend path 추가
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# 1. python-dotenv로 직접 로드
print("=" * 70)
print("방법 1: python-dotenv (direct)")
print("=" * 70)
from dotenv import load_dotenv
import os

load_dotenv(override=True)
key_from_dotenv = os.getenv("ELEVENLABS_API_KEY", "")
print(f"API 키 길이: {len(key_from_dotenv)}")
print(f"API 키: {key_from_dotenv[:15]}...{key_from_dotenv[-10:]}")

# 2. pydantic-settings로 로드
print("\n" + "=" * 70)
print("방법 2: pydantic-settings (config.py)")
print("=" * 70)
from app.config import settings

key_from_pydantic = settings.ELEVENLABS_API_KEY
print(f"API 키 길이: {len(key_from_pydantic)}")
print(f"API 키: {key_from_pydantic[:15]}...{key_from_pydantic[-10:]}")

# 3. API 테스트
print("\n" + "=" * 70)
print("API 테스트")
print("=" * 70)

import httpx

client = httpx.Client(
    headers={"xi-api-key": key_from_pydantic},
    timeout=30.0
)

try:
    response = client.post(
        "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
        json={
            "text": "Hello test",
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
    )

    if response.status_code == 200:
        print(f"✅ API 키 작동 확인!")
        print(f"   응답 크기: {len(response.content)} 바이트")
    elif response.status_code == 401:
        print(f"❌ 401 Unauthorized")
        print(f"   응답: {response.text}")
    else:
        print(f"⚠️  상태 코드: {response.status_code}")
        print(f"   응답: {response.text[:200]}")

except Exception as e:
    print(f"❌ 오류: {e}")

print("\n" + "=" * 70)
print("검증 완료")
print("=" * 70)
