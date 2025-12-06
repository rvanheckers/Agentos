#!/usr/bin/env python3
"""
Cinematic Composer MVP - Cinema-MVP Orchestrator
================================================

Orchestreert cinematografische crop berekening met alle Cinema-MVP componenten.

Components V1:
1. ShotDetector: Detect shots + classify types (close/medium/wide)
2. FaceDetector: Multi-frame face detection (bestaand)
3. CameraMovementAnalyzer: Optical flow @ 1 fps
4. CompositionalEngine: Rule of thirds, headroom, safe-zone, leading space

Architecture:
- Video-level preprocessing (shots, motion) wordt gecached
- Per-moment composition gebruikt pre-computed data
- Shot boundaries fungeren als "reset points" voor smoothing
- Temporal smoothing binnen shots (geen smoothing over cuts)

Performance Budget:
- Preprocessing: ~1-3 min voor 2 uur video
- Per-moment composition: ~10-50ms (real-time capable)

Context7-validated: Industry-standard cinematographic principles
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import time
import json

from agents2.video_processing.shot_detector import ShotDetector
from agents2.video_processing.camera_movement_analyzer import CameraMovementAnalyzer
from agents2.video_processing.compositional_engine import CompositionalEngine
from agents2.video_processing.layout_detector import LayoutDetector
from agents2.video_processing.shot_sequence_planner import ShotSequencePlanner

logger = logging.getLogger(__name__)


class CinematicComposer:
    """
    Cinematografische crop orchestrator.

    V1 MVP Features:
    - Shot-aware composition
    - Rule of thirds + headroom + safe-zone
    - Motion-based leading space
    - Temporal smoothing binnen shots

    Geen V1:
    - Gaze (iris) tracking
    - Audio-reactieve framing

    V3.1 Features:
    - Split-screen layout detection (✅ implemented)
    """

    def __init__(self, enable_layout_detection: bool = True):
        """
        Initialize cinematic composer met alle sub-components

        Args:
            enable_layout_detection: Enable split-screen detection (default True)
        """
        self.version = "3.2.0-cinema-mvp"  # UPGRADED: V3.2 with shot sequencing
        self.enable_layout_detection = enable_layout_detection

        self.shot_detector = ShotDetector()
        self.motion_analyzer = CameraMovementAnalyzer()
        self.compositional_engine = CompositionalEngine()
        self.layout_detector = LayoutDetector()
        self.shot_sequence_planner = ShotSequencePlanner()  # NEW: V3.2

        # Cached video-level data
        self._video_cache: Dict[str, Dict] = {}

    def preprocess_video(
        self,
        video_path: str,
        faces_per_timestamp: Optional[Dict[float, int]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Video-level preprocessing: shots + camera movement.

        Deze data wordt gecached en hergebruikt voor alle moments in deze video.

        Args:
            video_path: Path naar video
            faces_per_timestamp: Dict met timestamp -> #faces voor shot classification
            force_refresh: Force cache refresh (default False)

        Returns:
            {
                "shots": List[Dict],              # Van ShotDetector
                "motion_vectors": List[Dict],     # Van CameraMovementAnalyzer
                "preprocessing_time": float,
                "cache_key": str
            }
        """
        cache_key = str(Path(video_path).resolve())

        # Check cache
        if not force_refresh and cache_key in self._video_cache:
            logger.info(f"🎬 Using cached preprocessing data for {Path(video_path).name}")
            return self._video_cache[cache_key]

        start_time = time.time()
        logger.info(f"🎬 Starting cinematic preprocessing: {Path(video_path).name}")

        # 1. Detect shots
        logger.info("   Step 1/2: Detecting shots...")
        shots = self.shot_detector.analyze(
            video_path,
            faces_per_timestamp=faces_per_timestamp
        )

        # 2. Analyze camera movement
        logger.info("   Step 2/2: Analyzing camera movement...")
        motion_vectors = self.motion_analyzer.analyze(
            video_path,
            shot_boundaries=shots
        )

        preprocessing_time = time.time() - start_time

        result = {
            "shots": shots,
            "motion_vectors": motion_vectors,
            "preprocessing_time": preprocessing_time,
            "cache_key": cache_key
        }

        # Cache result
        self._video_cache[cache_key] = result

        logger.info(f"✅ Preprocessing completed in {preprocessing_time:.2f}s")
        logger.info(f"   Shots: {len(shots)}, Motion samples: {len(motion_vectors)}")

        return result

    def compose_for_moment(
        self,
        video_path: str,
        moment: Dict[str, Any],
        faces: List[Dict[str, Any]],
        orig_w: int,
        orig_h: int,
        target_ratio: float = 9/16,
        preprocessing_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Bereken cinematografische crop voor specifiek moment.

        Args:
            video_path: Path naar video
            moment: Dict met 'start_time', 'end_time', 'timestamp' (center)
            faces: List van face dicts (per-moment gefilterd)
            orig_w, orig_h: Originele video dimensies
            target_ratio: Target aspect ratio (default 9/16 voor vertical)
            preprocessing_data: Output van preprocess_video() (optioneel, voor caching)

        Returns:
            {
                "crop_x": int,
                "crop_y": int,
                "crop_w": int,
                "crop_h": int,
                "rules_applied": List[str],
                "shot_type": str,
                "shot_number": int,
                "motion": Dict,
                "composition_time_ms": float,
                "method": "cinematic_v3"
            }
        """
        start_time = time.time()

        # Get preprocessing data (cached of fresh)
        if preprocessing_data is None:
            preprocessing_data = self.preprocess_video(video_path)

        shots = preprocessing_data['shots']
        motion_vectors = preprocessing_data['motion_vectors']

        # Determine moment center timestamp
        moment_timestamp = moment.get('timestamp') or (
            moment['start_time'] + moment['end_time']
        ) / 2

        # 1. Find shot for this moment
        current_shot = self._find_shot_for_timestamp(shots, moment_timestamp)

        shot_type = "medium"  # Fallback
        shot_number = None

        if current_shot:
            shot_type = current_shot['type']
            shot_number = current_shot['shot_number']

        # 2. Get camera movement for this moment
        camera_movement = self.motion_analyzer.get_motion_for_timestamp(
            motion_vectors,
            moment_timestamp,
            window_sec=2.0
        )

        # 3. PRE-CHECK: Detect split-screen/multi-panel layout (V3.1)
        layout_detection = None
        if self.enable_layout_detection and faces:
            layout_detection = self.layout_detector.detect_layout(
                faces=faces,
                orig_w=orig_w,
                orig_h=orig_h
            )

            # If split-screen detected: skip/minimize cropping
            if layout_detection.get('should_skip_crop'):
                logger.info(
                    f"🎬 Split-screen detected ({layout_detection['layout_type']}, "
                    f"confidence: {layout_detection['confidence']:.2f}) - using minimal crop"
                )

                # Return minimal crop that maintains aspect ratio but preserves layout
                crop_w = int(orig_h * target_ratio)
                crop_h = orig_h

                # If crop width exceeds frame width, adjust
                if crop_w > orig_w:
                    crop_w = orig_w
                    crop_h = int(orig_w / target_ratio)

                # Center the crop
                crop_x = (orig_w - crop_w) // 2
                crop_y = (orig_h - crop_h) // 2

                composition_time_ms = (time.time() - start_time) * 1000

                return {
                    "crop_x": crop_x,
                    "crop_y": crop_y,
                    "crop_w": crop_w,
                    "crop_h": crop_h,
                    "rules_applied": ["split_screen_detected", "minimal_crop"],
                    "shot_type": shot_type,
                    "shot_number": shot_number,
                    "motion": camera_movement,
                    "layout_detection": layout_detection,
                    "composition_time_ms": composition_time_ms,
                    "method": "cinematic_v3.1_layout_aware"
                }

        # 4. Compose cinematografische crop (normal path)
        crop_x, crop_y, crop_w, crop_h, rules_applied = self.compositional_engine.compose(
            orig_w=orig_w,
            orig_h=orig_h,
            target_ratio=target_ratio,
            faces=faces,
            shot_type=shot_type,
            camera_movement=camera_movement
        )

        composition_time_ms = (time.time() - start_time) * 1000

        result = {
            "crop_x": crop_x,
            "crop_y": crop_y,
            "crop_w": crop_w,
            "crop_h": crop_h,
            "rules_applied": rules_applied,
            "shot_type": shot_type,
            "shot_number": shot_number,
            "motion": camera_movement,
            "layout_detection": layout_detection,  # V3.1: Include layout detection result
            "composition_time_ms": composition_time_ms,
            "method": "cinematic_v3.1"
        }

        logger.debug(
            f"🎨 Composed moment @ {moment_timestamp:.1f}s: "
            f"{shot_type} shot, {crop_w}x{crop_h} crop, "
            f"rules: {', '.join(rules_applied)}"
        )

        return result

    def compose_for_moment_with_sequence(
        self,
        video_path: str,
        moment: Dict[str, Any],
        faces: List[Dict[str, Any]],
        orig_w: int,
        orig_h: int,
        target_ratio: float = 9/16,
        preprocessing_data: Optional[Dict] = None,
        audio_segments: Optional[List[Dict]] = None,
        enable_shot_sequencing: bool = True
    ) -> Dict[str, Any]:
        """
        Bereken cinematografische crop MET shot sequencing (V3.2 NEW).

        V3.2 NEW: Returns shot sequence i.p.v. single crop wanneer multi-region layout detected.

        Args:
            video_path: Path naar video
            moment: Dict met 'start_time', 'end_time', 'timestamp'
            faces: List van face dicts (per-moment gefilterd)
            orig_w, orig_h: Originele video dimensies
            target_ratio: Target aspect ratio (default 9/16)
            preprocessing_data: Output van preprocess_video() (optioneel)
            audio_segments: NEW - transcription segments voor activity scoring
            enable_shot_sequencing: NEW - enable sub-moment splitting (default True)

        Returns:
            V3.1 Format (backwards compatible):
            {
                'crop_x': 100, 'crop_y': 50,
                'crop_w': 600, 'crop_h': 1080,
                ... (existing fields)
            }

            V3.2 Format (NEW):
            {
                'shot_sequence': [
                    {
                        'shot_type': 'establishing',
                        'crop_x': 0, 'crop_y': 0,
                        'crop_w': 1920, 'crop_h': 1080,
                        'start_offset': 0.0,
                        'duration': 2.5,
                        'reason': 'Context shot at beginning'
                    },
                    {
                        'shot_type': 'single',
                        'crop_region': 'left',
                        'crop_x': 100, 'crop_y': 50,
                        'crop_w': 600, 'crop_h': 1080,
                        'start_offset': 2.5,
                        'duration': 9.5,
                        'activity_score': 0.85,
                        'reason': 'Active speaker (audio + movement)'
                    }
                ],
                'total_sub_moments': 4,
                'cinematography_version': 'v3.2',

                # Backwards compatible (eerste shot):
                'crop_x': 0,
                'crop_y': 0,
                'crop_w': 1920,
                'crop_h': 1080,
                ... (existing fields)
            }

        Logic:
            1. Detect layout (split-screen/group)
            2. Track activity per region
            3. Plan shot sequence (ShotSequencePlanner)
            4. Calculate crop coordinates for each shot
            5. Return sequence + backwards compatible single crop
        """
        start_time = time.time()

        # Get preprocessing data (cached of fresh)
        if preprocessing_data is None:
            preprocessing_data = self.preprocess_video(video_path)

        shots = preprocessing_data['shots']
        motion_vectors = preprocessing_data['motion_vectors']

        # Determine moment center timestamp
        moment_timestamp = moment.get('timestamp') or (
            moment['start_time'] + moment['end_time']
        ) / 2

        # 1. Find shot for this moment
        current_shot = self._find_shot_for_timestamp(shots, moment_timestamp)

        shot_type = "medium"  # Fallback
        shot_number = None

        if current_shot:
            shot_type = current_shot['type']
            shot_number = current_shot['shot_number']

        # 2. Get camera movement for this moment
        camera_movement = self.motion_analyzer.get_motion_for_timestamp(
            motion_vectors,
            moment_timestamp,
            window_sec=2.0
        )

        # 3. Detect layout (split-screen/multi-panel)
        layout_detection = None
        if self.enable_layout_detection and faces:
            layout_detection = self.layout_detector.detect_layout(
                faces=faces,
                orig_w=orig_w,
                orig_h=orig_h,
                video_path=video_path,  # V3.2.1: Added for visual detection
                timestamp=moment_timestamp  # V3.2.1: Added for visual detection
            )

            # V3.2: Track activity per region if layout detected
            if layout_detection.get('layout_type') and audio_segments:
                layout_detection = self.layout_detector.track_activity_per_region(
                    layout=layout_detection,
                    faces=faces,
                    audio_segments=audio_segments,
                    moment=moment
                )

        # 4. Check if shot sequencing should be applied
        should_apply_sequencing = (
            enable_shot_sequencing and
            layout_detection and
            layout_detection.get('layout_type') and
            len(layout_detection.get('regions', [])) >= 2 and
            audio_segments is not None
        )

        if should_apply_sequencing:
            # V3.2: Plan shot sequence
            logger.info(
                f"🎬 V3.2: Planning shot sequence for {layout_detection['layout_type']} layout"
            )

            shot_sequence = self.shot_sequence_planner.plan_shot_sequence(
                moment=moment,
                layout=layout_detection,
                audio_segments=audio_segments or [],
                face_activity=None  # TODO: Pass face activity data if available
            )

            # Calculate crop coordinates for each shot in sequence
            shot_sequence_with_crops = []

            for i, sub_moment in enumerate(shot_sequence):
                crop_region = sub_moment.get('crop_region')

                if crop_region is None:
                    # Establishing/Transition: Minimal crop (preserve layout)
                    crop_w = int(orig_h * target_ratio)
                    crop_h = orig_h

                    if crop_w > orig_w:
                        crop_w = orig_w
                        crop_h = int(orig_w / target_ratio)

                    crop_x = (orig_w - crop_w) // 2
                    crop_y = (orig_h - crop_h) // 2

                else:
                    # Single/Reaction: Crop to specific region
                    region = self._find_region_by_position(
                        layout_detection, crop_region
                    )

                    if region:
                        # V3.2 FIX: Calculate crop from panel boundaries (NOT face composition)
                        # This ensures crops are aligned with split-screen panels
                        panel_bounds = self._calculate_panel_crop_for_region(
                            position=crop_region,
                            layout_type=layout_detection.get('layout_type'),
                            orig_w=orig_w,
                            orig_h=orig_h,
                            target_ratio=target_ratio
                        )

                        crop_x = panel_bounds['x']
                        crop_y = panel_bounds['y']
                        crop_w = panel_bounds['width']
                        crop_h = panel_bounds['height']
                    else:
                        # Fallback: center crop
                        crop_w = int(orig_h * target_ratio)
                        crop_h = orig_h
                        crop_x = (orig_w - crop_w) // 2
                        crop_y = (orig_h - crop_h) // 2

                # Calculate start_offset relative to moment start
                start_offset = sub_moment['start_time'] - moment['start_time']

                shot_sequence_with_crops.append({
                    'shot_type': sub_moment.get('shot_type', 'single'),
                    'crop_region': crop_region,
                    'crop_x': crop_x,
                    'crop_y': crop_y,
                    'crop_w': crop_w,
                    'crop_h': crop_h,
                    'start_offset': start_offset,
                    'duration': sub_moment.get('duration', sub_moment['end_time'] - sub_moment['start_time']),
                    'activity_score': sub_moment.get('activity_score'),
                    'reason': sub_moment.get('reason', '')
                })

            composition_time_ms = (time.time() - start_time) * 1000

            # Return V3.2 format with shot sequence
            # First shot is used for backwards compatibility
            first_shot = shot_sequence_with_crops[0] if shot_sequence_with_crops else {
                'crop_x': 0, 'crop_y': 0, 'crop_w': orig_w, 'crop_h': orig_h
            }

            return {
                # V3.2 NEW: Shot sequence
                'shot_sequence': shot_sequence_with_crops,
                'total_sub_moments': len(shot_sequence_with_crops),
                'cinematography_version': 'v3.2',

                # Backwards compatible: eerste shot
                'crop_x': first_shot['crop_x'],
                'crop_y': first_shot['crop_y'],
                'crop_w': first_shot['crop_w'],
                'crop_h': first_shot['crop_h'],
                'rules_applied': ['shot_sequencing', 'multi_region_layout'],
                'shot_type': shot_type,
                'shot_number': shot_number,
                'motion': camera_movement,
                'layout_detection': layout_detection,
                'composition_time_ms': composition_time_ms,
                'method': 'cinematic_v3.2_shot_sequencing'
            }

        else:
            # V3.1 fallback: Single crop (no sequencing)
            logger.debug("   V3.1 fallback: Using single crop (no shot sequencing)")

            # Use standard compose_for_moment
            return self.compose_for_moment(
                video_path=video_path,
                moment=moment,
                faces=faces,
                orig_w=orig_w,
                orig_h=orig_h,
                target_ratio=target_ratio,
                preprocessing_data=preprocessing_data
            )

    def _find_region_by_position(
        self,
        layout: Dict,
        position: str
    ) -> Optional[Dict]:
        """Find region by position name (left, right, center, etc.)"""
        regions = layout.get('regions', [])
        for region in regions:
            if region.get('position') == position:
                return region
        return None

    def _calculate_panel_crop_for_region(
        self,
        position: str,
        layout_type: str,
        orig_w: int,
        orig_h: int,
        target_ratio: float
    ) -> Dict[str, int]:
        """
        Calculate crop coordinates from STRICT panel boundaries for split-screen layouts.

        V3.2 FIX: This method calculates crops directly from panel edges (NOT face composition).
        This ensures crops are perfectly aligned with split-screen panel boundaries.

        For 2-way-vertical (1920x1080):
        - left: x=0, y=0, width=960, height=1080
        - right: x=960, y=0, width=960, height=1080

        For 2-way-horizontal (1920x1080):
        - top: x=0, y=0, width=1920, height=540
        - bottom: x=0, y=540, width=1920, height=540

        Args:
            position: Panel position ('left', 'right', 'top', 'bottom', 'top-left', etc.)
            layout_type: Layout type ('2-way-vertical', '2-way-horizontal', '4-way-grid')
            orig_w, orig_h: Original video dimensions
            target_ratio: Target aspect ratio (9/16 for vertical video)

        Returns:
            Dict with 'x', 'y', 'width', 'height' for strict panel boundary crop
        """

        # Default values (will be overwritten based on layout)
        panel_x = 0
        panel_y = 0
        panel_w = orig_w
        panel_h = orig_h

        # Calculate panel boundaries based on layout type
        if layout_type == '2-way-vertical':
            # Vertical split: left | right
            half_w = orig_w // 2
            panel_h = orig_h  # Full height

            if position == 'left':
                panel_x = 0
                panel_w = half_w
            elif position == 'right':
                panel_x = half_w
                panel_w = half_w
            else:
                logger.warning(f"Unknown position '{position}' for 2-way-vertical, using left panel")
                panel_x = 0
                panel_w = half_w

        elif layout_type == '2-way-horizontal':
            # Horizontal split: top / bottom
            half_h = orig_h // 2
            panel_w = orig_w  # Full width

            if position == 'top':
                panel_y = 0
                panel_h = half_h
            elif position == 'bottom':
                panel_y = half_h
                panel_h = half_h
            else:
                logger.warning(f"Unknown position '{position}' for 2-way-horizontal, using top panel")
                panel_y = 0
                panel_h = half_h

        elif layout_type == '4-way-grid':
            # Grid: top-left | top-right
            #       bottom-left | bottom-right
            half_w = orig_w // 2
            half_h = orig_h // 2

            if position == 'top-left':
                panel_x, panel_y = 0, 0
                panel_w, panel_h = half_w, half_h
            elif position == 'top-right':
                panel_x, panel_y = half_w, 0
                panel_w, panel_h = half_w, half_h
            elif position == 'bottom-left':
                panel_x, panel_y = 0, half_h
                panel_w, panel_h = half_w, half_h
            elif position == 'bottom-right':
                panel_x, panel_y = half_w, half_h
                panel_w, panel_h = half_w, half_h
            else:
                logger.warning(f"Unknown position '{position}' for 4-way-grid, using top-left")
                panel_x, panel_y = 0, 0
                panel_w, panel_h = half_w, half_h

        else:
            logger.warning(f"Unknown layout_type '{layout_type}', using full frame")
            panel_x, panel_y = 0, 0
            panel_w, panel_h = orig_w, orig_h

        # Now apply target_ratio crop WITHIN the panel boundaries
        # Target ratio is width/height (e.g., 9/16 = 0.5625 for vertical video)

        # Calculate crop dimensions that fit target_ratio
        target_crop_w = int(panel_h * target_ratio)
        target_crop_h = panel_h

        # If calculated width exceeds panel width, constrain by width instead
        if target_crop_w > panel_w:
            target_crop_w = panel_w
            target_crop_h = int(panel_w / target_ratio)

        # Center the crop WITHIN the panel
        crop_x = panel_x + (panel_w - target_crop_w) // 2
        crop_y = panel_y + (panel_h - target_crop_h) // 2

        logger.debug(
            f"📐 Panel crop calculated: position={position}, layout={layout_type}, "
            f"panel=[{panel_x},{panel_y},{panel_w}x{panel_h}], "
            f"crop=[{crop_x},{crop_y},{target_crop_w}x{target_crop_h}]"
        )

        return {
            'x': crop_x,
            'y': crop_y,
            'width': target_crop_w,
            'height': target_crop_h
        }

    def _find_shot_for_timestamp(
        self,
        shots: List[Dict],
        timestamp: float
    ) -> Optional[Dict]:
        """Vind shot die timestamp bevat"""
        for shot in shots:
            if shot['start_time'] <= timestamp <= shot['end_time']:
                return shot
        return None

    def validate_crop(
        self,
        crop_data: Dict,
        orig_w: int,
        orig_h: int
    ) -> bool:
        """Valideer crop bounds"""
        return self.compositional_engine.validate_crop(
            crop_data['crop_x'],
            crop_data['crop_y'],
            crop_data['crop_w'],
            crop_data['crop_h'],
            orig_w,
            orig_h
        )

    def get_statistics(
        self,
        preprocessing_data: Dict
    ) -> Dict[str, Any]:
        """
        Bereken statistieken uit preprocessing data.

        Useful voor metrics logging en debugging.
        """
        shots = preprocessing_data['shots']
        motion_vectors = preprocessing_data['motion_vectors']

        # Shot type distributie
        shot_types = {}
        for shot in shots:
            shot_type = shot['type']
            shot_types[shot_type] = shot_types.get(shot_type, 0) + 1

        # Camera movement distributie
        motion_directions = {}
        for vector in motion_vectors:
            direction = vector['direction']
            motion_directions[direction] = motion_directions.get(direction, 0) + 1

        avg_motion_magnitude = (
            sum(v['magnitude'] for v in motion_vectors) / len(motion_vectors)
            if motion_vectors else 0
        )

        return {
            "total_shots": len(shots),
            "shot_type_distribution": shot_types,
            "dominant_shot_type": max(shot_types, key=shot_types.get) if shot_types else None,
            "total_motion_samples": len(motion_vectors),
            "motion_direction_distribution": motion_directions,
            "average_motion_magnitude": avg_motion_magnitude,
            "preprocessing_time": preprocessing_data.get('preprocessing_time', 0)
        }


def main():
    """CLI entry point voor testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python cinematic_composer.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize composer
    composer = CinematicComposer()

    # Preprocess video
    preprocessing_data = composer.preprocess_video(video_path)

    # Print statistics
    stats = composer.get_statistics(preprocessing_data)

    print(json.dumps({
        "success": True,
        "statistics": stats,
        "composer_version": composer.version
    }, indent=2))

    # Test composition voor random moment @ 10s
    test_moment = {
        "start_time": 8.0,
        "end_time": 12.0,
        "timestamp": 10.0
    }

    # Mock face data
    test_faces = [{
        "x": 400,
        "y": 200,
        "width": 300,
        "height": 400,
        "center_x": 0.35,
        "center_y": 0.30,
        "confidence": 0.95
    }]

    # Compose crop
    crop_result = composer.compose_for_moment(
        video_path=video_path,
        moment=test_moment,
        faces=test_faces,
        orig_w=1920,
        orig_h=1080,
        preprocessing_data=preprocessing_data
    )

    print("\nTest composition @ 10s:")
    print(json.dumps(crop_result, indent=2))


if __name__ == "__main__":
    main()
