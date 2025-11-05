#!/usr/bin/env python3
"""
ElevenLabs API 진단 스크립트
API 키가 정상적으로 작동하는지 확인합니다.
"""
import sys
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

# .env 파일 명시적으로 로드
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


def test_api_key():
    """API 키 진단 테스트"""

    print("=" * 70)
    print("ElevenLabs API 진단")
    print("=" * 70)

    # API 키 확인 - 환경변수에서 직접 읽기
    api_key = os.getenv("ELEVENLABS_API_KEY", "")

    if not api_key:
        print("\n❌ ELEVENLABS_API_KEY가 설정되지 않았습니다.")
        return False

    print(f"\n✅ API 키 확인: {api_key[:15]}...{api_key[-10:]}")
    print(f"   전체 길이: {len(api_key)} 문자")

    # HTTP 클라이언트 생성
    client = httpx.Client(
        headers={"xi-api-key": api_key},
        timeout=30.0
    )

    print("\n" + "=" * 70)
    print("테스트 1: 사용자 정보 조회 (/v1/user) - OPTIONAL")
    print("=" * 70)

    try:
        response = client.get("https://api.elevenlabs.io/v1/user")
        print(f"상태 코드: {response.status_code}")

        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ 인증 성공!")
            print(f"   사용자 정보:")
            print(f"   - Subscription: {user_data.get('subscription', {}).get('tier', 'N/A')}")
            print(f"   - Character count: {user_data.get('subscription', {}).get('character_count', 0)}")
            print(f"   - Character limit: {user_data.get('subscription', {}).get('character_limit', 0)}")
        elif response.status_code == 401:
            print(f"⚠️  권한 없음 (이 테스트는 선택사항)")
            error_detail = response.json().get('detail', {})
            print(f"   메시지: {error_detail.get('message', 'N/A')}")
            print(f"   💡 API 키에 'user_read' 권한이 없지만, TTS는 작동할 수 있습니다.")
        else:
            print(f"⚠️  예상치 못한 응답")
            print(f"   응답: {response.text[:200]}")

    except Exception as e:
        print(f"⚠️  오류 발생 (이 테스트는 선택사항): {e}")

    print("\n" + "=" * 70)
    print("테스트 2: 음성 목록 조회 (/v1/voices) - OPTIONAL")
    print("=" * 70)

    try:
        response = client.get("https://api.elevenlabs.io/v1/voices")
        print(f"상태 코드: {response.status_code}")

        if response.status_code == 200:
            voices = response.json().get("voices", [])
            print(f"✅ 음성 목록 조회 성공!")
            print(f"   사용 가능한 음성: {len(voices)}개")

            # 처음 5개 음성 출력
            for i, voice in enumerate(voices[:5], 1):
                print(f"   {i}. {voice.get('name')} (ID: {voice.get('voice_id')})")
        elif response.status_code == 401:
            print(f"⚠️  권한 없음 (이 테스트는 선택사항)")
            error_detail = response.json().get('detail', {})
            print(f"   메시지: {error_detail.get('message', 'N/A')}")
            print(f"   💡 API 키에 'voices_read' 권한이 없지만, 기본 음성으로 TTS는 작동할 수 있습니다.")
        else:
            print(f"⚠️  예상치 못한 응답")
            print(f"   응답: {response.text[:200]}")

    except Exception as e:
        print(f"⚠️  오류 발생 (이 테스트는 선택사항): {e}")

    print("\n" + "=" * 70)
    print("테스트 3: TTS 생성 테스트")
    print("=" * 70)

    try:
        # 간단한 영어 텍스트로 테스트
        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        payload = {
            "text": "Hello, this is a test.",
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        print(f"음성 ID: {voice_id}")
        print(f"텍스트: {payload['text']}")

        response = client.post(url, json=payload)
        print(f"상태 코드: {response.status_code}")

        if response.status_code == 200:
            print(f"✅ TTS 생성 성공!")
            print(f"   응답 크기: {len(response.content)} 바이트")

            # 테스트 파일 저장
            output_dir = Path("backend/app/data/tts_test")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / "diagnostic_test.mp3"

            with open(output_file, "wb") as f:
                f.write(response.content)

            print(f"   저장 위치: {output_file}")

        else:
            print(f"❌ TTS 생성 실패")
            print(f"   응답 헤더: {dict(response.headers)}")
            print(f"   응답 본문: {response.text[:500]}")
            return False

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP 오류 발생:")
        print(f"   상태 코드: {e.response.status_code}")
        print(f"   응답 헤더: {dict(e.response.headers)}")
        print(f"   응답 본문: {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("🎉 모든 테스트 통과!")
    print("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = test_api_key()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단됨")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
