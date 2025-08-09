# Python 3.9를 베이스 이미지로 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 종속성 파일 복사 및 설치
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 데이터베이스 초기화를 위한 명령어 (나중에 app.py 수정 후 사용)
# RUN flask db init-db

# 컨테이너 실행 시 실행될 명령어
CMD ["flask", "run", "--host=0.0.0.0"]
