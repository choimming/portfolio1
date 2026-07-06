# YouTube 한국어 자막 쇼츠 생성기 (일본어 원본)

유튜브 일본어 영상을 다운로드하고 Whisper로 음성을 인식한 후 DeepL로 한국어로 번역하고, 9:16 세로 비디오로 크롭한 다음 한국어 자막을 추가하는 파이썬 스크립트입니다.

## 설치 요구사항

### 시스템 패키지

#### macOS
```bash
brew install ffmpeg
brew tap homebrew-ffmpeg/ffmpeg
brew install homebrew-ffmpeg/ffmpeg/ffmpeg --with-libvpx
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg libsm6 libxext6 libxrender-dev
```

#### Windows
- [FFmpeg](https://ffmpeg.org/download.html) 설치
- Python 3.8 이상 필요

### Python 패키지 설치
```bash
pip install -r requirements.txt
```

## DeepL API 설정

1. [DeepL API](https://www.deepl.com/pro/change-plan?billing=api) 가입
2. API 키 확인
3. 환경변수 설정:

```bash
# macOS/Linux
export DEEPL_API_KEY='your-api-key-here'

# Windows (PowerShell)
$env:DEEPL_API_KEY='your-api-key-here'

# Windows (cmd)
set DEEPL_API_KEY=your-api-key-here
```

## 사용 방법

### 1. links.txt 파일 작성
```bash
# links.txt에 유튜브 URL을 한 줄씩 작성
# 예:
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=9bZkp7q19f0
```

### 2. 스크립트 실행
```bash
python youtube_to_subtitled_shorts.py
```

## 처리 과정

각 비디오에 대해 다음 작업이 수행됩니다:

1. **다운로드**: yt-dlp로 유튜브 영상 다운로드
2. **오디오 추출**: ffmpeg로 비디오에서 오디오 추출
3. **음성 인식**: OpenAI Whisper (일본어)로 자막 생성
4. **번역**: DeepL로 일본어를 한국어로 번역
5. **구간 선택**: 적당한 길이(5-15초)의 구간 3개 자동 선택
6. **세로 크롭**: 9:16 비율(1080x1920)로 크롭
7. **자막 추가**: Noto Sans 폰트로 한국어 자막 하드코딩

## 출력 파일

```
output/
├── shorts_1_1.mp4      # 첫 번째 비디오, 첫 번째 클립
├── shorts_1_2.mp4      # 첫 번째 비디오, 두 번째 클립
├── shorts_1_3.mp4      # 첫 번째 비디오, 세 번째 클립
├── shorts_2_1.mp4      # 두 번째 비디오, 첫 번째 클립
└── ...
```

## Noto Sans 폰트 설정

스크립트는 다음 경로에서 Noto Sans CJK 폰트를 찾습니다:

- `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc` (Linux)
- `/System/Library/Fonts/Noto Sans CJK JP.otf` (macOS)
- `C:\Windows\Fonts\NotoSansCJK-Regular.ttc` (Windows)

폰트가 없으면 시스템 기본 폰트를 사용합니다.

### 폰트 설치 (필요시)

#### macOS
```bash
brew tap caskroom/fonts
brew install font-noto-sans-cjk
```

#### Ubuntu/Debian
```bash
sudo apt-get install fonts-noto-cjk
```

#### Windows
Google Fonts에서 [Noto Sans CJK](https://fonts.google.com/noto/specimen/Noto+Sans+CJK+JP) 다운로드 후 설치

## 옵션 커스터마이징

`youtube_to_subtitled_shorts.py`에서 다음을 수정할 수 있습니다:

```python
# 출력 해상도 (기본값: 1080x1920)
width=1080
height=1920

# 폰트 크기 (기본값: 화면 높이의 8%)
font_size = int(height * 0.08)

# 자막 위치 ('bottom' 또는 'top')
position='bottom'

# 구간 선택 기준 (초 단위)
valid_segments = [
    seg for seg in segments
    if 5 <= (seg['end'] - seg['start']) <= 15
]
```

## 문제 해결

### FFmpeg 설치 오류
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows: https://ffmpeg.org/download.html에서 다운로드
```

### OpenAI Whisper 오류
- CUDA가 필요한 경우: `pip install openai-whisper[cuda]`
- 초기 실행 시 모델 다운로드 필요 (1.5GB)

### DeepL API 오류
- API 키 확인: `echo $DEEPL_API_KEY`
- API 할당량 초과 확인
- Free 플랜으로는 월 50만 자 제한

### 폰트 렌더링 오류
- `pip install Pillow --upgrade`
- 시스템 폰트 경로 확인

## 라이선스 및 주의사항

- 유튜브 약관 준수: 다운로드한 콘텐츠는 개인 사용만 가능합니다
- 저작권: 원본 저작자의 권리를 존중해주세요
- API 비용: DeepL 사용량에 따라 비용이 발생할 수 있습니다
