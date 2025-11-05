# ElevenLabs API 문제 해결 완료

## 문제 원인

ElevenLabs API에서 401 Unauthorized 에러가 발생한 원인:

1. **API 키 권한 제한**: 새로 발급받은 API 키는 TTS 권한은 있지만, 일부 권한이 없음
   - ❌ `user_read` - 사용자 정보 조회 권한 없음
   - ❌ `voices_read` - 음성 목록 조회 권한 없음
   - ✅ **TTS 생성 권한은 정상 작동!**

2. **Jupyter 노트북 캐싱**: `.env` 파일을 업데이트한 후에도 노트북이 이전 값을 사용
   - Python의 모듈 캐싱으로 인해 `app.config.settings`가 이전 API 키를 유지
   - 노트북을 재시작해도 커널에 캐시된 모듈은 유지됨

## 해결 방법

### 1. API 키 확인
현재 `.env` 파일의 API 키는 정상 작동합니다:

### 2. 노트북 사용 시 주의사항

**중요**: `.env` 파일을 변경한 후에는 반드시 아래 셀을 실행하여 설정을 다시 로드해야 합니다:

```python
# Cell 3에 추가된 코드
import importlib
import app.config
importlib.reload(app.config)
from app.config import settings
```

이렇게 하면 업데이트된 `.env` 파일의 값을 다시 읽어옵니다.

### 3. 독립 스크립트 테스트

노트북 외에 다음 스크립트들로 테스트 가능:

#### a) 간단한 TTS 테스트
```bash
python test_tts_simple.py
```

#### b) 상세한 진단 테스트
```bash
python test_elevenlabs_api.py
```

#### c) API 키 검증
```bash
python verify_api_key.py
```

## 테스트 결과

✅ **모든 테스트 통과**

```
방법 1: python-dotenv (direct)
API 키 길이: 51
API 키: sk_ee50fbab9484...b400b42392

방법 2: pydantic-settings (config.py)
API 키 길이: 51
API 키: sk_ee50fbab9484...b400b42392

API 테스트
✅ API 키 작동 확인!
   응답 크기: 20107 바이트
```

## API 키 권한 관련 참고사항

현재 API 키는 다음과 같은 제한이 있습니다:

1. **사용자 정보 조회** (`/v1/user`): ❌ 권한 없음
   - 문제없음: 우리 앱에서는 사용하지 않음

2. **음성 목록 조회** (`/v1/voices`): ❌ 권한 없음
   - 문제없음: 기본 음성(Rachel)을 사용하므로 목록 조회 불필요

3. **TTS 생성** (`/v1/text-to-speech/{voice_id}`): ✅ 정상 작동
   - 우리가 실제로 필요한 기능!

### 더 많은 권한이 필요한 경우

ElevenLabs 웹사이트에서 API 키를 재생성할 때 다음 권한을 선택하세요:
- ✅ `text_to_speech` (필수 - 이미 있음)
- ✅ `voices_read` (선택 - 다양한 음성 사용 시)
- ✅ `user_read` (선택 - 사용량 확인 시)

## 다음 단계

1. ✅ API 키 정상 작동 확인
2. ✅ 노트북 설정 업데이트
3. ⏭️ `simple_test.ipynb` Cell 3부터 다시 실행하여 TTS 테스트

## 주요 파일

- [.env](.env) - API 키 설정
- [simple_test.ipynb](simple_test.ipynb) - 통합 테스트 노트북
- [verify_api_key.py](verify_api_key.py) - API 키 검증 스크립트
- [test_tts_simple.py](test_tts_simple.py) - 간단한 TTS 테스트
- [test_elevenlabs_api.py](test_elevenlabs_api.py) - 상세한 진단 테스트

---

**작성일**: 2025-11-05
**상태**: ✅ 해결 완료
