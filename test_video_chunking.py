#!/usr/bin/env python3
"""
Test Adaptive Chunking System met specifieke video
Test video: https://www.youtube.com/watch?v=Z9T9zCkB6c0
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("AGENTOS ADAPTIVE CHUNKING TEST")
print("=" * 80)
print(f"Video: https://www.youtube.com/watch?v=Z9T9zCkB6c0")
print(f"Task ID: 451deeb3-0804-4637-b77a-41b2710f8dbf")
print()

# Phase 1: Download video (if not already done)
print("📥 PHASE 1: Video Download")
print("-" * 80)

video_path = project_root / "io/input/451deeb3-0804-4637-b77a-41b2710f8dbf/video_1760374354.mp4.part"

if video_path.exists():
    size_mb = video_path.stat().st_size / (1024 * 1024)
    print(f"✅ Video already downloaded: {video_path}")
    print(f"   Size: {size_mb:.1f} MB")
else:
    print("❌ Video file not found at expected location")
    print(f"   Expected: {video_path}")
    sys.exit(1)

print()

# Phase 2: Extract audio and transcribe
print("🎵 PHASE 2: Audio Extraction & Transcription")
print("-" * 80)

from agents2.audio_processing.audio_transcriber import FastAudioTranscriber

# Check if transcript already exists
transcript_file = project_root / "io/input/451deeb3-0804-4637-b77a-41b2710f8dbf/transcript.txt"

if transcript_file.exists():
    print(f"✅ Transcript already exists: {transcript_file}")
    with open(transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()
else:
    print("Starting audio extraction and transcription...")
    transcriber = FastAudioTranscriber()

    try:
        result = transcriber.process_video_safely(str(video_path))
        transcript = result.get('text', result.get('transcript', ''))

        # Save transcript
        transcript_file.parent.mkdir(parents=True, exist_ok=True)
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(transcript)

        print(f"✅ Transcription complete: {len(transcript)} characters")
        print(f"   Saved to: {transcript_file}")
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
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

# Phase 3: Test Adaptive Chunking Threshold
print("📊 PHASE 3: Adaptive Chunking Threshold Analysis")
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

if transcript_length > chunking_threshold:
    print(f"🚀 USE CHUNKING (transcript > {chunking_threshold:,})")
    chunks_needed = (transcript_length - analyzer.chunk_overlap) // (analyzer.chunk_size - analyzer.chunk_overlap) + 1
    print(f"  Expected chunks: ~{chunks_needed}")
else:
    print(f"📄 SINGLE-PASS (transcript ≤ {chunking_threshold:,})")

print()

# Phase 4: Test Chunking Mechanics
if transcript_length > chunking_threshold:
    print("🔧 PHASE 4: Chunking Mechanics Test")
    print("-" * 80)

    from agents2.moment_detection.transcript_chunker import TranscriptChunker

    chunker = TranscriptChunker()

    print("Creating chunks...")
    chunks = chunker.chunk_transcript(transcript)

    print(f"✅ Created {len(chunks)} chunks\n")

    # Analyze chunks
    print("Chunk Analysis:")
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i}:")
        print(f"    Range: [{chunk.start_offset:,} - {chunk.end_offset:,}]")
        print(f"    Length: {len(chunk.text):,} chars")

        # Check overlap with previous chunk
        if i > 0:
            prev_chunk = chunks[i-1]
            overlap_start = chunk.start_offset
            overlap_end = prev_chunk.end_offset

            if overlap_end > overlap_start:
                overlap_size = overlap_end - overlap_start
                print(f"    Overlap with prev: {overlap_size:,} chars ({overlap_size / analyzer.chunk_size * 100:.1f}%)")
            else:
                print(f"    Gap from prev: {overlap_start - overlap_end:,} chars")

        # Check for sentence boundary snapping
        if chunk.boundary_snapped:
            print(f"    ✓ Snapped to sentence boundary")

    print()

    # Calculate expected cost
    print("💰 Expected Cost Analysis:")
    print(f"  Chunks to process: {len(chunks)}")
    print(f"  First chunk: Full cost (no cache)")
    print(f"  Remaining {len(chunks) - 1} chunks: Cache instruction block")
    print()

    # Haiku pricing (approximate)
    input_cost_per_mtok = 0.25  # $0.25 per MTok input
    cache_write_per_mtok = 0.30  # $0.30 per MTok cache write
    cache_read_per_mtok = 0.03   # $0.03 per MTok cache read
    output_cost_per_mtok = 1.25  # $1.25 per MTok output

    # Estimate instruction block size (conservative)
    instruction_tokens = 1500
    chunk_tokens = analyzer.chunk_size // 4
    output_tokens = 2000

    # First chunk: full cost + cache write
    first_chunk_cost = (
        (instruction_tokens + chunk_tokens) * input_cost_per_mtok / 1_000_000 +
        instruction_tokens * cache_write_per_mtok / 1_000_000 +
        output_tokens * output_cost_per_mtok / 1_000_000
    )

    # Remaining chunks: cache read + chunk input + output
    remaining_chunk_cost = (
        instruction_tokens * cache_read_per_mtok / 1_000_000 +
        chunk_tokens * input_cost_per_mtok / 1_000_000 +
        output_tokens * output_cost_per_mtok / 1_000_000
    )

    total_cost = first_chunk_cost + (len(chunks) - 1) * remaining_chunk_cost

    print(f"  Estimated cost breakdown:")
    print(f"    First chunk: ${first_chunk_cost:.4f}")
    print(f"    Per cached chunk: ${remaining_chunk_cost:.4f}")
    print(f"    Total estimated: ${total_cost:.2f}")

    # Compare with non-cached approach
    non_cached_cost = len(chunks) * (
        (instruction_tokens + chunk_tokens) * input_cost_per_mtok / 1_000_000 +
        output_tokens * output_cost_per_mtok / 1_000_000
    )
    savings = (1 - total_cost / non_cached_cost) * 100

    print(f"\n  Without caching: ${non_cached_cost:.2f}")
    print(f"  Savings: ${non_cached_cost - total_cost:.2f} ({savings:.0f}%)")

    print()

# Phase 5: Optional - Run full analysis with API
print("🤖 PHASE 5: Full Analysis (Optional)")
print("-" * 80)
print("To run full analysis with Claude API:")
print()
print("  from agents2.moment_detection.unified_content_analyzer import UnifiedContentAnalyzer")
print("  analyzer = UnifiedContentAnalyzer()")
print("  result = analyzer.analyze_content(")
print("      youtube_metadata={'title': 'Test Video', 'channel': 'Test', 'duration': 600},")
print("      transcript=transcript,")
print("      processing_constraints={'target_clip_count': 6}")
print("  )")
print()
print("⚠️  This will consume API tokens. Run manually if needed.")
print()

print("=" * 80)
print("✅ CHUNKING SYSTEM TEST COMPLETE")
print("=" * 80)
