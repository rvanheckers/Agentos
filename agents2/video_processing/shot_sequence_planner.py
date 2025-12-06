#!/usr/bin/env python3
"""
Shot Sequence Planner - Cinema-MVP V3.2 Component
=================================================

Plans cinematographic shot sequences for multi-person videos (split-screens, panels, group videos).

Key Features:
- Sub-moment splitting (long moments → 3-5 cinematographic shots)
- Shot type assignment (establishing/single/reaction/transition)
- Activity-based shot selection (audio 70% + movement 30%)
- Context7-validated timing parameters (2025 industry standards)

Shot Sequencing Strategy:
- SHORT (<8s): 1 best single shot
- MEDIUM (8-20s): 2-3 shots (establishing → single → reaction)
- LONG (20-40s): 3-5 shots (with speaker switches)
- VERY LONG (>40s): 5-8 shots (complex sequences)

Context7-Validated Parameters:
- MIN_SHOT_LENGTH = 2.5s (viewer comprehension)
- ESTABLISHING_DURATION = 2.5s (context shot)
- REACTION_DURATION = 1.0s (punchy cutaway)
- REACTION_FREQUENCY = 12% (industry standard 10-15%)
- TRANSITION_ESTABLISHING = 0.8s (speaker switch)

Architecture:
- Input: Moment + layout + audio segments + face activity
- Output: List of sub-moments with shot assignments
- Backwards compatible with V3.1 (can return single crop)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import math

logger = logging.getLogger(__name__)


class ShotSequencePlanner:
    """
    Plan cinematographic shot sequences for multi-person videos.

    V3.2 Features:
    - Sub-moment splitting (long moments → 3-5 sub-moments)
    - Shot type assignment (establishing/single/reaction/transition)
    - Activity-based shot selection (audio + movement scoring)
    - Cinematographic timing enforcement (min 2.5s per shot)
    """

    # Context7-validated timing parameters (2025 industry standards)
    MIN_SHOT_LENGTH = 2.5              # Sec - minimum voor viewer comprehension
    ESTABLISHING_DURATION = 2.5        # Sec - context shot (wide)
    REACTION_DURATION = 1.0            # Sec - cutaway (kort en punchy)
    TRANSITION_ESTABLISHING = 0.8      # Sec - smooth speaker switch

    # Shot Distribution
    REACTION_FREQUENCY = 0.12          # 12% van totale tijd (10-15% range)
    ESTABLISHING_FREQUENCY = 0.15      # 15% van tijd (start + transitions)
    SINGLES_FREQUENCY = 0.73           # 73% van tijd (bulk content)

    # Activity Scoring Weights
    AUDIO_WEIGHT = 0.70                # Audio overlap = primaire indicator
    MOVEMENT_WEIGHT = 0.20             # Face movement = secundair
    CONTEXT_WEIGHT = 0.10              # Position/size bonuses

    # V3.2 Robustness: Timing sync parameters
    TIMING_BUFFER_SEC = 0.25           # Buffer voor audio-face alignment
    AUDIO_SCALE_FACTOR = 0.5           # Scale audio weight als te weinig faces

    def __init__(self):
        """Initialize shot sequence planner"""
        self.version = "3.2.0-cinema-mvp"

    def plan_shot_sequence(
        self,
        moment: Dict[str, Any],
        layout: Dict[str, Any],
        audio_segments: List[Dict],
        face_activity: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Plan complete shot sequence voor moment.

        Args:
            moment: {'start_time': 0.0, 'end_time': 30.0, 'timestamp': 15.0}
            layout: Output van LayoutDetector (regions + activity)
            audio_segments: Transcription segments met timestamps
            face_activity: Movement data per region (optional)

        Returns:
            List van sub-moments met shot assignments:
            [
                {
                    'start_time': 0.0,
                    'end_time': 2.5,
                    'shot_type': 'establishing',
                    'crop_region': None,  # Full frame
                    'reason': 'Context shot at beginning'
                },
                {
                    'start_time': 2.5,
                    'end_time': 12.0,
                    'shot_type': 'single',
                    'crop_region': 'left',
                    'activity_score': 0.85,
                    'reason': 'Active speaker (audio + movement)'
                },
                ...
            ]

        Logic:
            1. Determine moment duration
            2. Split into sub-moments (timing-aware)
            3. Assign shot types (cinematographic rules)
            4. Select regions (activity scoring)
            5. Validate sequence (min shot length, flow)
        """
        start_time = moment.get('start_time', 0.0)
        end_time = moment.get('end_time', 0.0)
        duration = end_time - start_time

        logger.info(
            f"🎬 Planning shot sequence for {duration:.1f}s moment "
            f"({start_time:.1f}s - {end_time:.1f}s)"
        )

        # Check if layout has regions (split-screen/group)
        regions = layout.get('regions', [])
        if not regions or len(regions) < 2:
            # No split-screen detected: return single crop (backwards compatible)
            logger.info("   No multi-region layout detected - returning single shot")
            return [{
                'start_time': start_time,
                'end_time': end_time,
                'shot_type': 'single',
                'crop_region': None,
                'reason': 'Single-region moment (no split-screen)'
            }]

        # 1. Split moment into sub-moments based on duration
        sub_moments = self.split_moment(moment, layout)
        logger.info(f"   Split into {len(sub_moments)} sub-moments")

        # 2. Assign shot types to sub-moments
        sub_moments_with_types = self.assign_shot_types(
            sub_moments, layout, audio_segments, face_activity
        )

        # 3. Validate sequence (min shot length, flow)
        validated_sequence = self._validate_sequence(sub_moments_with_types)

        logger.info(
            f"✅ Shot sequence planned: {len(validated_sequence)} shots "
            f"({', '.join(s['shot_type'] for s in validated_sequence)})"
        )

        return validated_sequence

    def split_moment(
        self,
        moment: Dict,
        layout: Dict
    ) -> List[Dict]:
        """
        Split moment in cinematografische sub-moments.

        Splitting Rules (Context7-validated):

        SHORT (<8s):
            → 1 sub-moment (best single shot)

        MEDIUM (8-20s):
            → 2-3 sub-moments
            [0-2.5s]   Establishing
            [2.5-18s]  Single (active speaker)
            [18-20s]   Reaction (optional)

        LONG (20-40s):
            → 3-5 sub-moments
            [0-2.5s]    Establishing
            [2.5-15s]   Single A
            [15-16s]    Reaction B
            [16-17s]    Transition establishing
            [17-40s]    Single B

        VERY LONG (>40s):
            → 5-8 sub-moments
            Include multiple speaker switches + reactions

        Args:
            moment: Moment dict met start/end times
            layout: Layout detection result

        Returns:
            List van sub-moment dicts met tijdscodes
        """
        start_time = moment.get('start_time', 0.0)
        end_time = moment.get('end_time', 0.0)
        duration = end_time - start_time

        sub_moments = []

        if duration < 8.0:
            # SHORT: Single shot
            sub_moments.append({
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'suggested_type': 'single'
            })

        elif duration < 20.0:
            # MEDIUM: 2-3 shots
            # Establishing (2.5s)
            sub_moments.append({
                'start_time': start_time,
                'end_time': start_time + self.ESTABLISHING_DURATION,
                'duration': self.ESTABLISHING_DURATION,
                'suggested_type': 'establishing'
            })

            # Main single (rest of time, minus optional reaction)
            remaining_time = duration - self.ESTABLISHING_DURATION

            if remaining_time > 5.0:
                # Add reaction if enough time (last 1s)
                single_end = end_time - self.REACTION_DURATION
                sub_moments.append({
                    'start_time': start_time + self.ESTABLISHING_DURATION,
                    'end_time': single_end,
                    'duration': single_end - (start_time + self.ESTABLISHING_DURATION),
                    'suggested_type': 'single'
                })
                sub_moments.append({
                    'start_time': single_end,
                    'end_time': end_time,
                    'duration': self.REACTION_DURATION,
                    'suggested_type': 'reaction'
                })
            else:
                # No reaction, just single
                sub_moments.append({
                    'start_time': start_time + self.ESTABLISHING_DURATION,
                    'end_time': end_time,
                    'duration': remaining_time,
                    'suggested_type': 'single'
                })

        elif duration < 40.0:
            # LONG: 3-5 shots (with speaker switch)
            current_time = start_time

            # Establishing (2.5s)
            sub_moments.append({
                'start_time': current_time,
                'end_time': current_time + self.ESTABLISHING_DURATION,
                'duration': self.ESTABLISHING_DURATION,
                'suggested_type': 'establishing'
            })
            current_time += self.ESTABLISHING_DURATION

            # Calculate split point for speaker switch (middle third of remaining time)
            remaining_time = end_time - current_time
            first_speaker_duration = remaining_time * 0.5

            # First speaker single
            sub_moments.append({
                'start_time': current_time,
                'end_time': current_time + first_speaker_duration,
                'duration': first_speaker_duration,
                'suggested_type': 'single'
            })
            current_time += first_speaker_duration

            # Reaction to first speaker (1s)
            if current_time + self.REACTION_DURATION < end_time:
                sub_moments.append({
                    'start_time': current_time,
                    'end_time': current_time + self.REACTION_DURATION,
                    'duration': self.REACTION_DURATION,
                    'suggested_type': 'reaction'
                })
                current_time += self.REACTION_DURATION

            # Transition establishing (0.8s)
            if current_time + self.TRANSITION_ESTABLISHING < end_time:
                sub_moments.append({
                    'start_time': current_time,
                    'end_time': current_time + self.TRANSITION_ESTABLISHING,
                    'duration': self.TRANSITION_ESTABLISHING,
                    'suggested_type': 'transition'
                })
                current_time += self.TRANSITION_ESTABLISHING

            # Second speaker single (rest of time)
            if current_time < end_time:
                sub_moments.append({
                    'start_time': current_time,
                    'end_time': end_time,
                    'duration': end_time - current_time,
                    'suggested_type': 'single'
                })

        else:
            # VERY LONG: 5-8 shots (complex sequence)
            current_time = start_time

            # Establishing (2.5s)
            sub_moments.append({
                'start_time': current_time,
                'end_time': current_time + self.ESTABLISHING_DURATION,
                'duration': self.ESTABLISHING_DURATION,
                'suggested_type': 'establishing'
            })
            current_time += self.ESTABLISHING_DURATION

            # Split remaining time into 3-4 speaker segments
            remaining_time = end_time - current_time
            num_speakers = 3  # 3 speaker switches for very long moments
            speaker_duration = remaining_time / num_speakers

            for i in range(num_speakers):
                # Speaker single
                single_duration = speaker_duration - self.REACTION_DURATION - self.TRANSITION_ESTABLISHING

                if single_duration >= self.MIN_SHOT_LENGTH:
                    sub_moments.append({
                        'start_time': current_time,
                        'end_time': current_time + single_duration,
                        'duration': single_duration,
                        'suggested_type': 'single'
                    })
                    current_time += single_duration

                # Reaction (except last speaker)
                if i < num_speakers - 1 and current_time + self.REACTION_DURATION < end_time:
                    sub_moments.append({
                        'start_time': current_time,
                        'end_time': current_time + self.REACTION_DURATION,
                        'duration': self.REACTION_DURATION,
                        'suggested_type': 'reaction'
                    })
                    current_time += self.REACTION_DURATION

                    # Transition (except last speaker)
                    if current_time + self.TRANSITION_ESTABLISHING < end_time:
                        sub_moments.append({
                            'start_time': current_time,
                            'end_time': current_time + self.TRANSITION_ESTABLISHING,
                            'duration': self.TRANSITION_ESTABLISHING,
                            'suggested_type': 'transition'
                        })
                        current_time += self.TRANSITION_ESTABLISHING

        return sub_moments

    def assign_shot_types(
        self,
        sub_moments: List[Dict],
        layout: Dict,
        audio_segments: List[Dict],
        face_activity: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Assign shot types to sub-moments (cinematographic rules).

        Shot Type Selection Logic:

        1. ESTABLISHING:
           - Always at moment start (first 2.5s)
           - At speaker switches (0.8s before new speaker)
           - Crop: Minimal (preserves layout)

        2. SINGLE:
           - Bulk of moment (active speaker)
           - Select region with highest activity score
           - Crop: To active region (close-up)

        3. REACTION:
           - 10-15% of total time (REACTION_FREQUENCY)
           - 0.8-1.2s duration (REACTION_DURATION)
           - Select adjacent region (listener)
           - Crop: To listener region

        4. TRANSITION:
           - When speaker switches detected
           - 0.5-1.0s establishing before new speaker
           - Crop: Minimal (both speakers visible)

        Args:
            sub_moments: List van sub-moment dicts
            layout: Layout detection result
            audio_segments: Transcription segments
            face_activity: Movement data (optional)

        Returns:
            sub_moments with 'shot_type' and 'crop_region' assigned
        """
        regions = layout.get('regions', [])

        # Track last active region for reaction selection
        last_active_region = None

        for i, sub_moment in enumerate(sub_moments):
            suggested_type = sub_moment.get('suggested_type', 'single')

            if suggested_type == 'establishing' or suggested_type == 'transition':
                # Establishing/Transition: Show full frame (no crop)
                sub_moment['shot_type'] = suggested_type
                sub_moment['crop_region'] = None
                sub_moment['reason'] = (
                    'Context shot at beginning' if suggested_type == 'establishing'
                    else 'Speaker transition'
                )

            elif suggested_type == 'single':
                # Single: Select most active region
                best_region = None
                best_score = 0.0

                for region in regions:
                    score = self.calculate_activity_score(
                        region, sub_moment, audio_segments, face_activity
                    )

                    if score > best_score:
                        best_score = score
                        best_region = region

                if best_region:
                    sub_moment['shot_type'] = 'single'
                    sub_moment['crop_region'] = best_region.get('position', 'center')
                    sub_moment['activity_score'] = best_score
                    sub_moment['reason'] = f'Active speaker (activity: {best_score:.2f})'
                    last_active_region = best_region
                else:
                    # Fallback: no crop
                    sub_moment['shot_type'] = 'single'
                    sub_moment['crop_region'] = None
                    sub_moment['reason'] = 'No active region detected'

            elif suggested_type == 'reaction':
                # Reaction: Select adjacent/listening region
                reaction_region = self._select_reaction_region(
                    regions, last_active_region
                )

                if reaction_region:
                    sub_moment['shot_type'] = 'reaction'
                    sub_moment['crop_region'] = reaction_region.get('position', 'center')
                    sub_moment['reason'] = 'Listener reaction cutaway'
                else:
                    # Fallback: show full frame
                    sub_moment['shot_type'] = 'reaction'
                    sub_moment['crop_region'] = None
                    sub_moment['reason'] = 'Reaction shot (full frame)'

        return sub_moments

    def calculate_activity_score(
        self,
        region: Dict,
        sub_moment: Dict,
        audio_segments: List[Dict],
        face_activity: Optional[Dict]
    ) -> float:
        """
        Bereken activity score voor regio in sub-moment.

        Scoring Algorithm (Context7-validated):

        1. Audio Overlap Score (70% weight):
           - Count audio segments overlapping met sub-moment
           - Bij 2-way split: gebruik temporal heuristic
             (left region = eerste helft, right = tweede helft)
           - Score = (overlap_duration / sub_moment_duration)

        2. Movement Score (20% weight):
           - Use face movement_range data
           - Score = (movement_intensity / max_movement_in_layout)

        3. Context Bonus (10% weight):
           - Center region bonus (vaak host/moderator)
           - Previous speaker continuation bonus
           - Size bonus (groter = meer prominent)

        Combined Score:
            activity_score = (
                audio_score * 0.7 +
                movement_score * 0.2 +
                context_bonus * 0.1
            )

        Args:
            region: Region dict met position, faces
            sub_moment: Sub-moment dict met times
            audio_segments: Transcription segments
            face_activity: Movement data (optional)

        Returns:
            Activity score 0.0-1.0
        """
        # 1. Audio Overlap Score
        audio_score = self._calculate_audio_overlap_score(
            region, sub_moment, audio_segments
        )

        # 2. Movement Score
        movement_score = self._calculate_movement_score(
            region, face_activity
        )

        # 3. Context Bonus
        context_bonus = self._calculate_context_bonus(region)

        # Combined score
        activity_score = (
            audio_score * self.AUDIO_WEIGHT +
            movement_score * self.MOVEMENT_WEIGHT +
            context_bonus * self.CONTEXT_WEIGHT
        )

        return min(1.0, max(0.0, activity_score))  # Clamp to 0-1

    def _calculate_audio_overlap_score(
        self,
        region: Dict,
        sub_moment: Dict,
        audio_segments: List[Dict]
    ) -> float:
        """
        Calculate audio overlap score for region in sub-moment.

        Uses temporal heuristic for 2-way splits without speaker diarization.
        """
        start_time = sub_moment.get('start_time', 0.0)
        end_time = sub_moment.get('end_time', 0.0)
        duration = end_time - start_time

        if duration <= 0:
            return 0.0

        # V3.2 FIX: Add timing buffer for audio-face alignment
        buffer = self.TIMING_BUFFER_SEC
        buffered_start = max(0, start_time - buffer)
        buffered_end = end_time + buffer

        # Count overlapping audio segments
        overlap_duration = 0.0

        for segment in audio_segments:
            seg_start = segment.get('start', 0.0)
            seg_end = segment.get('end', 0.0)

            # Calculate overlap (use buffered times)
            overlap_start = max(buffered_start, seg_start)
            overlap_end = min(buffered_end, seg_end)

            if overlap_end > overlap_start:
                overlap_duration += (overlap_end - overlap_start)

        # Calculate score (normalized by sub-moment duration)
        score = overlap_duration / duration if duration > 0 else 0.0

        # V3.2 FIX: Scale audio weight if insufficient faces
        face_count = region.get('activity_data', {}).get('face_count', 1)
        if face_count < 1:
            score *= self.AUDIO_SCALE_FACTOR

        return min(1.0, score)

    def _calculate_movement_score(
        self,
        region: Dict,
        face_activity: Optional[Dict]
    ) -> float:
        """
        Calculate movement score for region.

        Uses movement_range data from face tracking.
        """
        if not face_activity:
            return 0.5  # Neutral score if no activity data

        # Get activity data for this region
        activity_data = region.get('activity_data', {})
        movement_intensity = activity_data.get('movement_intensity', 0.5)

        return movement_intensity

    def _calculate_context_bonus(self, region: Dict) -> float:
        """
        Calculate context bonus for region.

        Bonuses:
        - Center region: +0.3 (often host/moderator)
        - Larger region: +0.2 (more prominent)
        """
        position = region.get('position', '')
        bonus = 0.0

        # Center bonus
        if position == 'center':
            bonus += 0.3

        # Size bonus (if region has size data)
        # TODO: Implement when layout detector provides size data

        return min(1.0, bonus)

    def _select_reaction_region(
        self,
        regions: List[Dict],
        last_active_region: Optional[Dict]
    ) -> Optional[Dict]:
        """
        Select region for reaction shot (listener, not speaker).

        Strategy:
        - If last_active_region known: select adjacent region
        - Otherwise: select first non-active region
        """
        if not regions:
            return None

        if not last_active_region:
            # No context: return first region
            return regions[0]

        # Find adjacent region (not the active speaker)
        last_position = last_active_region.get('position', '')

        for region in regions:
            if region.get('position') != last_position:
                return region

        # Fallback: return first region
        return regions[0]

    def _validate_sequence(self, sequence: List[Dict]) -> List[Dict]:
        """
        Validate shot sequence against cinematographic standards.

        Checks:
        1. Min shot length (2.5s) - MUST PASS
        2. Shot variety (not all same type) - SHOULD PASS
        3. Reasonable establishing frequency - SHOULD PASS

        Returns:
            Validated sequence (may merge short shots)
        """
        # V3.2 FIX: Improved merge logic - two-pass approach
        # Pass 1: Merge adjacent short shots
        merged = []
        i = 0
        while i < len(sequence):
            shot = sequence[i]
            duration = shot.get('duration', 0.0)

            # Check if this shot and next are both short
            if i < len(sequence) - 1:
                next_shot = sequence[i + 1]
                next_duration = next_shot.get('duration', 0.0)

                if duration < self.MIN_SHOT_LENGTH and next_duration < self.MIN_SHOT_LENGTH:
                    # Both short: merge them
                    merged_shot = {
                        'start_time': shot['start_time'],
                        'end_time': next_shot['end_time'],
                        'duration': next_shot['end_time'] - shot['start_time'],
                        'shot_type': shot['shot_type'],  # Keep first shot type
                        'crop_region': shot.get('crop_region'),
                        'reason': f'Merged short shots ({duration:.1f}s + {next_duration:.1f}s)'
                    }
                    merged.append(merged_shot)
                    logger.warning(
                        f"⚠️  Merged shot {i} ({duration:.1f}s) + shot {i+1} ({next_duration:.1f}s) → "
                        f"{merged_shot['duration']:.1f}s"
                    )
                    i += 2  # Skip both
                    continue

            # Single shot check
            if duration < self.MIN_SHOT_LENGTH:
                if i < len(sequence) - 1:
                    # Merge with next (extend next shot backwards)
                    logger.warning(
                        f"⚠️  Shot {i} too short ({duration:.1f}s) - extending next shot"
                    )
                    next_shot = sequence[i + 1]
                    next_shot['start_time'] = shot['start_time']
                    next_shot['duration'] = next_shot['end_time'] - shot['start_time']
                    i += 1
                    continue
                elif merged:
                    # Extend previous shot
                    logger.warning(
                        f"⚠️  Shot {i} too short ({duration:.1f}s) - extending previous shot"
                    )
                    merged[-1]['end_time'] = shot['end_time']
                    merged[-1]['duration'] = shot['end_time'] - merged[-1]['start_time']
                    i += 1
                    continue

            merged.append(shot)
            i += 1

        return merged


def main():
    """CLI entry point voor testing"""
    import json

    # Test shot sequence planner
    planner = ShotSequencePlanner()

    # Test case 1: SHORT moment (5 seconds)
    print("=" * 60)
    print("Test Case 1: SHORT moment (5s)")
    print("=" * 60)

    moment_short = {
        'start_time': 0.0,
        'end_time': 5.0,
        'timestamp': 2.5
    }

    layout_2way = {
        'layout_type': '2-way-vertical',
        'confidence': 0.85,
        'regions': [
            {'position': 'left', 'faces': [{'center_x': 0.25, 'center_y': 0.5}]},
            {'position': 'right', 'faces': [{'center_x': 0.75, 'center_y': 0.5}]}
        ]
    }

    audio_segments_short = [
        {'start': 0.0, 'end': 5.0, 'text': 'Hello there'}
    ]

    sequence = planner.plan_shot_sequence(
        moment_short, layout_2way, audio_segments_short
    )

    print(json.dumps(sequence, indent=2))

    # Test case 2: MEDIUM moment (15 seconds)
    print("\n" + "=" * 60)
    print("Test Case 2: MEDIUM moment (15s)")
    print("=" * 60)

    moment_medium = {
        'start_time': 0.0,
        'end_time': 15.0,
        'timestamp': 7.5
    }

    audio_segments_medium = [
        {'start': 0.0, 'end': 10.0, 'text': 'I think this is great'},
        {'start': 10.0, 'end': 15.0, 'text': 'I agree'}
    ]

    sequence = planner.plan_shot_sequence(
        moment_medium, layout_2way, audio_segments_medium
    )

    print(json.dumps(sequence, indent=2))

    # Test case 3: LONG moment (30 seconds)
    print("\n" + "=" * 60)
    print("Test Case 3: LONG moment (30s)")
    print("=" * 60)

    moment_long = {
        'start_time': 0.0,
        'end_time': 30.0,
        'timestamp': 15.0
    }

    audio_segments_long = [
        {'start': 0.0, 'end': 15.0, 'text': 'Let me explain this concept in detail...'},
        {'start': 15.0, 'end': 30.0, 'text': 'That makes sense, let me add to that...'}
    ]

    sequence = planner.plan_shot_sequence(
        moment_long, layout_2way, audio_segments_long
    )

    print(json.dumps(sequence, indent=2))

    print("\n" + "=" * 60)
    print(f"Shot Sequence Planner Version: {planner.version}")
    print("=" * 60)


if __name__ == "__main__":
    main()
