#!/usr/bin/env python3
"""
Live Test: TranscriptChunker met echte YouTube video

Test URL: https://www.youtube.com/watch?v=S7bT_CrS1Io
Video: Mehdi - Gaza Doctors (50 min)

Focus:
- Chunking behavior (10K/1K sliding window)
- Prompt caching effectiveness
- Cost tracking
- Deduplication
- Timestamp accuracy
"""

import os
import sys
import json
import logging
import time
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env loaded")
except ImportError:
    print("⚠️ python-dotenv not installed, loading .env manually")
    # Manual .env loading
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
        print(f"✅ .env loaded manually from {env_path}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_chunker_live.log')
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents2.moment_detection.transcript_chunker import TranscriptChunker


def download_video_and_transcript(video_url: str, output_dir: str = "test_data"):
    """
    Download YouTube video and extract transcript

    Returns:
        {
            'video_path': str,
            'transcript_path': str,
            'metadata': dict
        }
    """
    import subprocess

    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"📥 Downloading video: {video_url}")

    # Download video + subtitles
    output_template = f"{output_dir}/%(id)s.%(ext)s"

    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--write-sub",
        "--sub-lang", "en",
        "--convert-subs", "srt",
        "--write-info-json",
        "-f", "best[height<=720]",  # Lower quality to save time
        "-o", output_template,
        video_url
    ]

    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"yt-dlp failed: {result.stderr}")
        raise RuntimeError(f"Failed to download video: {result.stderr}")

    logger.info("✅ Download complete")

    # Find downloaded files
    video_id = video_url.split("v=")[-1]
    video_files = list(Path(output_dir).glob(f"{video_id}.*"))

    video_path = None
    subtitle_path = None
    info_path = None

    for f in video_files:
        if f.suffix in ['.mp4', '.webm', '.mkv']:
            video_path = str(f)
        elif f.suffix in ['.srt', '.vtt']:
            subtitle_path = str(f)
        elif f.suffix == '.json' and 'info' in f.name:
            info_path = str(f)

    # Load metadata
    metadata = {}
    if info_path:
        with open(info_path, 'r', encoding='utf-8') as f:
            info = json.load(f)
            metadata = {
                'title': info.get('title', 'Unknown'),
                'description': info.get('description', ''),
                'channel_name': info.get('channel', 'Unknown'),
                'duration': info.get('duration', 0),
                'upload_date': info.get('upload_date', ''),
                'view_count': info.get('view_count', 0)
            }

    logger.info(f"📹 Video: {video_path}")
    logger.info(f"📝 Subtitles: {subtitle_path}")
    logger.info(f"📊 Metadata: {metadata}")

    return {
        'video_path': video_path,
        'subtitle_path': subtitle_path,
        'metadata': metadata
    }


def parse_srt_to_text(srt_path: str) -> str:
    """
    Parse SRT file to plain text transcript

    Args:
        srt_path: Path to SRT file

    Returns:
        Plain text transcript
    """
    if not srt_path or not os.path.exists(srt_path):
        logger.warning(f"⚠️ Subtitle file not found: {srt_path}")
        return ""

    logger.info(f"📄 Parsing SRT: {srt_path}")

    with open(srt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    transcript_lines = []
    for line in lines:
        line = line.strip()
        # Skip empty lines, sequence numbers, and timestamps
        if not line or line.isdigit() or '-->' in line:
            continue
        transcript_lines.append(line)

    transcript = ' '.join(transcript_lines)

    logger.info(f"📏 Transcript length: {len(transcript)} chars, {len(transcript.split())} words")

    return transcript


def test_chunker(video_url: str):
    """
    Complete end-to-end test van TranscriptChunker
    """
    logger.info("=" * 80)
    logger.info("🧪 TRANSCRIPT CHUNKER LIVE TEST")
    logger.info("=" * 80)
    logger.info(f"Video URL: {video_url}")
    logger.info("")

    # 1. Download video + transcript
    logger.info("PHASE 1: Download & Extract")
    logger.info("-" * 80)

    try:
        download_result = download_video_and_transcript(video_url)
        transcript = parse_srt_to_text(download_result['subtitle_path'])
        metadata = download_result['metadata']
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return

    if not transcript:
        logger.error("❌ No transcript found")
        return

    logger.info(f"✅ Transcript extracted: {len(transcript)} chars")
    logger.info("")

    # 2. Setup constraints
    logger.info("PHASE 2: Setup Constraints")
    logger.info("-" * 80)

    constraints = {
        'min_duration': 15,
        'max_duration': 60,
        'max_moments': 5,
        'video_duration': metadata.get('duration', 3000),
        'words_per_minute': 160,  # Typical speaking speed
        'dedup_threshold_s': 2.0
    }

    logger.info(f"Constraints: {json.dumps(constraints, indent=2)}")
    logger.info("")

    # 3. Initialize Chunker
    logger.info("PHASE 3: Initialize TranscriptChunker")
    logger.info("-" * 80)

    chunker = TranscriptChunker()

    logger.info(f"Model: {chunker.model_name}")
    logger.info(f"Chunk size: {chunker.chunk_size}")
    logger.info(f"Overlap: {chunker.overlap_size}")
    logger.info(f"Rate limit: {chunker.rate_limit_per_min}/min")
    logger.info(f"Batch size: {chunker.batch_size}")
    logger.info("")

    # 4. Test chunking (dry run)
    logger.info("PHASE 4: Test Chunking (Dry Run)")
    logger.info("-" * 80)

    chunks = chunker.chunk_transcript(transcript)

    logger.info(f"✅ Created {len(chunks)} chunks")
    logger.info("")
    logger.info("Chunk Details:")
    for i, chunk in enumerate(chunks[:5]):  # Show first 5
        logger.info(f"  Chunk {chunk.chunk_id}:")
        logger.info(f"    - Offset: {chunk.start_offset:,} - {chunk.end_offset:,}")
        logger.info(f"    - Length: {len(chunk.text):,} chars")
        logger.info(f"    - Preview: {chunk.text[:100]}...")

    if len(chunks) > 5:
        logger.info(f"  ... and {len(chunks) - 5} more chunks")

    logger.info("")

    # 5. Estimate cost
    logger.info("PHASE 5: Cost Estimation")
    logger.info("-" * 80)

    # Rough token estimate (4 chars ≈ 1 token)
    avg_chunk_tokens = chunker.chunk_size // 4
    instruction_tokens = 500  # Rough estimate for instruction block

    first_chunk_cost = (avg_chunk_tokens + instruction_tokens) * 0.25 / 1_000_000
    cache_read_cost = instruction_tokens * 0.03 / 1_000_000
    remaining_chunk_cost = (avg_chunk_tokens * 0.25 / 1_000_000) + cache_read_cost

    estimated_cost = first_chunk_cost + (len(chunks) - 1) * remaining_chunk_cost

    logger.info(f"Estimated cost (with caching):")
    logger.info(f"  - First chunk: ${first_chunk_cost:.4f}")
    logger.info(f"  - Per chunk (2+): ${remaining_chunk_cost:.4f}")
    logger.info(f"  - Total estimated: ${estimated_cost:.2f}")
    logger.info("")

    # 6. Run full analysis
    logger.info("PHASE 6: Full Analysis (WITH API CALLS)")
    logger.info("-" * 80)
    logger.info("⚠️  This will make actual Anthropic API calls and incur costs!")
    logger.info("")

    # Check for API key
    if not os.getenv('ANTHROPIC_API_KEY'):
        logger.error("❌ ANTHROPIC_API_KEY not set - cannot proceed")
        logger.info("Set API key: export ANTHROPIC_API_KEY='your-key-here'")
        return

    logger.info("🚀 Starting analysis...")
    start_time = time.time()

    result = chunker.analyze_long_transcript(
        transcript=transcript,
        metadata=metadata,
        constraints=constraints
    )

    duration = time.time() - start_time

    logger.info("")
    logger.info("=" * 80)
    logger.info("📊 RESULTS")
    logger.info("=" * 80)

    if result['success']:
        logger.info("✅ Analysis successful!")
        logger.info("")

        logger.info(f"Moments Detected: {len(result['moments'])}")
        logger.info(f"Chunks Processed: {result['chunks_processed']}")
        logger.info(f"Chunks Succeeded: {result['chunks_succeeded']}")
        logger.info(f"Chunks Failed: {result['chunks_failed']}")
        logger.info(f"Duration: {result['duration_s']:.1f}s")
        logger.info("")

        logger.info("💰 Cost Analysis:")
        cost = result['cost']
        logger.info(f"  - Total Cost: ${cost['total_cost']:.4f}")
        logger.info(f"  - Cost per Chunk: ${cost['cost_per_chunk']:.4f}")
        logger.info(f"  - Cache Hit Rate: {cost['cache_hit_rate']:.1%}")
        logger.info("")

        logger.info("🔢 Token Counts:")
        tokens = cost['token_counts']
        logger.info(f"  - Input tokens: {tokens['input']:,}")
        logger.info(f"  - Output tokens: {tokens['output']:,}")
        logger.info(f"  - Cache creation: {tokens['cache_creation']:,}")
        logger.info(f"  - Cache reads: {tokens['cache_read']:,}")
        logger.info("")

        logger.info("🔄 Deduplication:")
        logger.info(f"  - Before: {result['moments_before_dedup']} moments")
        logger.info(f"  - After: {result['moments_after_dedup']} moments")
        logger.info(f"  - Removed: {result['moments_before_dedup'] - result['moments_after_dedup']} duplicates")
        logger.info("")

        logger.info("🎬 Top Moments:")
        for i, moment in enumerate(result['moments'][:5], 1):
            logger.info(f"  {i}. [{moment['start_time']:.1f}s - {moment['end_time']:.1f}s] Score: {moment['viral_score']}")
            logger.info(f"     Type: {moment['moment_type']}")
            logger.info(f"     Key: \"{moment.get('key_phrase', 'N/A')[:80]}...\"")
            logger.info("")

        # Save results
        output_file = 'test_chunker_results.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"💾 Full results saved to: {output_file}")

    else:
        logger.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")

    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST COMPLETE")
    logger.info("=" * 80)


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=S7bT_CrS1Io"
    test_chunker(video_url)
