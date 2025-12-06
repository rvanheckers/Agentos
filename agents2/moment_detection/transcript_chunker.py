#!/usr/bin/env python3
"""
Production-Grade Transcript Chunker v1.0
=========================================

Implements industry-standard transcript chunking for 3+ hour podcasts.
Based on TRANSCRIPT_CHUNKING_STRATEGY.md with expert-validated corrections.

KEY FEATURES:
- Sliding window (10K chunks, 1K overlap)
- Prompt caching (87% cost reduction: $7.50 → $0.98)
- Parallel processing with rate limiting
- Robust JSON parsing with bracket counting
- Timestamp mapping via words_per_minute
- Sentence boundary detection with max shift constraint
- Deduplication via timestamp + Jaccard similarity

CRITICAL FIXES APPLIED:
1. Prompt caching: Cache INVARIANT instruction block, not chunk text
2. Sentence boundary: Use max_shift = 10% of chunk_size (not percentage comparison)
3. JSON parsing: Bracket counting fallback for malformed responses
4. Timestamp mapping: Use words_per_minute (not arbitrary 0.01)

TARGET METRICS:
- Cost: <$1.00 per 3-hour video (with caching)
- Cache hit rate: >80% (after first chunk)
- Latency: <60s for 30 chunks
- Accuracy: 6-8 moments detected for 15-min videos

Author: AgentOS Development Team
Date: 2025-10-13
Version: 1.0.0
"""

import json
import logging
import os
import time
import threading
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

from agents2.base.secure_agent import SecureVideoAgent

logger = logging.getLogger(__name__)


@dataclass
class TranscriptChunk:
    """
    Single transcript chunk with metadata

    Attributes:
        chunk_id: Sequential identifier (0-indexed)
        text: Chunk text content
        start_offset: Character position in original transcript
        end_offset: Character position in original transcript
    """
    chunk_id: int
    text: str
    start_offset: int
    end_offset: int


class TranscriptChunker(SecureVideoAgent):
    """
    Production-grade transcript chunking for 3+ hour podcasts

    Implements sliding window with overlap, prompt caching, parallel processing,
    and intelligent moment deduplication.

    Architecture:
    - Chunk Creation: Sliding window with sentence boundary detection
    - Analysis: Parallel batch processing with rate limiting
    - Caching: Invariant instruction block cached across chunks
    - Deduplication: Timestamp overlap + Jaccard similarity
    - Result Merging: Sort by chunk_id to preserve temporal order

    Cost Model (3-hour video):
    - Transcript: 300,000 chars
    - Chunks: 30 chunks (10K each, 1K overlap)
    - First chunk: $0.25 (creates cache)
    - Remaining 29: $0.025 each = $0.725
    - Total: $0.98 (vs $7.50 without caching)
    """

    def __init__(
        self,
        model_name: str = None,
        chunk_size: int = None,
        overlap_size: int = None,
        max_tokens: int = None,
        temperature: float = None,
        top_p: float = None
    ):
        """
        Initialize transcript chunker with configurable parameters

        Args:
            model_name: Anthropic model (default: claude-3-haiku-20240307)
            chunk_size: Characters per chunk (default: 10000)
            overlap_size: Overlap between chunks (default: 1000)
            max_tokens: Max response tokens (default: 4000)
            temperature: Model temperature (default: 0.3)
            top_p: Model top_p (default: 0.95)
        """
        super().__init__()

        # Model configuration
        self.model_name = model_name or os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')
        self.max_tokens = max_tokens or int(os.getenv('ANTHROPIC_MAX_TOKENS', '4000'))
        self.temperature = temperature or float(os.getenv('ANTHROPIC_TEMP', '0.3'))
        self.top_p = top_p or float(os.getenv('ANTHROPIC_TOP_P', '0.95'))

        # Chunking configuration
        self.chunk_size = chunk_size or int(os.getenv('CHUNK_SIZE', '10000'))
        self.overlap_size = overlap_size or int(os.getenv('CHUNK_OVERLAP', '1000'))
        self.snap_start_boundary = os.getenv('SNAP_START_BOUNDARY', 'true').lower() in ('1', 'true', 'yes')

        # Rate limiting (50 requests/min for Anthropic)
        self.rate_limit_per_min = int(os.getenv('RATE_LIMIT_PER_MIN', '50'))
        self.batch_size = int(os.getenv('BATCH_SIZE', '5'))
        self.batch_delay_s = 60.0 / self.rate_limit_per_min * self.batch_size  # 6s for 5 chunks

        # Token tracking for cost calculation
        self.token_counts = {
            'input': 0,
            'output': 0,
            'cache_read': 0,
            'cache_creation': 0
        }
        self.token_lock = threading.Lock()

        # Initialize Anthropic client (lazy initialization to avoid blocking imports)
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        self._client_initialized = False

        logger.info(f"🤖 TranscriptChunker v1.0: {self.model_name}, chunk_size={self.chunk_size}, overlap={self.overlap_size}")

    def _truncate_for_budget(self, text: str, max_input_tokens: int = None) -> str:
        """
        Trim chunk text to prevent context overflow

        Uses conservative estimate: ~4 chars per token (English text).
        Leaves margin for system prompt, instructions, and response.

        Args:
            text: Chunk text to truncate
            max_input_tokens: Max input tokens (default: from env or 12000)

        Returns:
            Truncated text (or original if within budget)

        Example:
            max_tokens = 12000
            max_chars = 12000 * 4 = 48000 chars
            If chunk > 48000 chars → truncate to fit
        """
        if max_input_tokens is None:
            # Conservative default (model context minus system/instructions/output)
            max_input_tokens = int(os.getenv('MAX_INPUT_TOKENS_BUDGET', '12000'))

        approx_chars = max_input_tokens * 4  # ~4 chars per token

        if len(text) <= approx_chars:
            return text

        # Preserve more of the end (for sentence boundary context)
        # Trim middle hard
        head = text[:approx_chars - 500]
        tail = text[approx_chars - 500:approx_chars + 500]

        logger.warning(f"⚠️ Truncating chunk from {len(text)} to ~{approx_chars} chars (budget: {max_input_tokens} tokens)")

        return head + tail

    def _ensure_client(self):
        """Lazy initialization of Anthropic client"""
        if self._client_initialized:
            return

        self._client_initialized = True

        if self.anthropic_api_key and Anthropic:
            try:
                self.client = Anthropic(api_key=self.anthropic_api_key)
                logger.info("✅ Anthropic client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Anthropic client: {e}")
        else:
            logger.warning("⚠️ ANTHROPIC_API_KEY not found - chunker will not function")

    def chunk_transcript(self, transcript: str) -> List[TranscriptChunk]:
        """
        Split transcript into overlapping chunks with sentence boundary detection

        Algorithm:
        1. Calculate chunk positions with overlap
        2. Find nearest sentence boundary for each position
        3. Create TranscriptChunk objects with metadata

        Args:
            transcript: Full transcript text

        Returns:
            List of TranscriptChunk objects

        Example:
            transcript = "Hello world. This is a test. " * 1000  # 30K chars
            chunks = chunker.chunk_transcript(transcript)
            # Returns ~3 chunks: [0-10K], [9K-19K], [18K-28K]
        """
        if not transcript:
            return []

        chunks = []
        chunk_id = 0
        pos = 0

        while pos < len(transcript):
            # Calculate chunk boundaries
            start_pos = pos
            end_pos = min(pos + self.chunk_size, len(transcript))

            # Adjust start to sentence boundary (except first chunk)
            # Configurable via SNAP_START_BOUNDARY env var
            if self.snap_start_boundary and pos > 0:
                start_pos = self.find_sentence_boundary(
                    transcript,
                    pos,
                    window=min(200, self.overlap_size)
                )

            # Adjust end to sentence boundary (except last chunk)
            if end_pos < len(transcript):
                end_pos = self.find_sentence_boundary(
                    transcript,
                    end_pos,
                    window=200
                )

            # Create chunk
            chunk_text = transcript[start_pos:end_pos]
            if chunk_text.strip():  # Skip empty chunks
                chunks.append(TranscriptChunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    start_offset=start_pos,
                    end_offset=end_pos
                ))
                chunk_id += 1

            # Move to next position (with overlap)
            pos = end_pos - self.overlap_size

            # Prevent infinite loop if chunk is smaller than overlap
            if pos <= start_pos:
                pos = end_pos

        logger.info(f"📄 Chunked transcript: {len(transcript)} chars → {len(chunks)} chunks (overlap={self.overlap_size})")
        return chunks

    def find_sentence_boundary(self, text: str, pos: int, window: int = 200) -> int:
        """
        Find nearest sentence boundary within window of position

        CORRECTED IMPLEMENTATION:
        - Uses max_shift constraint (10% of chunk_size)
        - Compares absolute distances, not percentages
        - Prevents excessive boundary shifts

        Args:
            text: Full text
            pos: Target position
            window: Search window size (default: 200 chars)

        Returns:
            Adjusted position at sentence boundary, or original pos if none found

        Example:
            text = "Hello world. This is a test. More text here."
            pos = 15  # Middle of "This"
            boundary = find_sentence_boundary(text, pos, window=10)
            # Returns 13 (position after "world.")
        """
        sentence_ends = ['.', '!', '?', '\n']

        # Define search window
        search_start = max(0, pos - window)
        search_end = min(len(text), pos + window)
        search_text = text[search_start:search_end]

        # Find all sentence boundaries in window
        candidates = []
        for i, ch in enumerate(search_text):
            if ch in sentence_ends:
                # Check next char is whitespace or end of text
                abs_pos = search_start + i + 1
                if abs_pos >= len(text) or text[abs_pos].isspace():
                    candidates.append(abs_pos)

        if not candidates:
            return pos

        # Find closest candidate
        closest = min(candidates, key=lambda x: abs(x - pos))

        # CRITICAL FIX: Apply max shift constraint
        # Max shift = 10% of chunk_size (e.g., 1000 chars for 10K chunks)
        max_shift = int(0.1 * self.chunk_size)

        if abs(closest - pos) <= max_shift:
            return closest

        # Shift too large, use original position
        return pos

    def _build_instruction_block(self, metadata: Dict[str, Any], constraints: Dict[str, Any]) -> str:
        """
        Build INVARIANT instruction block for prompt caching

        CRITICAL: This block must be IDENTICAL across all chunks to enable caching.
        DO NOT include chunk-specific content here.

        Structure:
        1. Video metadata (constant)
        2. Task description (constant)
        3. Constraints (constant)
        4. Response format (constant)

        Args:
            metadata: Video metadata (title, description, channel)
            constraints: Processing constraints (duration, max_moments, etc.)

        Returns:
            Instruction text (will be cached after first chunk)
        """
        title = metadata.get('title', 'Unknown')
        description = metadata.get('description', '')[:300]
        channel = metadata.get('channel_name', metadata.get('uploader', 'Unknown'))

        # Extract constraints
        min_duration = float(constraints.get('min_duration', 15))
        max_duration = float(constraints.get('max_duration', 60))
        max_moments = int(constraints.get('max_moments', 5))
        video_duration = float(constraints.get('video_duration', 300))

        return f"""TRANSCRIPT CHUNKING ANALYZER - Instructions

VIDEO METADATA (constant across all chunks):
Title: {title}
Description: {description}
Channel: {channel}
Video Duration: {video_duration}s

TASK:
You are analyzing a CHUNK of a long podcast/video transcript. Your job is to:
1. Detect HIGH-IMPACT VIRAL MOMENTS within this chunk
2. Return exact timestamps relative to chunk start (0-based)
3. Focus on quotable, emotional, or surprising content
4. Avoid filler, intros, outros, sponsors, CTAs

CONSTRAINTS:
- Moment Duration: {min_duration}s - {max_duration}s
- Max Moments per Chunk: {max_moments}
- Video Total Duration: {video_duration}s

DETECTION RUBRICS:
✓ HOOKS: "Wait until you see", "You won't believe", "This changes everything"
✓ SURPRISES: Unexpected reveals, plot twists, shocking statements
✓ EMOTIONAL PEAKS: Passion, anger, laughter, cheering
✓ QUOTABLE LINES: Memorable, succinct, repeatable (max 120 chars)
✓ SOCIAL PROOF: Crowd reactions, "thousands", "everyone"

AVOID:
✗ Sponsor mentions, CTAs, merchandise
✗ Intro/outro segments
✗ Long-winded explanations
✗ Technical setup/housekeeping

REQUIRED JSON OUTPUT:
{{
  "chunk_moments": [
    {{
      "start_time": 10.5,
      "end_time": 25.0,
      "viral_score": 85,
      "moment_type": "powerful_quote|emotional_peak|surprise|hook",
      "key_phrase": "Verbatim quote from transcript (max 120 chars)",
      "engagement_drivers": ["emotional", "quotable", "surprising"]
    }}
  ]
}}

Return ONLY valid JSON. Timestamps are relative to chunk start (0-based).
Process the chunk below and detect moments:"""

    def _analyze_single_chunk(
        self,
        chunk: TranscriptChunk,
        metadata: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze single chunk with CORRECT prompt caching implementation

        CRITICAL CACHING PATTERN:
        - Instruction block (invariant) → cache_control: ephemeral
        - Chunk text (variant) → NO cache_control

        Result: First chunk creates cache, subsequent chunks read from cache.

        Args:
            chunk: TranscriptChunk to analyze
            metadata: Video metadata
            constraints: Processing constraints

        Returns:
            {
                'success': bool,
                'chunk_id': int,
                'moments': List[Dict],
                'error': str (if failed)
            }
        """
        try:
            # Build invariant instruction block (will be cached)
            system_prompt = "You are a viral moment detection AI. Return ONLY valid JSON."
            instruction_block = self._build_instruction_block(metadata, constraints)

            # Truncate chunk text for token budget
            safe_chunk_text = self._truncate_for_budget(chunk.text)

            # Build user content with CORRECT cache structure
            user_content = [
                {
                    "type": "text",
                    "text": instruction_block,
                    "cache_control": {"type": "ephemeral"}  # CACHE THIS (invariant)
                },
                {
                    "type": "text",
                    "text": f"\n\nTRANSCRIPT CHUNK {chunk.chunk_id}:\n\n{safe_chunk_text}"
                    # DO NOT CACHE THIS (varies per chunk)
                }
            ]

            # Call Claude API with conditional cache headers
            # First chunk creates cache, subsequent chunks read from it
            use_cache = (chunk.chunk_id > 0)
            extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31"} if use_cache else None

            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                extra_headers=extra_headers
            )

            # Track token usage
            self.track_usage(response)

            # Extract response text
            response_text = self._extract_response_text(response)

            # Parse JSON
            parsed_data = self._extract_json(response_text)

            # Extract moments with fallback for backward compatibility
            chunk_moments = parsed_data.get('chunk_moments')
            if chunk_moments is None:
                # Fallback: older tools may use 'viral_moments' key
                chunk_moments = parsed_data.get('viral_moments', [])

            # Adjust timestamps
            adjusted_moments = self._adjust_timestamps(chunk_moments, chunk, constraints)

            logger.info(f"✅ Chunk {chunk.chunk_id}: {len(adjusted_moments)} moments detected")

            return {
                'success': True,
                'chunk_id': chunk.chunk_id,
                'moments': adjusted_moments
            }

        except Exception as e:
            logger.error(f"❌ Chunk {chunk.chunk_id} analysis failed: {e}")
            return {
                'success': False,
                'chunk_id': chunk.chunk_id,
                'moments': [],
                'error': str(e)
            }

    def _extract_response_text(self, response) -> str:
        """Extract text from Anthropic API response"""
        try:
            parts = []
            for block in getattr(response, "content", []) or []:
                text_val = getattr(block, "text", None)
                if text_val is None and isinstance(block, dict):
                    text_val = block.get("text")
                if text_val:
                    parts.append(str(text_val))
            joined = "".join(parts).strip()
            return joined if joined else str(response)
        except Exception:
            return str(response)

    def _extract_json(self, response_text: str) -> dict:
        """
        Robust JSON extraction with fallback

        CORRECTED IMPLEMENTATION:
        - Try direct parse first
        - Fallback to bracket counting
        - Handles malformed responses

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed JSON dict

        Raises:
            ValueError: If no valid JSON found
        """
        # Try direct parse first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Fallback: Find first valid JSON object with bracket counting
        try:
            return json.loads(self._find_first_json_object(response_text))
        except Exception as e:
            raise ValueError(f"No valid JSON object found in response: {e}")

    def _find_first_json_object(self, text: str) -> str:
        """
        Find first valid JSON object using bracket counting

        CORRECTED IMPLEMENTATION:
        - Counts opening/closing braces
        - Handles nested objects
        - Returns complete JSON string

        Args:
            text: Text containing JSON

        Returns:
            JSON string

        Raises:
            ValueError: If no balanced JSON found
        """
        depth = 0
        start = None

        for i, ch in enumerate(text):
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start is not None:
                    return text[start:i+1]

        raise ValueError("No valid JSON object found (unbalanced braces)")

    def _calculate_time_offset(self, chunk: TranscriptChunk, constraints: Dict[str, Any]) -> float:
        """
        Calculate time offset for chunk with preferential explicit offsets

        PRIORITY ORDER:
        1. Explicit offsets (if available):
           - 'chunk_start_seconds' (global offset)
           - 'chunk_starts_seconds'[chunk_id] (per-chunk list)
        2. WPM/CPW fallback (character-based estimation)

        Args:
            chunk: TranscriptChunk with start_offset
            constraints: May include explicit offsets or words_per_minute

        Returns:
            Time offset in seconds

        Example:
            # With explicit offset
            constraints = {'chunk_starts_seconds': [0, 750, 1500]}
            chunk_id = 1 → returns 750.0s

            # Fallback to WPM
            chunk.start_offset = 10000 chars
            wpm = 160 → returns 750.0s
        """
        # 1) Try explicit offsets first (most accurate)
        if 'chunk_start_seconds' in constraints:
            return float(constraints['chunk_start_seconds'])

        if 'chunk_starts_seconds' in constraints:
            arr = constraints.get('chunk_starts_seconds') or []
            if isinstance(arr, (list, tuple)) and chunk.chunk_id < len(arr):
                try:
                    return float(arr[chunk.chunk_id])
                except (TypeError, ValueError):
                    pass  # Fall through to WPM fallback

        # 2) WPM/CPW fallback
        wpm = float(constraints.get('words_per_minute', 160.0))  # Default podcast speed
        cpw = float(constraints.get('chars_per_word', 5.0))  # Chars per word

        # Calculate seconds per character
        sec_per_char = 60.0 / max(1.0, wpm * cpw)

        # Calculate offset
        time_offset_s = float(chunk.start_offset) * sec_per_char

        return time_offset_s

    def _adjust_timestamps(
        self,
        moments: List[Dict[str, Any]],
        chunk: TranscriptChunk,
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Adjust chunk-relative timestamps to absolute video timestamps

        Args:
            moments: Moments with chunk-relative timestamps
            chunk: TranscriptChunk with start_offset
            constraints: Processing constraints (includes WPM)

        Returns:
            Moments with absolute timestamps
        """
        time_offset = self._calculate_time_offset(chunk, constraints)

        adjusted = []
        for moment in moments:
            adjusted_moment = dict(moment)
            adjusted_moment['start_time'] = moment['start_time'] + time_offset
            adjusted_moment['end_time'] = moment['end_time'] + time_offset
            adjusted.append(adjusted_moment)

        return adjusted

    def deduplicate_moments(
        self,
        moments: List[Dict[str, Any]],
        threshold_s: float = 2.0,
        jaccard_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate moments using timestamp overlap + Jaccard similarity

        Algorithm:
        1. Sort by timestamp
        2. For each moment, check overlap with previous moments
        3. If overlap AND high content similarity → merge/keep best
        4. Otherwise keep both

        Args:
            moments: List of moments from all chunks
            threshold_s: Max time difference for overlap (default: 2.0s)
            jaccard_threshold: Min Jaccard similarity to consider duplicate (default: 0.6)

        Returns:
            Deduplicated moments

        Example:
            moments = [
                {'start_time': 10.0, 'end_time': 20.0, 'key_phrase': 'Hello world', 'viral_score': 80},
                {'start_time': 11.5, 'end_time': 21.0, 'key_phrase': 'Hello world test', 'viral_score': 75}
            ]
            # These overlap (< 2s difference) AND have high Jaccard similarity
            # → Keep first (higher viral_score)
        """
        if not moments:
            return []

        # Sort by start time
        sorted_moments = sorted(moments, key=lambda m: m['start_time'])

        deduplicated = []

        for moment in sorted_moments:
            # Check if this moment overlaps with any existing moment
            is_duplicate = False

            for i, existing in enumerate(deduplicated):
                # Check time overlap
                time_overlap = (
                    abs(moment['start_time'] - existing['start_time']) <= threshold_s or
                    abs(moment['end_time'] - existing['end_time']) <= threshold_s
                )

                if time_overlap:
                    # Check content similarity
                    kp_a = moment.get('key_phrase', '') or ''
                    kp_b = existing.get('key_phrase', '') or ''

                    # If both have key_phrases: use Jaccard similarity
                    # If one/both empty: use moment_type match
                    if kp_a and kp_b:
                        jaccard = self._calculate_jaccard_similarity(kp_a, kp_b)
                        similar = jaccard >= jaccard_threshold
                    else:
                        # Fall back to moment_type match for empty phrases
                        similar = (moment.get('moment_type') == existing.get('moment_type'))

                    if similar:
                        # Duplicate detected - keep higher viral_score
                        if moment.get('viral_score', 0) > existing.get('viral_score', 0):
                            deduplicated[i] = moment
                        is_duplicate = True
                        break

            if not is_duplicate:
                deduplicated.append(moment)

        logger.info(f"🔄 Deduplication: {len(moments)} → {len(deduplicated)} moments")
        return deduplicated

    def _calculate_jaccard_similarity(self, phrase1: str, phrase2: str) -> float:
        """
        Calculate Jaccard similarity between two phrases

        Jaccard = |A ∩ B| / |A ∪ B|

        Args:
            phrase1: First phrase
            phrase2: Second phrase

        Returns:
            Similarity score (0.0 - 1.0)

        Example:
            phrase1 = "hello world test"
            phrase2 = "hello world example"
            # Intersection: {'hello', 'world'} = 2 words
            # Union: {'hello', 'world', 'test', 'example'} = 4 words
            # Jaccard = 2/4 = 0.5
        """
        if not phrase1 or not phrase2:
            return 0.0

        # Tokenize and normalize
        words1 = set(phrase1.lower().split())
        words2 = set(phrase2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Calculate Jaccard
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def track_usage(self, response):
        """
        Track token usage defensively (some fields may be missing)

        Handles cases where:
        - response.usage is None
        - Individual token fields are missing
        - Fields are None instead of 0
        """
        usage = getattr(response, 'usage', None)
        if not usage:
            return

        with self.token_lock:
            self.token_counts['input'] += int(getattr(usage, 'input_tokens', 0) or 0)
            self.token_counts['output'] += int(getattr(usage, 'output_tokens', 0) or 0)
            self.token_counts['cache_read'] += int(getattr(usage, 'cache_read_input_tokens', 0) or 0)
            self.token_counts['cache_creation'] += int(getattr(usage, 'cache_creation_input_tokens', 0) or 0)

    def calculate_cost(self, chunks_processed: int = None) -> Dict[str, Any]:
        """
        Calculate actual cost based on token usage

        Pricing (Haiku):
        - Input: $0.25 / 1M tokens
        - Output: $1.25 / 1M tokens
        - Cache write: $0.30 / 1M tokens
        - Cache read: $0.03 / 1M tokens

        Args:
            chunks_processed: Number of chunks processed (for cost_per_chunk calculation)

        Returns:
            {
                'total_cost': float,
                'token_counts': dict,
                'cache_hit_rate': float,
                'cost_per_chunk': float
            }
        """
        # Pricing (can be overridden via environment)
        prices = {
            'input': float(os.getenv('PRICE_INPUT', '0.25')) / 1_000_000,
            'output': float(os.getenv('PRICE_OUTPUT', '1.25')) / 1_000_000,
            'cache_write': float(os.getenv('PRICE_CACHE_WRITE', '0.30')) / 1_000_000,
            'cache_read': float(os.getenv('PRICE_CACHE_READ', '0.03')) / 1_000_000
        }

        cost = (
            self.token_counts['input'] * prices['input'] +
            self.token_counts['output'] * prices['output'] +
            self.token_counts['cache_creation'] * prices['cache_write'] +
            self.token_counts['cache_read'] * prices['cache_read']
        )

        # Calculate cache hit rate: read / (read + write)
        denom = (self.token_counts['cache_read'] + self.token_counts['cache_creation']) or 1
        cache_hit_rate = self.token_counts['cache_read'] / denom

        # Cost per chunk (fixed bug: was dividing by 4, should divide by actual chunks)
        if chunks_processed is None:
            chunks_processed = 1  # Fallback to avoid division issues

        return {
            'total_cost': round(cost, 4),
            'token_counts': dict(self.token_counts),
            'cache_hit_rate': round(cache_hit_rate, 3),
            'cost_per_chunk': round(cost / max(1, chunks_processed), 4)
        }

    def analyze_long_transcript(
        self,
        transcript: str,
        metadata: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point - Analyze long transcript with chunking

        Pipeline:
        1. Chunk transcript (sliding window + sentence boundaries)
        2. Parallel batch processing with rate limiting
        3. Sort results by chunk_id (preserve temporal order)
        4. Deduplicate moments (timestamp + Jaccard)
        5. Calculate cost and metrics

        Args:
            transcript: Full transcript text
            metadata: Video metadata (title, description, channel)
            constraints: Processing constraints (duration, max_moments, WPM, etc.)

        Returns:
            {
                'success': bool,
                'moments': List[Dict],
                'cost': Dict,
                'chunks_processed': int,
                'duration_s': float,
                'cache_hit_rate': float
            }
        """
        # Ensure client is initialized
        self._ensure_client()

        if not self.client:
            return {
                'success': False,
                'error': 'Anthropic client not initialized (check ANTHROPIC_API_KEY)'
            }

        start_time = time.time()

        logger.info(f"🚀 Starting long transcript analysis: {len(transcript)} chars")

        # 1. Chunk transcript
        chunks = self.chunk_transcript(transcript)

        if not chunks:
            return {
                'success': False,
                'error': 'No chunks created from transcript'
            }

        logger.info(f"📦 Created {len(chunks)} chunks")

        # 2. Parallel processing with batches
        all_results = []

        with ThreadPoolExecutor(max_workers=self.batch_size) as executor:
            # Split into batches for rate limiting
            batches = [
                chunks[i:i+self.batch_size]
                for i in range(0, len(chunks), self.batch_size)
            ]

            logger.info(f"🔄 Processing {len(batches)} batches (batch_size={self.batch_size})")

            for batch_idx, batch in enumerate(batches):
                # Submit batch
                futures = [
                    executor.submit(self._analyze_single_chunk, chunk, metadata, constraints)
                    for chunk in batch
                ]

                # Collect results
                for future in as_completed(futures):
                    all_results.append(future.result())

                # Rate limiting (wait between batches)
                if batch_idx < len(batches) - 1:  # Don't wait after last batch
                    sleep_s = max(0.0, self.batch_delay_s)  # Guard against negative sleep
                    logger.info(
                        f"⏳ Rate limit: sleeping ~{sleep_s:.1f}s "
                        f"(batch_size={self.batch_size}, limit≈{self.rate_limit_per_min}/min)"
                    )
                    time.sleep(sleep_s)

        # 3. Sort results by chunk_id (restore temporal order)
        all_results.sort(key=lambda r: r['chunk_id'])

        # 4. Collect all moments
        all_moments = []
        failed_chunks = []

        for result in all_results:
            if result['success']:
                all_moments.extend(result['moments'])
            else:
                failed_chunks.append(result['chunk_id'])

        if failed_chunks:
            logger.warning(f"⚠️ {len(failed_chunks)} chunks failed: {failed_chunks}")

        logger.info(f"📊 Total moments before deduplication: {len(all_moments)}")

        # 5. Deduplicate
        dedup_threshold_s = float(constraints.get('dedup_threshold_s', 2.0))
        final_moments = self.deduplicate_moments(all_moments, threshold_s=dedup_threshold_s)

        # 6. Calculate cost and metrics
        cost_info = self.calculate_cost(chunks_processed=len(chunks))
        duration_s = time.time() - start_time

        logger.info(f"✅ Analysis complete: {len(final_moments)} moments, ${cost_info['total_cost']:.2f}, {duration_s:.1f}s")

        return {
            'success': True,
            'moments': final_moments,
            'cost': cost_info,
            'chunks_processed': len(chunks),
            'chunks_succeeded': len(chunks) - len(failed_chunks),
            'chunks_failed': len(failed_chunks),
            'duration_s': round(duration_s, 2),
            'cache_hit_rate': cost_info['cache_hit_rate'],
            'moments_before_dedup': len(all_moments),
            'moments_after_dedup': len(final_moments),
            'method': 'transcript_chunking_v1.0'
        }


def main():
    """Test TranscriptChunker with sample data"""

    # Test metadata
    test_metadata = {
        'title': '3-Hour Political Podcast',
        'description': 'Deep dive into current events',
        'channel_name': 'Test Channel'
    }

    # Test transcript (simulate long podcast)
    test_transcript = "This is a test transcript. " * 5000  # ~150K chars

    # Test constraints
    test_constraints = {
        'min_duration': 15,
        'max_duration': 60,
        'max_moments': 5,
        'video_duration': 10800,  # 3 hours
        'words_per_minute': 160
    }

    # Initialize chunker
    chunker = TranscriptChunker()

    # Test chunking only (no API calls)
    chunks = chunker.chunk_transcript(test_transcript)
    print(f"✅ Chunking test: {len(test_transcript)} chars → {len(chunks)} chunks")

    for chunk in chunks[:3]:
        print(f"  Chunk {chunk.chunk_id}: chars {chunk.start_offset}-{chunk.end_offset} ({len(chunk.text)} chars)")

    # Full analysis (requires ANTHROPIC_API_KEY)
    if chunker.client:
        result = chunker.analyze_long_transcript(test_transcript, test_metadata, test_constraints)
        print(json.dumps(result, indent=2))
    else:
        print("⚠️ Skipping full analysis (ANTHROPIC_API_KEY not set)")


if __name__ == "__main__":
    main()
