#!/usr/bin/env python3
"""
Direct test: Skip transcription, go straight to moment detection with chunking
"""

import os
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("AGENTOS MOMENT DETECTION + CHUNKING TEST")
print("=" * 80)
print(f"Job ID: 5c310509-9c75-4aa7-ab38-dad1c11bc885")
print()

# Paths
job_id = "5c310509-9c75-4aa7-ab38-dad1c11bc885"
input_dir = project_root / f"io/input/{job_id}"
video_path = input_dir / "video_1760376591.mp4"
audio_path = input_dir / "video_1760376591_audio.mp3"

print(f"📂 Input directory: {input_dir}")
print(f"🎬 Video: {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.1f}MB)")
print(f"🎵 Audio: {audio_path.name} ({audio_path.stat().st_size / 1024 / 1024:.1f}MB)")
print()

# Step 1: Create transcript using faster-whisper
print("🎤 STEP 1: Audio Transcription")
print("-" * 80)

from agents2.audio_processing.audio_transcriber import FastAudioTranscriber

transcript_file = input_dir / "transcript.txt"

if transcript_file.exists():
    print(f"✅ Transcript already exists: {transcript_file}")
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()
else:
    print("Starting faster-whisper transcription...")
    transcriber = FastAudioTranscriber()

    try:
        result = transcriber.process_video_safely(str(video_path))

        if result.get('success'):
            transcript = result.get('transcript', '')

            # Save transcript
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(transcript)

            print(f"✅ Transcription complete: {len(transcript)} characters")
            print(f"   Saved to: {transcript_file}")
        else:
            print(f"❌ Transcription failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

transcript_length = len(transcript)
word_count = len(transcript.split())
print(f"\n📊 Transcript Stats:")
print(f"   Length: {transcript_length:,} characters")
print(f"   Words: {word_count:,}")
print(f"   Estimated tokens: ~{transcript_length // 4:,}")

print()

# Step 2: Test Adaptive Chunking Threshold
print("📊 STEP 2: Adaptive Chunking Threshold Analysis")
print("-" * 80)

from agents2.moment_detection.unified_content_analyzer import UnifiedContentAnalyzer

analyzer = UnifiedContentAnalyzer()

# Calculate threshold
chunking_threshold = analyzer._compute_chunking_threshold()
estimated_tokens = analyzer._estimate_tokens_from_chars(transcript_length)
safe_budget_tokens = analyzer._safe_input_budget_tokens()
safe_budget_chars = safe_budget_tokens * 4

print(f"Configuration:")
print(f"  CHUNK_SIZE: {analyzer.chunk_size}")
print(f"  CHUNK_OVERLAP: {analyzer.chunk_overlap} ({analyzer.chunk_overlap / analyzer.chunk_size * 100:.0f}%)")
print(f"  MODEL_CONTEXT_TOKENS: {int(os.getenv('MODEL_CONTEXT_TOKENS', '128000')):,}")
print(f"  INPUT_UTILIZATION: {float(os.getenv('INPUT_UTILIZATION', '0.8')):.0%}")
print()

print(f"Calculated Thresholds:")
print(f"  Base threshold: {int(analyzer.chunk_size * 0.95):,} chars (chunk_size * 0.95)")
print(f"  Safe budget: {safe_budget_tokens:,} tokens = {safe_budget_chars:,} chars")
print(f"  Final threshold: {chunking_threshold:,} chars")
print()

print(f"This Video:")
print(f"  Transcript: {transcript_length:,} chars (~{estimated_tokens:,} tokens)")
print(f"  Decision: ", end="")

use_chunking = transcript_length > chunking_threshold

if use_chunking:
    print(f"🚀 USE CHUNKING (transcript > {chunking_threshold:,})")
    chunks_needed = (transcript_length - analyzer.chunk_overlap) // (analyzer.chunk_size - analyzer.chunk_overlap) + 1
    print(f"  Expected chunks: ~{chunks_needed}")
else:
    print(f"📄 SINGLE-PASS (transcript ≤ {chunking_threshold:,})")

print()

# Step 3: Run Moment Detection with Chunking
print("🎬 STEP 3: Moment Detection with Adaptive Chunking")
print("-" * 80)

youtube_metadata = {
    'title': 'JESSE KLAVER en MONA KEIJZER in DEBAT over de WONINGNOOD | Pauw & De Wit',
    'uploader': 'Pauw & De Wit',
    'upload_date': '20251010',
    'duration': 1106,
    'webpage_url': 'https://www.youtube.com/watch?v=Z9T9zCkB6c0',
    'view_count': 128028,
    'description': 'Debat over woningnood tussen Jesse Klaver en Mona Keijzer'
}

processing_constraints = {
    'target_clip_count': 6,
    'min_duration': 25,
    'max_duration': 45,
    'target_len': 30
}

print(f"Calling analyze_content()...")
print(f"  Metadata: {youtube_metadata['title']}")
print(f"  Target clips: {processing_constraints['target_clip_count']}")
print()

try:
    result = analyzer.analyze_content(
        youtube_metadata=youtube_metadata,
        transcript=transcript,
        processing_constraints=processing_constraints
    )

    print("✅ Moment Detection Complete!")
    print()

    # Display results
    if result.get('success'):
        moments = result.get('viral_moments', [])
        print(f"📊 Results:")
        print(f"   Found {len(moments)} moments")

        if use_chunking:
            print(f"   Method: TranscriptChunker (sliding window)")

            # Check for chunking metadata
            if 'chunking_stats' in result:
                stats = result['chunking_stats']
                print(f"   Chunks processed: {stats.get('chunks_processed', 'N/A')}")
                print(f"   Total tokens: {stats.get('total_tokens', 'N/A'):,}")
                print(f"   Cost: ${stats.get('total_cost', 0):.4f}")
        else:
            print(f"   Method: Single-pass analysis")

        print()
        print("Top 3 Moments:")
        for i, moment in enumerate(moments[:3], 1):
            print(f"  {i}. [{moment['start_time']:.1f}s - {moment['end_time']:.1f}s]")
            print(f"     Confidence: {moment.get('confidence', 0):.2f}")
            print(f"     Type: {moment.get('moment_type', 'unknown')}")
            print(f"     Phrase: {moment.get('key_phrase', 'N/A')[:60]}...")

        # Save results
        output_file = input_dir / "moment_detection_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print()
        print(f"💾 Results saved to: {output_file}")

    else:
        print(f"❌ Moment detection failed: {result.get('error', 'Unknown error')}")

except Exception as e:
    print(f"❌ Error during moment detection: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 80)
print("✅ ADAPTIVE CHUNKING TEST COMPLETE")
print("=" * 80)
