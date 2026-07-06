# 매일 자동 실행 설정 가이드

매일 자동으로 새 영상을 처리하도록 스케줄러를 설정하는 방법입니다.

## 사전 준비

```bash
# 1. 필수 패키지 설치
pip install -r requirements.txt

# 2. DeepL API 키 설정
export DEEPL_API_KEY='your-api-key-here'

# 3. 실행 권한 추가
chmod +x youtube_to_subtitled_shorts.py
```

---

## 옵션 1: Linux/macOS - Cron 작업 설정 (추천)

### 1-1. Cron 편집기 열기
```bash
crontab -e
```

### 1-2. 매일 오전 8시에 실행하도록 설정
```crontab
# 매일 오전 8시에 실행
0 8 * * * cd /home/user/portfolio1 && export DEEPL_API_KEY='your-api-key-here' && /usr/bin/python3 youtube_to_subtitled_shorts.py

# 또는 특정 시간대 선택:
# 매일 오전 6시
0 6 * * * cd /home/user/portfolio1 && export DEEPL_API_KEY='your-api-key-here' && /usr/bin/python3 youtube_to_subtitled_shorts.py

# 매일 정오
0 12 * * * cd /home/user/portfolio1 && export DEEPL_API_KEY='your-api-key-here' && /usr/bin/python3 youtube_to_subtitled_shorts.py

# 매일 오후 8시
0 20 * * * cd /home/user/portfolio1 && export DEEPL_API_KEY='your-api-key-here' && /usr/bin/python3 youtube_to_subtitled_shorts.py
```

### 1-3. Cron 작업 확인
```bash
# 설정된 크론 작업 확인
crontab -l

# 실행 로그 확인
grep CRON /var/log/syslog  # Ubuntu/Debian
log stream --predicate 'process == "cron"'  # macOS
```

### 1-4. Cron 로그 실시간 모니터링 (macOS)
```bash
log stream --predicate 'process == "cron"' --level debug
```

---

## 옵션 2: Windows - 작업 스케줄러 설정

### 2-1. 배치 파일 생성
`youtube_scheduler.bat` 파일 생성:

```batch
@echo off
cd /d C:\Users\YourUsername\portfolio1
set DEEPL_API_KEY=your-api-key-here
python youtube_to_subtitled_shorts.py
```

### 2-2. 작업 스케줄러 열기
- `Win + R` → `taskschd.msc` 실행

### 2-3. 새 작업 만들기
1. 오른쪽 패널에서 "기본 작업 만들기" 클릭
2. 이름: "YouTube Shorts Generator"
3. "다음 단계" 클릭

### 2-4. 트리거 설정
- 트리거: "매일"
- 시간: 08:00 (원하는 시간 선택)
- "다음 단계" 클릭

### 2-5. 동작 설정
- 동작: "프로그램 시작"
- 프로그램/스크립트: `C:\Users\YourUsername\portfolio1\youtube_scheduler.bat`
- "마침" 클릭

---

## 옵션 3: Python APScheduler 사용 (더 유연함)

### 3-1. APScheduler 설치
```bash
pip install apscheduler
```

### 3-2. 스케줄러 스크립트 생성
`run_scheduler.py` 파일 생성:

```python
#!/usr/bin/env python3
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import subprocess
import signal
import sys

def run_youtube_converter():
    """YouTube 변환 스크립트 실행"""
    print(f"\n[{datetime.now()}] Starting YouTube converter...")
    result = subprocess.run(
        ["python", "youtube_to_subtitled_shorts.py"],
        cwd="/home/user/portfolio1",
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(f"Success: {result.stdout}")

def main():
    # DeepL API 키 설정
    os.environ['DEEPL_API_KEY'] = 'your-api-key-here'
    
    # 스케줄러 생성
    scheduler = BackgroundScheduler()
    
    # 매일 오전 8시에 실행
    scheduler.add_job(
        run_youtube_converter,
        trigger=CronTrigger(hour=8, minute=0),
        name="YouTube Converter",
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        scheduler.shutdown()
        sys.exit(0)

if __name__ == "__main__":
    main()
```

### 3-3. 백그라운드 실행 (Linux/macOS)
```bash
nohup python run_scheduler.py > scheduler.log 2>&1 &
```

### 3-4. 백그라운드 프로세스 확인
```bash
ps aux | grep run_scheduler
```

---

## 옵션 4: systemd 서비스 (Linux 전용)

### 4-1. 서비스 파일 생성
`/etc/systemd/system/youtube-shorts.service` 생성:

```ini
[Unit]
Description=YouTube to Subtitled Shorts Converter
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/user/portfolio1
Environment="DEEPL_API_KEY=your-api-key-here"
ExecStart=/usr/bin/python3 /home/user/portfolio1/youtube_to_subtitled_shorts.py
Restart=always
RestartSec=10
StandardOutput=append:/home/user/portfolio1/service.log
StandardError=append:/home/user/portfolio1/service.log

[Install]
WantedBy=multi-user.target
```

### 4-2. 타이머 설정
`/etc/systemd/system/youtube-shorts.timer` 생성:

```ini
[Unit]
Description=YouTube Shorts Generator Daily Timer
Requires=youtube-shorts.service

[Timer]
OnCalendar=daily
OnCalendar=08:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 4-3. 서비스 활성화
```bash
sudo systemctl daemon-reload
sudo systemctl enable youtube-shorts.timer
sudo systemctl start youtube-shorts.timer

# 상태 확인
sudo systemctl status youtube-shorts.timer
sudo systemctl list-timers
```

---

## 로그 확인

스크립트 실행 로그는 자동으로 저장됩니다:

- **processing.log**: 상세 실행 로그
- **processed.json**: 처리된 영상 목록 (중복 방지)

```bash
# 최신 로그 확인
tail -f processing.log

# 처리된 영상 확인
cat processed.json | jq .
```

---

## 출력 구조

```
portfolio1/
├── links.txt                      # 채널 링크 목록
├── youtube_to_subtitled_shorts.py # 메인 스크립트
├── processed.json                 # 처리 완료 영상 기록
├── processing.log                 # 실행 로그
├── output/                        # 최종 출력 폴더
│   ├── shorts_1_1.mp4
│   ├── shorts_1_2.mp4
│   ├── shorts_1_3.mp4
│   ├── shorts_2_1.mp4
│   └── ...
└── temp/                          # 임시 파일 (자동 정리)
```

---

## 트러블슈팅

### 크론 작업이 실행되지 않음

1. 환경변수 확인:
```bash
# 풀 경로 사용
0 8 * * * /usr/bin/env DEEPL_API_KEY='key' /usr/bin/python3 /full/path/script.py
```

2. 로그 확인:
```bash
# Ubuntu/Debian
sudo tail -f /var/log/syslog | grep CRON

# macOS
log stream --predicate 'process == "cron"'
```

### "DEEPL_API_KEY not set" 오류

크론이나 스케줄러에서 환경변수가 전달되지 않으면:

1. 스크립트 수정:
```python
# youtube_to_subtitled_shorts.py에서
api_key = os.environ.get('DEEPL_API_KEY', 'hardcoded-key')
```

2. 또는 .env 파일 사용:
```bash
# .env 파일 생성
echo "DEEPL_API_KEY=your-key" > .env

# 스크립트에 추가
from dotenv import load_dotenv
load_dotenv()
```

### 메모리 부족 오류

대용량 비디오 처리 시 메모리 부족이 발생할 수 있습니다:

1. 한 번에 처리하는 영상 수 제한 (links.txt에 채널 개수 줄이기)
2. 크롭 해상도 낮추기 (1080x1920 → 720x1280)
3. 스왑 공간 증가

---

## API 비용 관리

DeepL API 사용량 모니터링:

```bash
# 월별 API 호출 확인
grep "translate_to_korean" processing.log | wc -l

# 예상 비용 계산
# DeepL Free: 월 50만 자 무료
# Pro: 초과분 시 요금 발생
```

---

## 다음 단계

1. **실행 테스트**: `python youtube_to_subtitled_shorts.py` 수동 실행
2. **로그 확인**: processing.log 확인
3. **스케줄러 설정**: 위 옵션 중 하나 선택
4. **정기 모니터링**: processed.json으로 진행 상태 확인

---

## 추천 설정

| OS | 추천 옵션 |
|---|---|
| **Linux** | systemd 서비스 (옵션 4) |
| **macOS** | Cron (옵션 1) |
| **Windows** | 작업 스케줄러 (옵션 2) |
| **모든 OS** | APScheduler (옵션 3) |
