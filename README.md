# Django Channels

Django + React 기반의 실시간 채팅 서비스

## 주요 기능

- 회원가입, 로그인/로그아웃
- 채팅방 생성/삭제/입장/퇴장
- 실시간 채팅 및 메시지 전송
- 실시간 방 목록/인원/온라인수 업데이트 (WebSocket 기반)
- 안읽은 메시지 수, 메시지 읽음 표시
- 파일 업로드, 메시지 리액션
- 푸시 알림 지원

## 폴더 구조

```
kasie-channel/
├── chat-frontend/      # React 프론트엔드
├── chat/               # Django 앱 (백엔드)
├── config/             # Django 프로젝트 설정
```

## 실행 방법

### 1. 백엔드(Django)

```bash
cd kasie-channel
python manage.py migrate
python manage.py runserver
```

### 2. 프론트엔드(React)

```bash
cd chat-frontend
npm install
npm start
```

### 3. 개발 서버 주소

- Django: `http://localhost:8000/`
- React: `http://localhost:3000/`

## 실시간 기능

- 글로벌 WebSocket 연결로 방 생성/삭제/인원수/온라인수 등 실시간 반영
- 채팅방별 WebSocket 연결로 실시간 메시지 송수신