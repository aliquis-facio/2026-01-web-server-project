# ASCII Motion Board

Django 기반 ASCII ART 게시판입니다. 사용자가 이미지를 업로드하면 단일 ASCII ART로 변환하고, 영상을 업로드하면 프레임을 추출해 ASCII 애니메이션과 GIF 다운로드를 제공합니다.

## 실행

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 주요 기능

- 회원가입, 로그인, 로그아웃
- 게시글 CRUD
- 영상 업로드
- 이미지 업로드
- 이미지 -> ASCII ART 변환
- OpenCV 기반 프레임 추출
- 영상 -> ASCII 애니메이션 변환
- 자체 그레이스케일 매핑 기반 ASCII 변환
- Pillow 기반 ASCII GIF 생성
- ASCII TXT/GIF 다운로드
- 댓글, 좋아요, 검색, 조회수
