#!/usr/bin/env python3
"""
Diagnostic tool: Analyze why Claude only detects 2 moments instead of 6-8

This script analyzes:
1. Transcript distribution (begin/middle/end coverage)
2. Where the 12K cutoff falls in the content
3. Whether important political moments are missed due to truncation
4. Recommendations for improving moment detection
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import logging
import re
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_transcript_segments(transcript: str, max_length: int = 12000) -> Dict:
    """
    Analyze transcript and determine what Claude sees vs. what it misses
    """
    total_length = len(transcript)
    coverage_pct = (max_length / total_length) * 100 if total_length > 0 else 0

    # Split into segments
    visible_part = transcript[:max_length]
    hidden_part = transcript[max_length:]

    # Analyze sentence distribution
    visible_sentences = [s.strip() for s in re.split(r'[.!?]+', visible_part) if s.strip()]
    hidden_sentences = [s.strip() for s in re.split(r'[.!?]+', hidden_part) if s.strip()]

    # Find political/viral keywords
    political_keywords = [
        'asiel', 'migratie', 'crisis', 'onderzoek', 'beleid', 'minister',
        'regering', 'verkiezingen', 'politiek', 'debat', 'probleem',
        'oplossing', 'data', 'cijfers', 'percentage'
    ]

    def count_keywords(text: str, keywords: List[str]) -> Dict[str, int]:
        text_lower = text.lower()
        return {kw: text_lower.count(kw) for kw in keywords if text_lower.count(kw) > 0}

    visible_keywords = count_keywords(visible_part, political_keywords)
    hidden_keywords = count_keywords(hidden_part, political_keywords)

    # Find strong statement patterns (quotable moments)
    strong_patterns = [
        r'\b(als je kijkt naar|het feit is|de waarheid is|het probleem is)\b',
        r'\b(ik denk dat|ik vind|volgens mij|naar mijn mening)\b',
        r'\b(\d+\s*procent|\d+\s*miljoen|\d+\s*duizend)\b',  # Numbers/stats
        r'\b(moet|moeten|kunnen|zouden|zou)\b'  # Modal verbs (arguments)
    ]

    def find_strong_moments(text: str) -> int:
        count = 0
        for pattern in strong_patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        return count

    visible_strong = find_strong_moments(visible_part)
    hidden_strong = find_strong_moments(hidden_part)

    return {
        'total_length': total_length,
        'max_length': max_length,
        'coverage_pct': coverage_pct,
        'visible_sentences': len(visible_sentences),
        'hidden_sentences': len(hidden_sentences),
        'visible_keywords': visible_keywords,
        'hidden_keywords': hidden_keywords,
        'visible_strong_moments': visible_strong,
        'hidden_strong_moments': hidden_strong,
        'visible_part_preview': visible_part[-200:],  # Last 200 chars of visible
        'hidden_part_preview': hidden_part[:200] if hidden_part else ""  # First 200 chars of hidden
    }

def main():
    """Run transcript analysis"""
    # Simulate transcript from test (we'll get it from test run)
    logger.info("🔍 TRANSCRIPT COVERAGE ANALYSIS")
    logger.info("=" * 80)

    # Get transcript from test run
    from agents2.audio_processing.audio_transcriber import FastAudioTranscriber

    job_id = 'bfed5c2b-1b60-44a5-a776-abc8b377af27'
    video_path = f'./io/input/{job_id}/video_1751933560.mp4'

    # Check if files exist
    if not os.path.exists(video_path):
        logger.error(f"❌ Video not found: {video_path}")
        logger.info("ℹ️  This diagnostic requires the test video to be present")
        logger.info("ℹ️  The analysis will show:")
        logger.info("   1. What % of transcript Claude sees (current: 55%)")
        logger.info("   2. Whether important political moments are in the hidden 45%")
        logger.info("   3. Recommendations for improving detection")
        logger.info("")
        logger.info("📊 EXPECTED OUTCOME:")
        logger.info("   - If hidden part has more political keywords → increase max_transcript_length")
        logger.info("   - If visible part already has good coverage → improve prompts/thresholds")
        logger.info("   - If video truly has only 2 viral moments → detection is correct")
        return

    logger.info(f"📹 Transcribing: {video_path}")
    transcriber = FastAudioTranscriber()

    result = transcriber.transcribe_audio({
        "video_path": video_path,
        "method": "auto"
    })

    if not result.get('success'):
        logger.error(f"❌ Transcription failed: {result.get('error')}")
        return

    transcript = result['transcript']
    logger.info(f"✅ Transcript loaded: {len(transcript)} chars")
    logger.info("")

    # Analyze with current settings (12K)
    logger.info("📊 ANALYSIS WITH CURRENT SETTINGS (12K limit)")
    logger.info("-" * 80)

    analysis_12k = analyze_transcript_segments(transcript, 12000)

    logger.info(f"Total transcript length: {analysis_12k['total_length']} chars")
    logger.info(f"Claude sees (max_length): {analysis_12k['max_length']} chars")
    logger.info(f"Coverage: {analysis_12k['coverage_pct']:.1f}%")
    logger.info("")

    logger.info(f"📝 SENTENCE DISTRIBUTION:")
    logger.info(f"   Visible sentences: {analysis_12k['visible_sentences']}")
    logger.info(f"   Hidden sentences: {analysis_12k['hidden_sentences']}")
    logger.info(f"   Hidden %: {(analysis_12k['hidden_sentences'] / (analysis_12k['visible_sentences'] + analysis_12k['hidden_sentences']) * 100):.1f}%")
    logger.info("")

    logger.info(f"🔑 POLITICAL KEYWORDS:")
    logger.info(f"   Visible part: {sum(analysis_12k['visible_keywords'].values())} occurrences")
    for kw, count in sorted(analysis_12k['visible_keywords'].items(), key=lambda x: -x[1])[:5]:
        logger.info(f"      - {kw}: {count}x")
    logger.info(f"   Hidden part: {sum(analysis_12k['hidden_keywords'].values())} occurrences")
    for kw, count in sorted(analysis_12k['hidden_keywords'].items(), key=lambda x: -x[1])[:5]:
        logger.info(f"      - {kw}: {count}x")
    logger.info("")

    logger.info(f"💪 STRONG STATEMENT PATTERNS:")
    logger.info(f"   Visible: {analysis_12k['visible_strong_moments']} patterns")
    logger.info(f"   Hidden: {analysis_12k['hidden_strong_moments']} patterns")
    logger.info("")

    logger.info(f"📍 CUTOFF POINT PREVIEW:")
    logger.info(f"   Last visible text: ...{analysis_12k['visible_part_preview']}")
    logger.info(f"   First hidden text: {analysis_12k['hidden_part_preview']}...")
    logger.info("")

    # Compare with full coverage
    analysis_full = analyze_transcript_segments(transcript, len(transcript))

    hidden_keyword_ratio = sum(analysis_12k['hidden_keywords'].values()) / max(1, sum(analysis_full['visible_keywords'].values()))
    hidden_strong_ratio = analysis_12k['hidden_strong_moments'] / max(1, analysis_full['visible_strong_moments'])

    logger.info("=" * 80)
    logger.info("🎯 DIAGNOSIS:")
    logger.info("-" * 80)

    if hidden_keyword_ratio > 0.3:
        logger.info(f"⚠️  SIGNIFICANT CONTENT LOSS: {hidden_keyword_ratio:.1%} of political keywords are hidden")
        logger.info(f"   Recommendation: Increase max_transcript_length to {int(analysis_12k['total_length'] * 0.8)} (80% coverage)")
    elif hidden_keyword_ratio > 0.15:
        logger.info(f"⚠️  MODERATE CONTENT LOSS: {hidden_keyword_ratio:.1%} of political keywords are hidden")
        logger.info(f"   Recommendation: Consider increasing to {int(analysis_12k['total_length'] * 0.7)} (70% coverage)")
    else:
        logger.info(f"✅ GOOD COVERAGE: Only {hidden_keyword_ratio:.1%} of political keywords are hidden")
        logger.info(f"   Current 55% coverage seems adequate for this content")

    logger.info("")

    if hidden_strong_ratio > 0.3:
        logger.info(f"⚠️  MANY STRONG MOMENTS MISSED: {hidden_strong_ratio:.1%} of quotable patterns hidden")
        logger.info(f"   Root cause: Transcript truncation")
    else:
        logger.info(f"✅ Strong moments well-covered: {(1-hidden_strong_ratio):.1%} are visible to Claude")

    logger.info("")
    logger.info("🔧 RECOMMENDATIONS:")
    logger.info("-" * 80)

    if hidden_keyword_ratio > 0.2 or hidden_strong_ratio > 0.2:
        logger.info("1. INCREASE max_transcript_length")
        logger.info(f"   Current: 12,000 chars (55% coverage)")
        logger.info(f"   Recommended: {int(analysis_12k['total_length'] * 0.8)} chars (80% coverage)")
        logger.info(f"   Cost impact: Minimal (Claude Haiku has 200K context window)")
        logger.info("")
        logger.info("2. VERIFY after increase:")
        logger.info(f"   python test_pipeline_run.py")
        logger.info(f"   Expected: 4-6 clips (up from 2)")
    else:
        logger.info("1. CURRENT COVERAGE IS GOOD (55%)")
        logger.info("   Problem is likely NOT truncation")
        logger.info("")
        logger.info("2. POTENTIAL ROOT CAUSES:")
        logger.info("   a) Video content genuinely has only 2 viral moments")
        logger.info("   b) Claude prompts need tuning for political content")
        logger.info("   c) Thresholds are too strict (min_conf=0.15)")
        logger.info("")
        logger.info("3. NEXT STEPS:")
        logger.info("   a) Review Claude's response to see what it considered")
        logger.info("   b) Lower min_conf to 0.10 for political content")
        logger.info("   c) Check if video is genuinely low-viral (discussion vs. debate)")

    logger.info("")
    logger.info("=" * 80)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
