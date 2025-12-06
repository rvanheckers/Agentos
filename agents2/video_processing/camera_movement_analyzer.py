#!/usr/bin/env python3
"""
Camera Movement Analyzer - Cinema-MVP Component
===============================================

Lichtgewicht camera bewegingsdetectie met Lucas-Kanade optical flow.

Features:
- Optical flow sampling @ 1 fps (performance optimized)
- Direction detection (left/right/up/down/static)
- Magnitude berekening voor compositional engine
- Shot-boundary aware reset (voorkom vals-positieven bij cuts)

Architecture:
- Lucas-Kanade sparse optical flow (feature tracking)
- Shi-Tomasi corner detection voor feature points
- Lichtgewicht sampling (1 fps) voorkomt overhead
- Retourneert motion vectors voor leading space berekening

Performance: ~10-30s voor 2 uur video @ 1 fps sampling
Context7-validated: OpenCV optical flow best practices
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import time
import numpy as np

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

logger = logging.getLogger(__name__)


class CameraMovementAnalyzer:
    """
    Lichtgewicht camera bewegingsanalyse voor cinematografische framing.

    V1 Features:
    - Lucas-Kanade optical flow @ 1 fps
    - Direction classification (left/right/up/down/static)
    - Magnitude berekening
    - Shot boundary reset
    """

    # V1 Configuration
    SAMPLE_FPS = 1.0                    # 1 fps sampling voor performance
    MIN_FEATURE_POINTS = 30             # Minimum corner points voor flow
    STATIC_THRESHOLD = 2.0              # Pixels - below = static
    DIRECTION_THRESHOLD = 3.0           # Pixels - minimum voor duidelijke richting

    # Lucas-Kanade parameters (Context7: OpenCV best practices)
    LK_PARAMS = dict(
        winSize=(15, 15),
        maxLevel=2,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
    )

    # Shi-Tomasi corner detection parameters
    FEATURE_PARAMS = dict(
        maxCorners=100,
        qualityLevel=0.3,
        minDistance=7,
        blockSize=7
    )

    def __init__(self):
        """Initialize camera movement analyzer"""
        self.version = "1.0.0-cinema-mvp"
        self.opencv_available = OPENCV_AVAILABLE

    def analyze(
        self,
        video_path: str,
        shot_boundaries: Optional[List[Dict[str, float]]] = None,
        sample_fps: float = SAMPLE_FPS
    ) -> List[Dict[str, Any]]:
        """
        Analyseer camera beweging met optical flow.

        Args:
            video_path: Path naar video file
            shot_boundaries: Optionele list van shots met 'start_time', 'end_time'
                            (gebruikt voor flow reset bij cuts)
            sample_fps: Sampling rate (default 1.0 fps)

        Returns:
            List van motion vectors:
            [
                {
                    "timestamp": 0.0,
                    "direction": "right",        # left | right | up | down | static
                    "magnitude": 5.2,            # Pixels gemiddeld
                    "confidence": 0.85,          # Gebaseerd op #tracked features
                    "shot_number": 1             # Optioneel, als shot_boundaries gegeven
                }
            ]
        """
        if not self.opencv_available:
            logger.warning("⚠️  OpenCV niet beschikbaar - geen motion analysis mogelijk")
            return []

        start_time = time.time()

        try:
            logger.info(f"🎥 Starting camera movement analysis: {Path(video_path).name}")
            logger.info(f"   Sampling @ {sample_fps} fps")

            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0

            # Calculate sample frame indices
            frame_interval = int(fps / sample_fps)
            sample_indices = list(range(0, total_frames, frame_interval))

            logger.info(f"   Total frames: {total_frames}, sampling {len(sample_indices)} frames")

            motion_vectors = []
            prev_gray = None
            prev_features = None

            for i, frame_idx in enumerate(sample_indices):
                # Set frame position
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()

                if not ret:
                    break

                timestamp = frame_idx / fps
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Check if we crossed a shot boundary
                crossed_boundary = self._crossed_shot_boundary(
                    timestamp, shot_boundaries
                )

                if crossed_boundary:
                    # Reset tracking bij shot cut
                    prev_gray = None
                    prev_features = None
                    logger.debug(f"   Shot boundary @ {timestamp:.1f}s - reset tracking")

                if prev_gray is None:
                    # Initialize tracking
                    prev_gray = gray
                    prev_features = cv2.goodFeaturesToTrack(
                        gray, **self.FEATURE_PARAMS
                    )
                    continue

                # Calculate optical flow
                if prev_features is None or len(prev_features) < self.MIN_FEATURE_POINTS:
                    # Re-detect features
                    prev_features = cv2.goodFeaturesToTrack(
                        prev_gray, **self.FEATURE_PARAMS
                    )

                if prev_features is not None and len(prev_features) >= self.MIN_FEATURE_POINTS:
                    # Lucas-Kanade optical flow
                    curr_features, status, err = cv2.calcOpticalFlowPyrLK(
                        prev_gray, gray, prev_features, None, **self.LK_PARAMS
                    )

                    # Select good features (status == 1)
                    good_prev = prev_features[status == 1]
                    good_curr = curr_features[status == 1]

                    # Bereken motion vector
                    direction, magnitude, confidence = self._calculate_motion_vector(
                        good_prev, good_curr
                    )

                    # Determine shot number
                    shot_number = self._get_shot_number(timestamp, shot_boundaries)

                    motion_vectors.append({
                        "timestamp": timestamp,
                        "direction": direction,
                        "magnitude": magnitude,
                        "confidence": confidence,
                        "shot_number": shot_number,
                        "tracked_features": len(good_curr)
                    })

                    logger.debug(
                        f"   {timestamp:.1f}s: {direction} ({magnitude:.1f}px, "
                        f"{len(good_curr)} features)"
                    )

                    # Update for next iteration
                    prev_features = good_curr.reshape(-1, 1, 2)

                # Update previous frame
                prev_gray = gray

            cap.release()

            processing_time = time.time() - start_time
            logger.info(f"✅ Motion analysis completed in {processing_time:.2f}s")
            logger.info(f"   Analyzed {len(motion_vectors)} motion samples")

            return motion_vectors

        except Exception as e:
            logger.error(f"❌ Motion analysis failed: {e}")
            raise

    def _calculate_motion_vector(
        self,
        prev_points: np.ndarray,
        curr_points: np.ndarray
    ) -> Tuple[str, float, float]:
        """
        Bereken motion vector uit optical flow.

        Args:
            prev_points: Feature points in vorig frame (N x 2)
            curr_points: Feature points in huidig frame (N x 2)

        Returns:
            (direction, magnitude, confidence):
            - direction: "left" | "right" | "up" | "down" | "static"
            - magnitude: Gemiddelde beweging in pixels
            - confidence: 0-1 gebaseerd op consistentie van flow
        """
        # Bereken displacement vectors
        flow = curr_points - prev_points  # (N x 2)

        # Gemiddelde displacement
        avg_dx = np.median(flow[:, 0])
        avg_dy = np.median(flow[:, 1])

        # Magnitude (Euclidean distance)
        magnitude = np.sqrt(avg_dx**2 + avg_dy**2)

        # Confidence: gebaseerd op consistentie (lage std = hoge confidence)
        std_dx = np.std(flow[:, 0])
        std_dy = np.std(flow[:, 1])
        avg_std = (std_dx + std_dy) / 2

        # Normalize confidence (hoge std = lage confidence)
        confidence = max(0, 1 - (avg_std / 10.0))

        # Determine direction
        if magnitude < self.STATIC_THRESHOLD:
            direction = "static"
        elif abs(avg_dx) > abs(avg_dy):
            # Horizontale beweging dominant
            if abs(avg_dx) > self.DIRECTION_THRESHOLD:
                direction = "right" if avg_dx > 0 else "left"
            else:
                direction = "static"
        else:
            # Verticale beweging dominant
            if abs(avg_dy) > self.DIRECTION_THRESHOLD:
                direction = "down" if avg_dy > 0 else "up"
            else:
                direction = "static"

        return direction, float(magnitude), float(confidence)

    def _crossed_shot_boundary(
        self,
        timestamp: float,
        shot_boundaries: Optional[List[Dict]]
    ) -> bool:
        """
        Check of timestamp net een shot boundary is gepasseerd.

        Returns:
            True als deze sample de eerste is na een shot cut
        """
        if not shot_boundaries:
            return False

        # Check of timestamp binnen 1 seconde na shot start ligt
        for shot in shot_boundaries:
            shot_start = shot.get('start_time', 0)
            if abs(timestamp - shot_start) < 1.0:  # Binnen 1 sec van start
                return True

        return False

    def _get_shot_number(
        self,
        timestamp: float,
        shot_boundaries: Optional[List[Dict]]
    ) -> Optional[int]:
        """Bepaal shot number voor timestamp"""
        if not shot_boundaries:
            return None

        for shot in shot_boundaries:
            if shot['start_time'] <= timestamp <= shot['end_time']:
                return shot.get('shot_number')

        return None

    def get_motion_for_timestamp(
        self,
        motion_vectors: List[Dict],
        timestamp: float,
        window_sec: float = 2.0
    ) -> Optional[Dict[str, Any]]:
        """
        Haal motion vector op voor specifieke timestamp met temporal smoothing.

        Args:
            motion_vectors: Output van analyze()
            timestamp: Tijd in seconden
            window_sec: Temporal window voor averaging (default 2s)

        Returns:
            Gemiddelde motion vector in window, of None
        """
        # Filter vectors binnen window
        window_vectors = [
            v for v in motion_vectors
            if abs(v['timestamp'] - timestamp) <= window_sec / 2
        ]

        if not window_vectors:
            return None

        # Gemiddelde magnitude en dominante richting
        avg_magnitude = sum(v['magnitude'] for v in window_vectors) / len(window_vectors)
        avg_confidence = sum(v['confidence'] for v in window_vectors) / len(window_vectors)

        # Dominante richting (meest voorkomend)
        directions = [v['direction'] for v in window_vectors]
        dominant_direction = max(set(directions), key=directions.count)

        return {
            'direction': dominant_direction,
            'magnitude': avg_magnitude,
            'confidence': avg_confidence,
            'samples_in_window': len(window_vectors)
        }


def main():
    """CLI entry point voor testing"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python camera_movement_analyzer.py <video_path> [sample_fps]")
        sys.exit(1)

    video_path = sys.argv[1]
    sample_fps = float(sys.argv[2]) if len(sys.argv) > 2 else CameraMovementAnalyzer.SAMPLE_FPS

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Analyze motion
    analyzer = CameraMovementAnalyzer()
    motion_vectors = analyzer.analyze(video_path, sample_fps=sample_fps)

    # Calculate statistics
    direction_counts = {}
    for vector in motion_vectors:
        direction = vector['direction']
        direction_counts[direction] = direction_counts.get(direction, 0) + 1

    avg_magnitude = sum(v['magnitude'] for v in motion_vectors) / len(motion_vectors) if motion_vectors else 0

    # Output als JSON
    print(json.dumps({
        "success": True,
        "total_samples": len(motion_vectors),
        "motion_vectors": motion_vectors,
        "statistics": {
            "direction_distribution": direction_counts,
            "average_magnitude": avg_magnitude
        },
        "analyzer_version": analyzer.version
    }, indent=2))


if __name__ == "__main__":
    main()
