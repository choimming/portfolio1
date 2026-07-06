#!/usr/bin/env python3
"""
테스트용 YouTube 쇼츠 생성 스크립트
- DeepL 없이 일본어 자막으로 실행
- 첫 번째 채널의 최신 영상 1개만 처리
"""
import os
import json
from pathlib import Path
from datetime import datetime
import shutil

import yt_dlp
import whisper
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import ffmpeg

OUTPUT_DIR = Path("output")
TEMP_DIR = Path("temp")
LINKS_FILE = Path("links.txt")
LOG_FILE = Path("test.log")

OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

def log_msg(msg):
    """로그 출력"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{ts}] {msg}\n")

def get_channel_url():
    """첫 번째 채널 URL 가져오기"""
    with open(LINKS_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                return line
    return None

def get_latest_video(channel_url):
    """채널의 최신 영상 1개 가져오기"""
    log_msg(f"📺 채널에서 최신 영상 찾는 중: {channel_url}")

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlistend': 1,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)

            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
                return {
                    'url': f"https://www.youtube.com/watch?v={entry['id']}",
                    'title': entry.get('title', 'Unknown')
                }
    except Exception as e:
        log_msg(f"❌ 오류: {e}")

    return None

def download_youtube(url, output_path):
    """유튜브 비디오 다운로드"""
    log_msg(f"⬇️  다운로드 중: {url}")

    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        log_msg(f"❌ 다운로드 실패: {e}")
        return None

def extract_audio(video_path, audio_path):
    """오디오 추출"""
    log_msg(f"🔊 오디오 추출 중...")

    try:
        stream = ffmpeg.input(str(video_path))
        stream = ffmpeg.output(stream, str(audio_path), acodec='pcm_s16le', ac=1, ar=16000)
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, quiet=True)
        return True
    except Exception as e:
        log_msg(f"❌ 오디오 추출 실패: {e}")
        return False

def transcribe_audio(audio_path):
    """Whisper로 음성 인식"""
    log_msg(f"🎤 Whisper로 일본어 음성 인식 중... (첫 로드 시 모델 다운로드)")

    try:
        model = whisper.load_model("base")
        result = model.transcribe(str(audio_path), language="ja")

        segments = []
        for seg in result['segments']:
            segments.append({
                'start': seg['start'],
                'end': seg['end'],
                'text': seg['text'],
            })

        log_msg(f"✅ {len(segments)}개 구간 인식 완료")
        return segments
    except Exception as e:
        log_msg(f"❌ 음성 인식 실패: {e}")
        return []

def crop_to_vertical(video_path, output_path, start_time, duration, width=1080, height=1920):
    """9:16 세로 포맷으로 크롭"""
    log_msg(f"✂️  9:16 세로 크롭 중...")

    try:
        probe = ffmpeg.probe(str(video_path))
        video_info = next(s for s in probe['streams'] if s['type'] == 'video')
        orig_width = video_info['width']
        orig_height = video_info['height']

        crop_width = min(int(orig_height * 9 / 16), orig_width)
        crop_height = orig_height
        x_offset = (orig_width - crop_width) // 2

        stream = ffmpeg.input(str(video_path), ss=start_time, t=duration)
        stream = ffmpeg.filter(stream, 'crop', crop_width, crop_height, x_offset, 0)
        stream = ffmpeg.filter(stream, 'scale', width, height)
        stream = ffmpeg.output(stream, str(output_path), vcodec='libx264', acodec='aac')
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, quiet=True)

        return True
    except Exception as e:
        log_msg(f"❌ 크롭 실패: {e}")
        return False

def add_subtitles(video_path, output_path, text_ja, position='bottom'):
    """일본어 자막 추가"""
    log_msg(f"📝 일본어 자막 추가 중...")

    try:
        cap = cv2.VideoCapture(str(video_path))

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        # Noto Sans 폰트
        font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"

        font_size = int(height * 0.08)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(frame_pil)

            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()

            text_y = height - font_size - int(height * 0.05)

            lines = text_ja.split('\n')
            for i, line in enumerate(lines):
                y_offset = text_y + (i * int(font_size * 1.2))

                bbox = draw.textbbox((0, y_offset), line, font=font)
                box_margin = 10
                draw.rectangle(
                    [bbox[0] - box_margin, bbox[1] - box_margin,
                     bbox[2] + box_margin, bbox[3] + box_margin],
                    fill=(0, 0, 0, 200),
                    outline=(255, 255, 255)
                )

                draw.text((width // 2, y_offset), line, font=font,
                         fill=(255, 255, 255), anchor="mm")

            frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)
            out.write(frame)

        cap.release()
        out.release()

        return True
    except Exception as e:
        log_msg(f"❌ 자막 추가 실패: {e}")
        return False

def select_segments(segments, count=3):
    """재밌는 구간 선택 (5-15초)"""
    log_msg(f"🎬 재밌는 구간 3개 선택 중...")

    valid = [s for s in segments if 5 <= (s['end'] - s['start']) <= 15]

    if len(valid) < count:
        log_msg(f"⚠️  {len(valid)}개만 찾음 (필요: {count}개)")
        return valid[:count]

    step = len(valid) // count
    return [valid[i * step] for i in range(count)]

def main():
    log_msg("="*60)
    log_msg("🧪 테스트 모드 시작 (DeepL 없이, 일본어 자막)")
    log_msg("="*60)

    # 채널 URL 가져오기
    channel_url = get_channel_url()
    if not channel_url:
        log_msg("❌ links.txt에 채널이 없습니다")
        return

    log_msg(f"채널: {channel_url}\n")

    # 최신 영상 찾기
    video_info = get_latest_video(channel_url)
    if not video_info:
        log_msg("❌ 최신 영상을 찾을 수 없습니다")
        return

    log_msg(f"제목: {video_info['title']}\n")

    video_dir = TEMP_DIR / "test_video"
    video_dir.mkdir(exist_ok=True)

    # 1. 다운로드
    video_file = download_youtube(video_info['url'], video_dir)
    if not video_file:
        return

    # 2. 오디오 추출
    audio_file = video_dir / "audio.wav"
    if not extract_audio(video_file, audio_file):
        return

    # 3. 음성 인식
    segments = transcribe_audio(audio_file)
    if not segments:
        return

    log_msg("\n📝 인식된 자막:")
    for seg in segments[:5]:  # 처음 5개만 표시
        log_msg(f"  [{seg['start']:.1f}s] {seg['text']}")

    # 4. 구간 선택
    selected = select_segments(segments, count=3)
    if not selected:
        log_msg("❌ 적합한 구간이 없습니다")
        return

    log_msg(f"✅ 선택된 구간: {len(selected)}개\n")

    # 5. 각 구간별 쇼츠 생성
    for idx, seg in enumerate(selected, 1):
        log_msg(f"\n🎬 쇼츠 {idx}/3 생성 중 ({seg['start']:.1f}-{seg['end']:.1f}초)")

        # 크롭
        cropped = video_dir / f"cropped_{idx}.mp4"
        duration = seg['end'] - seg['start'] + 1
        crop_to_vertical(video_file, cropped, seg['start'], duration)

        # 자막 추가
        output_file = OUTPUT_DIR / f"test_shorts_{idx}.mp4"
        if add_subtitles(cropped, output_file, seg['text']):
            log_msg(f"✅ 저장됨: {output_file}")
        else:
            log_msg(f"❌ 실패: {output_file}")

    log_msg("\n" + "="*60)
    log_msg("🎉 테스트 완료!")
    log_msg(f"📁 출력: {OUTPUT_DIR}/")
    log_msg("="*60)

    # 정리
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
