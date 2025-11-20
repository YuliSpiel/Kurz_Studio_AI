좋다, 이제 이거 “스킬 장착용 사이드프로젝트 로드맵”으로 박제해보자 ✅

아래는 **실제 구현 순서 기준 체크리스트**야.
그냥 위에서부터 하나씩 지워나간다고 생각하면 됨.

---

## 0. 준비 단계

* [ ] Python 가상환경 만들기 & FastAPI, Uvicorn 설치
* [ ] Docker로 PostgreSQL, Redis 컨테이너 띄우기

  * [ ] `docker-compose.yml` or 단일 `docker run`으로 Postgres
  * [ ] Redis 컨테이너도 같이

---

## 1. FastAPI + Postgres + SQLAlchemy (기본 뼈대)

**목표: `/users`, `/runs`만 있는 가장 단순한 API 서버 만들기**

* [ ] `backend/app` 폴더 구조 만들기

  * [ ] `main.py` (FastAPI 앱)
  * [ ] `config.py` (환경변수, DB URL)
  * [ ] `database.py` (engine, session, Base)
* [ ] SQLAlchemy 모델 정의

  * [ ] `models/user.py` – 최소 필드: `id`, `email`, `username`
  * [ ] `models/run.py` – 최소 필드: `id`, `user_id`, `prompt`, `state`
* [ ] Alembic 설정

  * [ ] `alembic init` 실행
  * [ ] `env.py`에서 `Base.metadata` 연결
  * [ ] 첫 마이그레이션 생성 & 적용 (`alembic revision --autogenerate`, `upgrade head`)
* [ ] 최소 라우터 구현

  * [ ] `routers/users.py` – `POST /users` (회원 가입용, 매우 단순 버전)
  * [ ] `routers/runs.py` – `POST /runs`, `GET /runs/{id}`
* [ ] 로컬에서 테스트

  * [ ] `uvicorn app.main:app --reload` 실행
  * [ ] 브라우저/Swagger `/docs`에서 API 호출해보기

---

## 2. 인증 & JWT (로그인 가능한 서비스로 만들기)

**목표: “로그인한 유저만 run 생성 가능” 상태 만들기**

* [ ] 패스워드 해싱 설정

  * [ ] `utils/security.py`에 `hash_password`, `verify_password` 함수 만들기 (passlib)
* [ ] JWT 유틸

  * [ ] `utils/auth.py`에 `create_access_token`, `verify_token` 구현
* [ ] User 관련 Pydantic 스키마

  * [ ] `schemas/user.py` – `UserCreate`, `UserRead`, `UserLogin` 등
* [ ] Auth 라우터

  * [ ] `routers/auth.py` – `POST /auth/register`
  * [ ] `routers/auth.py` – `POST /auth/login` (JWT 발급)
* [ ] 현재 유저 디펜던시

  * [ ] `dependencies.py` – `get_current_user` (Authorization 헤더에서 토큰 파싱)
* [ ] Runs 라우터에 인증 적용

  * [ ] `POST /runs`에 `current_user: User = Depends(get_current_user)` 붙이기
* [ ] 테스트

  * [ ] 회원가입 → 로그인 → 발급된 토큰으로 `POST /runs` 호출 성공

---

## 3. Celery + Redis (비동기 파이프라인 기본)

**목표: “run 생성 → 바로 응답 / 실제 처리는 백그라운드”**

* [ ] Redis 컨테이너 실행 확인
* [ ] Celery 설정 파일

  * [ ] `tasks/__init__.py`, `celery_app` 생성
  * [ ] `broker_url`, `result_backend`를 Redis로 설정
* [ ] 샘플 태스크 만들기

  * [ ] `tasks/plan.py` – `@celery_app.task`로 `process_run(run_id)` 같은 더미 태스크
  * [ ] 태스크 안에서 `time.sleep(5)` 후 DB에서 `state = "DONE"` 업데이트
* [ ] Runs 생성 시 태스크 호출

  * [ ] `POST /runs`에서 run 저장 후 `process_run.delay(run.id)` 호출
* [ ] 워커 실행

  * [ ] `celery -A app.tasks.celery_app worker --loglevel=info`로 돌려보기
* [ ] 동작 확인

  * [ ] `POST /runs` → 즉시 응답
  * [ ] 몇 초 후 `GET /runs/{id}` → `state`가 DONE으로 바뀌는지 체크

---

## 4. S3/R2 스토리지 연동

**목표: “로컬 파일 대신 오브젝트 스토리지 + URL만 DB에 저장”**

* [ ] S3 또는 Cloudflare R2 버킷 생성
* [ ] `.env`에 스토리지 관련 키/엔드포인트 저장
* [ ] `services/storage_service.py` 구현

  * [ ] `upload_to_s3(local_path, s3_key) -> url`
* [ ] 샘플 파일 업로드 로직

  * [ ] Celery 태스크에서 임시 더미 파일 만들어 업로드 후 `runs.video_url` 업데이트
  * [ ] 업로드된 URL을 브라우저에서 직접 열어보기
* [ ] 실제 파이프라인과 연결

  * [ ] 나중에 영상 합성 파이프라인(`final_video.mp4`) 위치와 연결 예정

---

## 5. 크레딧 & 결제 (PortOne 연동)

**목표: “테스트 결제 → 크레딧 충전 → 크레딧으로 run 생성 제어”**

* [ ] DB 스키마 확장

  * [ ] `users.credits` 필드 추가 (기본 0)
  * [ ] `transactions` 테이블 생성 (charge/spend, amount, status 등)
* [ ] 크레딧 서비스

  * [ ] `services/credit_service.py` – `charge_credits`, `deduct_credits` 구현
* [ ] PortOne 설정

  * [ ] PortOne 테스트 상점/채널 등록
  * [ ] 백엔드에서 PortOne SDK 초기화 (테스트 키)
* [ ] 결제 라우터

  * [ ] `routers/payments.py` – `POST /payments/charge`

    * [ ] imp_uid / amount 받아서 PortOne로 검증
    * [ ] 성공 시 `transactions` 기록 + `users.credits` 증가
* [ ] run 생성 시 크레딧 차감

  * [ ] `POST /runs`에서:

    * [ ] 현재 유저의 `credits` 확인
    * [ ] 부족하면 에러 반환
    * [ ] 충분하면 `deduct_credits` 호출, run 생성 진행
* [ ] 프론트와 연동 (최소 버전)

  * [ ] 포트원 JS SDK로 결제 버튼 하나 붙이기
  * [ ] 결제 완료 후 imp_uid를 백엔드에 POST

---

## 6. 커뮤니티 & 라이브러리 (여유 생기면)

**목표: “내 작품함 + 커뮤니티 피드”까지 한 번에 경험해보기**

* [ ] `galleries` 테이블 / 모델 구현

  * [ ] `GET /gallery` – 내 작품 목록
  * [ ] `POST /gallery/{run_id}` – 즐겨찾기/폴더 지정
* [ ] `community_posts`, `likes`, `comments` 테이블 / 모델 구현

  * [ ] `GET /community` – 게시글 리스트
  * [ ] `POST /community` – 영상(run) 기반 게시글 작성
  * [ ] `POST /community/{id}/like` – 좋아요 토글
  * [ ] `POST /community/{id}/comments` – 댓글 작성

---

## 7. 마지막 다듬기 (선택)

* [ ] CORS 설정 (프론트 도메인만 허용)
* [ ] Rate limiting(슬로우API/Redis)으로 `/runs` 남발 방지
* [ ] 최소 수준의 로깅/에러 핸들링 추가
* [ ] README에 전체 아키텍처, 실행 방법 정리

---

이 체크리스트 그대로 쓰고 싶으면,
다음에 내가 **단계 1~2용 최소 프로젝트 스캐폴딩 코드** 한 번에 뽑아줄게.
그거 기준으로 "✔ 하나씩 지워가기 모드"로 진행하면 좋을 듯.

---

## 8. 버그 픽스 & 개선 이력 (2025-11-20)

### 🐛 FFmpeg 렌더링 무한 루프 이슈
**문제:**
- 46초 영상 렌더링 중 14분+ 동안 멈춤
- 출력 파일이 1.9GB로 비정상적으로 커짐
- 원인: BGM에 `aloop=loop=-1` 적용 + `duration=first` 조합이 작동 안함

**해결:** ([ffmpeg_renderer.py](../backend/app/utils/ffmpeg_renderer.py) Lines 470-522)
```python
# Calculate total video duration
total_video_duration = scene_start_time

# BGM is 30 seconds long - only loop if video is longer than 30s
if total_video_duration > 30.0:
    # Loop BGM and apply volume
    filter_complex_parts.append(f"[{audio_idx}:a]aloop=loop=-1:size=2e9,volume={volume}[bgm]")
else:
    # No loop needed - just apply volume
    filter_complex_parts.append(f"[{audio_idx}:a]volume={volume}[bgm]")

# Use duration=longest for amix
filter_complex_parts.append(f"{mix_inputs}amix=inputs={num_streams}:duration=longest[aout]")

# Add -shortest flag to trim audio to video length
cmd.extend(["-shortest"])
```

**핵심:**
- BGM은 항상 30초로 생성됨
- 영상이 30초 이하면 루프 불필요
- 영상이 30초 초과면 `aloop`로 무한 루프 후 `-shortest`로 자름

---

### 🐛 AI 프롬프트 풍부화 중복 호출 이슈
**문제:**
- Enhancement API가 연속으로 2번 호출됨
- 두 결과가 다르게 나와서 사용자 입력이 예상과 다르게 변경됨
- 원인: Enter 키 핸들러가 `handleSubmit()`을 직접 호출 → form submit 이벤트도 발생

**해결:** ([HeroChat.tsx](../frontend/src/components/HeroChat.tsx))

1. **중복 호출 방지 가드 추가** (Lines 154-158)
```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault()
  if (!prompt.trim() || disabled) return

  // Prevent duplicate calls while already enhancing
  if (isEnhancing) {
    console.log('[ENHANCE] Already enhancing, ignoring duplicate call')
    return
  }
  // ...
}
```

2. **Enter 키 핸들러 수정** (Lines 422-432)
```typescript
onKeyDown={(e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    // Don't call handleSubmit directly - let the form submit event handle it
    // This prevents duplicate submissions
    const form = e.currentTarget.form
    if (form) {
      form.requestSubmit()
    }
  }
}}
```

**핵심:**
- `isEnhancing` 플래그로 중복 호출 차단
- Enter 키는 `form.requestSubmit()`만 호출 (직접 호출 금지)

---

### ✨ 레이아웃 설정 모달에 제목 수정 기능 추가
**요구사항:**
- 레이아웃 검수 단계에서 영상 제목도 수정 가능해야 함

**구현:**

1. **Frontend - 입력 필드 추가** ([LayoutReviewModal.tsx](../frontend/src/components/LayoutReviewModal.tsx) Lines 223-240)
```typescript
<input
  type="text"
  value={title}
  onChange={(e) => setTitle(e.target.value)}
  placeholder="영상 제목을 입력하세요"
  style={{/* ... */}}
/>
```

2. **API 클라이언트 확장** ([client.ts](../frontend/src/api/client.ts) Lines 290-310)
```typescript
export async function confirmLayoutWithConfig(
  runId: string,
  layoutConfig?: LayoutConfig,
  title?: string  // 추가
): Promise<void> {
  const body: any = {}
  if (layoutConfig) body.layout_config = layoutConfig
  if (title !== undefined) body.title = title
  // ...
}
```

3. **Backend - 제목 저장 로직** ([main.py](../backend/app/main.py) Lines 852-856)
```python
# Update title if provided
if "title" in request:
    updated_title = request["title"]
    layout_data["title"] = updated_title
    logger.info(f"[{run_id}] Updated title in layout.json: {updated_title}")
```

---

### 🔧 씬 재생 길이 (Scene Duration) 개선

**문제:**
- TTS 실제 길이: 1.3초 ~ 2.3초 (평균 1.7초)
- layout.json의 씬 총 길이: 4초 ~ 5.5초
- **실제 침묵/텀: 2.5 ~ 3초** - 너무 김!

**조사 결과:**
- [voice.py](../backend/app/tasks/voice.py)에 TTS 길이 기반 duration 업데이트 로직이 이미 존재 (Lines 195-219)
- MoviePy AudioFileClip으로 실제 TTS 길이 측정 후 layout.json 업데이트
- 하지만 실제로는 적용 안 됨 (원인: 디버깅 필요)

**해결:** ([voice.py](../backend/app/tasks/voice.py) Lines 206-215)
```python
if scene_audio_durations:
    # Use the longest audio duration for the scene, plus 50ms padding
    max_audio_duration = max(scene_audio_durations)
    new_duration = max_audio_duration + 50  # Add 50ms padding (minimal pause)
    old_duration = scene.get("duration_ms", 5000)

    scene["duration_ms"] = new_duration
    logger.info(f"[{run_id}] ✅ UPDATED {scene_id} duration: {old_duration}ms → {new_duration}ms (TTS: {max_audio_duration}ms + 50ms padding)")
else:
    logger.warning(f"[{run_id}] ⚠️ No audio duration found for {scene_id}, keeping original duration: {scene.get('duration_ms', 5000)}ms")
```

**변경사항:**
1. **패딩 대폭 축소**: 500ms → 50ms (거의 끊김 없는 흐름)
2. **로깅 개선**: ✅/⚠️ 아이콘으로 업데이트 성공/실패 명확히 표시
3. **디버깅 강화**: duration 업데이트가 실제로 일어나는지 로그로 추적 가능

**예상 효과:**
- 기존: TTS 1.7s + 500ms = 2.2s 총 재생 시간
- 개선 후: TTS 1.7s + 50ms = 1.75s 총 재생 시간
- **0.45초 단축 + 빠른 템포 + 끊김 없는 흐름**

**TODO:**
- [x] 패딩 500ms → 50ms로 대폭 축소
- [x] 로깅 개선 (✅/⚠️ 아이콘 추가)
- [ ] Celery worker 재시작 후 새 run으로 테스트
- [ ] duration 업데이트가 제대로 작동하는지 로그 확인
- [ ] 필요시 추가 디버깅 (MoviePy AudioFileClip 이슈 가능성)

**참고 데이터:**
```
Run ID: 20251120_1526_귀여운카피바라가

TTS Audio 실제 길이:
scene_1: 1.67s → 기존: 2.17s (500ms) → 개선: 1.72s (50ms) ✅
scene_3: 2.35s → 기존: 2.85s (500ms) → 개선: 2.40s (50ms) ✅

기존 문제: 실제 layout은 4-5.5초 (2.5~3초 침묵) ❌
목표: TTS + 50ms로 거의 끊김 없이 ✅
```
