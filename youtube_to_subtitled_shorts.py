#!/usr/bin/env python3
import os
import json
import subprocess
import tempfile
from pathlib import Path
import shutil

import yt_dlp
import whisper
import deepl
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ffmpeg

# Configuration
OUTPUT_DIR = Path("output")
TEMP_DIR = Path("temp")
LINKS_FILE = Path("links.txt")

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

def load_links():
    """links.txt에서 유튜브 링크 읽기"""
    if not LINKS_FILE.exists():
        print(f"Error: {LINKS_FILE} not found")
        return []

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    return links

def download_youtube(url, output_path):
    """유튜브 비디오 다운로드"""
    print(f"Downloading: {url}")

    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)
            return video_file
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def extract_audio(video_path, audio_path):
    """비디오에서 오디오 추출"""
    print(f"Extracting audio from {video_path}")

    try:
        stream = ffmpeg.input(str(video_path))
        stream = ffmpeg.output(stream, str(audio_path), acodec='pcm_s16le', ac=1, ar=16000)
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, quiet=True)
        return True
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return False

def transcribe_audio(audio_path):
    """Whisper로 일본어 음성 인식"""
    print(f"Transcribing audio: {audio_path}")

    try:
        model = whisper.load_model("base")
        result = model.transcribe(str(audio_path), language="ja")

        # 타이밍 정보와 함께 반환
        segments = []
        for seg in result['segments']:
            segments.append({
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'],
                'jp_text': seg['text']
            })

        return segments
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return []

def translate_to_korean(text):
    """DeepL로 일본어를 한국어로 번역"""
    try:
        # DeepL API 키가 환경변수에 설정되어 있어야 함
        api_key = os.environ.get('DEEPL_API_KEY')
        if not api_key:
            print("Warning: DEEPL_API_KEY not set")
            return text

        translator = deepl.Translator(api_key)
        result = translator.translate_text(text, source_lang="JA", target_lang="KO")
        return result.text
    except Exception as e:
        print(f"Error translating text: {e}")
        return text

def crop_to_vertical(video_path, output_path, start_time, duration, width=1080, height=1920):
    """비디오를 9:16 세로 포맷으로 크롭"""
    print(f"Cropping video to vertical format: {video_path}")

    try:
        # 원본 비디오 정보 읽기
        probe = ffmpeg.probe(str(video_path))
        video_info = next(s for s in probe['streams'] if s['type'] == 'video')
        orig_width = video_info['width']
        orig_height = video_info['height']

        # 중앙에서 크롭할 영역 계산
        crop_width = min(int(orig_height * 9 / 16), orig_width)
        crop_height = orig_height
        x_offset = (orig_width - crop_width) // 2

        # ffmpeg 커맨드로 크롭 및 스케일
        stream = ffmpeg.input(str(video_path), ss=start_time, t=duration)
        stream = ffmpeg.filter(stream, 'crop', crop_width, crop_height, x_offset, 0)
        stream = ffmpeg.filter(stream, 'scale', width, height)
        stream = ffmpeg.output(stream, str(output_path), vcodec='libx264', acodec='aac')
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, quiet=True)

        return True
    except Exception as e:
        print(f"Error cropping video: {e}")
        return False

def add_korean_subtitles(video_path, output_path, korean_text, position='bottom'):
    """한국어 자막을 비디오에 하드코딩"""
    print(f"Adding Korean subtitles to video")

    try:
        cap = cv2.VideoCapture(str(video_path))

        # 비디오 정보
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # VideoWriter 설정
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        # 폰트 설정 (Noto Sans, 필요시 다른 경로 사용)
        font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        if not os.path.exists(font_path):
            # 대체 경로들
            alt_paths = [
                "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
                "/System/Library/Fonts/Noto Sans CJK JP.otf",
                "C:\\Windows\\Fonts\\NotoSansCJK-Regular.ttc"
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    font_path = alt_path
                    break

        font_size = int(height * 0.08)  # 화면 높이의 8%

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # PIL로 자막 추가 (한글 지원)
            frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(frame_pil)

            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()

            # 자막 위치
            if position == 'bottom':
                text_y = height - font_size - int(height * 0.05)
            else:
                text_y = int(height * 0.1)

            # 자막 배경 박스와 텍스트
            text_color = (255, 255, 255)  # 흰색
            shadow_color = (0, 0, 0)  # 검은색 (가독성)

            # 멀티라인 자막 처리
            lines = korean_text.split('\n')
            for i, line in enumerate(lines):
                y_offset = text_y + (i * int(font_size * 1.2))

                # 배경 박스 (반투명 검은색)
                bbox = draw.textbbox((0, y_offset), line, font=font)
                box_margin = 10
                draw.rectangle(
                    [bbox[0] - box_margin, bbox[1] - box_margin,
                     bbox[2] + box_margin, bbox[3] + box_margin],
                    fill=(0, 0, 0, 128),
                    outline=(255, 255, 255)
                )

                # 텍스트 그리기
                draw.text((width // 2, y_offset), line, font=font, fill=text_color, anchor="mm")

            # PIL에서 OpenCV로 변환
            frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)
            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()
        return True
    except Exception as e:
        print(f"Error adding subtitles: {e}")
        return False

def select_interesting_segments(segments, count=3):
    """재밌는 구간 선택 (길이가 적당한 구간)"""
    print(f"Selecting {count} interesting segments")

    # 길이가 5-15초 사이인 구간을 선택
    valid_segments = [
        seg for seg in segments
        if 5 <= (seg['end'] - seg['start']) <= 15
    ]

    if len(valid_segments) < count:
        print(f"Warning: Only {len(valid_segments)} segments found, need {count}")
        selected = valid_segments[:count]
    else:
        # 고르게 분산된 구간 선택
        step = len(valid_segments) // count
        selected = [valid_segments[i * step] for i in range(count)]

    return selected

def process_video(video_url, video_index):
    """단일 비디오 처리"""
    print(f"\n{'='*60}")
    print(f"Processing video {video_index}")
    print(f"{'='*60}")

    video_dir = TEMP_DIR / f"video_{video_index}"
    video_dir.mkdir(exist_ok=True)

    # 1. 비디오 다운로드
    video_file = download_youtube(video_url, video_dir)
    if not video_file:
        return False

    # 2. 오디오 추출
    audio_file = video_dir / "audio.wav"
    if not extract_audio(video_file, audio_file):
        return False

    # 3. 음성 인식
    segments = transcribe_audio(audio_file)
    if not segments:
        print("No segments transcribed")
        return False

    # 4. 번역
    for seg in segments:
        korean_text = translate_to_korean(seg['jp_text'])
        seg['kr_text'] = korean_text
        print(f"[{seg['start']:.2f}-{seg['end']:.2f}] JP: {seg['jp_text']}")
        print(f"                KR: {korean_text}")

    # 5. 재밌는 구간 선택
    selected_segments = select_interesting_segments(segments, count=3)

    # 6. 각 구간별 쇼츠 생성
    for idx, seg in enumerate(selected_segments):
        print(f"\nCreating shorts {idx + 1}/3")

        # 6-1. 9:16 세로 크롭
        cropped_video = video_dir / f"cropped_{idx}.mp4"
        duration = seg['end'] - seg['start'] + 1  # 약간의 여유
        crop_to_vertical(video_file, cropped_video, seg['start'], duration)

        # 6-2. 한국어 자막 추가
        output_file = OUTPUT_DIR / f"shorts_{video_index}_{idx + 1}.mp4"
        add_korean_subtitles(cropped_video, output_file, seg['kr_text'])

        print(f"Saved: {output_file}")

    return True

def main():
    """메인 함수"""
    print("YouTube to Subtitled Shorts Converter")
    print(f"Reading links from: {LINKS_FILE}")

    links = load_links()
    if not links:
        print("No links found in links.txt")
        return

    print(f"Found {len(links)} links\n")

    # DeepL API 키 확인
    if not os.environ.get('DEEPL_API_KEY'):
        print("Warning: DEEPL_API_KEY environment variable not set")
        print("Set it with: export DEEPL_API_KEY='your-api-key'")

    # 각 링크 처리
    for idx, url in enumerate(links, 1):
        try:
            process_video(url, idx)
        except Exception as e:
            print(f"Error processing video {idx}: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"Processing complete! Output saved to: {OUTPUT_DIR}")
    print(f"{'='*60}")

    # 임시 파일 정리
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
