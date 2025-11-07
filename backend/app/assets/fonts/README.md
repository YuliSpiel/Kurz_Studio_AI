# Custom Fonts

이 디렉토리는 커스텀 폰트 파일을 저장하는 곳입니다.

## 폰트 설치 방법

1. `.ttf` 또는 `.otf` 폰트 파일을 이 디렉토리에 복사합니다.
2. 파일명이 폰트 ID로 사용됩니다 (확장자 제외).
3. 서버를 재시작하면 자동으로 폰트 목록에 추가됩니다.

예시:
```
backend/app/assets/fonts/
├── NanumGothic.ttf
├── Paperlogy-7Bold.ttf
└── README.md
```

## 라이선스 주의사항

- **상업용 이용 가능** 라이선스를 가진 폰트만 사용하세요.
- 각 폰트의 라이선스 조건을 반드시 확인하세요.
- 재배포가 허용되지 않는 폰트는 Git에 커밋하지 마세요.

## 권장 무료 폰트

- **나눔고딕**: https://hangeul.naver.com/font
- **눈누**: https://noonnu.cc/ (다양한 무료 폰트 모음)
- **Google Fonts**: https://fonts.google.com/ (한글 지원 폰트 검색)

## 시스템 폰트

macOS 시스템 폰트는 자동으로 사용 가능합니다:
- AppleGothic
- AppleMyungjo

## 문제 해결

폰트가 목록에 나타나지 않으면:
1. 파일 확장자가 `.ttf` 또는 `.otf`인지 확인
2. 파일명에 특수문자나 공백이 없는지 확인
3. 서버 재시작
