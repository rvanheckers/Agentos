#!/usr/bin/env python3
"""
TikTok Video Transcriptie Script
Transcribeert audio van een TikTok video naar tekst
"""
from faster_whisper import WhisperModel
import os
import json
from pathlib import Path

def transcribe_video(video_path: str, output_path: str):
    """Transcribeer video naar tekst"""
    print(f"🎬 Loading Faster-Whisper model (small)...")
    model = WhisperModel("small", device="cpu", compute_type="int8")

    print(f"🎙️  Transcribing video: {video_path}")
    segments, info = model.transcribe(video_path)  # Auto-detect language

    # Verzamel segmenten
    result_segments = []
    full_text = ""
    for segment in segments:
        result_segments.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        full_text += segment.text + " "

    # Sla de volledige transcriptie op
    transcriptie_text = full_text.strip()

    # Sla ook de segmenten op met timestamps
    segments_text = ""
    for segment in result_segments:
        start = segment["start"]
        end = segment["end"]
        text = segment["text"]
        segments_text += f"[{start:.2f}s - {end:.2f}s] {text}\n"

    # Schrijf de transcriptie naar een bestand
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("TIKTOK VIDEO TRANSCRIPTIE\n")
        f.write("=" * 80 + "\n\n")
        f.write("VOLLEDIGE TRANSCRIPTIE:\n")
        f.write("-" * 80 + "\n")
        f.write(transcriptie_text + "\n\n")
        f.write("=" * 80 + "\n\n")
        f.write("TRANSCRIPTIE MET TIMESTAMPS:\n")
        f.write("-" * 80 + "\n")
        f.write(segments_text)
        f.write("\n" + "=" * 80 + "\n")

    # Sla ook JSON versie op
    json_output = output_path.replace('.txt', '.json')
    result_data = {
        "text": transcriptie_text,
        "segments": result_segments,
        "language": info.language,
        "duration": info.duration
    }
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Transcriptie opgeslagen in: {output_path}")
    print(f"✅ JSON data opgeslagen in: {json_output}")
    print(f"\n📝 Transcriptie preview:\n{transcriptie_text[:200]}...")

    return transcriptie_text

if __name__ == "__main__":
    video_file = "tiktok_video.mp4"
    output_file = "transcriptie.txt"

    if not os.path.exists(video_file):
        print(f"❌ Video bestand niet gevonden: {video_file}")
        exit(1)

    transcribe_video(video_file, output_file)
