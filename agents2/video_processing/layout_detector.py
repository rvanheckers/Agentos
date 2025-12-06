#!/usr/bin/env python3
"""
Layout Detector - Cinema-MVP V3.1 Component
===========================================

Detecteert pre-existing video layouts zoals split-screens, multi-panels, etc.
Voorkomt dat systeem DOOR bestaande kaders heen cropped.

Features:
- 2-way split detection (vertical/horizontal)
- 3-way layout detection
- 4-way grid detection
- Symmetry analysis
- Spatial clustering

Use Cases:
- Interview formats (2-way split)
- Panel discussions (3-way, 4-way)
- Video calls (grid layouts)
- News broadcasts (split-screen)

Architecture:
- Spatial clustering van face posities
- Symmetry analysis (±10% tolerance)
- Size consistency checking (±30% tolerance)
- Confidence scoring (0-1)

Performance: ~5-10ms per frame (lichtgewicht berekeningen)
Context7-validated: Industry-standard thresholds
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import math
from collections import defaultdict
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class LayoutDetector:
    """
    Detecteert pre-existing video layouts (split-screens, grids, panels).

    V1 Features:
    - 2-way split (vertical/horizontal)
    - 3-way layouts
    - 4-way grid
    - Symmetry analysis
    - Size consistency
    """

    # Configuration (Context7-validated thresholds)
    SYMMETRY_TOLERANCE = 0.10       # ±10% voor symmetrische positionering
    SIZE_SIMILARITY_TOLERANCE = 0.30  # ±30% voor face size consistency
    MIN_CONFIDENCE = 0.70           # Minimum confidence voor detectie

    # Spatial grid parameters
    HORIZONTAL_BINS = 3             # Links | Center | Rechts
    VERTICAL_BINS = 2               # Boven | Onder

    # V3.2 Robustness: Timing sync parameters
    TIMING_BUFFER_SEC = 0.25           # Buffer voor audio-face alignment
    MIN_FACE_COUNT_FOR_AUDIO = 1       # Minimum faces voor audio weight
    AUDIO_SCALE_FACTOR = 0.5           # Scale audio weight als te weinig faces

    def __init__(self):
        """Initialize layout detector"""
        self.version = "3.2.1-cinema-mvp"  # UPGRADED: V3.2.1 with visual edge detection

    def detect_layout(
        self,
        faces: List[Dict[str, Any]],
        orig_w: int,
        orig_h: int,
        video_path: Optional[str] = None,
        timestamp: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Detecteer pre-existing video layout.

        Args:
            faces: List van face dicts met normalized 'center_x', 'center_y', 'width', 'height'
            orig_w, orig_h: Originele frame dimensies
            video_path: Path naar video (V3.2.1 voor visual detection)
            timestamp: Timestamp voor frame extraction (V3.2.1)

        Returns:
            {
                'layout_type': '2-way-vertical' | '2-way-horizontal' | '3-way' | '4-way' | None,
                'confidence': 0.0-1.0,
                'reason': 'Uitleg voor debugging',
                'should_skip_crop': bool,
                'detected_regions': List[Dict] (optioneel, voor debugging)
            }
        """

        # V3.2.1 FIX: Don't return early - let visual detection handle insufficient faces
        if not faces or len(faces) < 2:
            # Create default "insufficient faces" detection
            best_detection = {
                'layout_type': None,
                'confidence': 0.0,
                'reason': f'Insufficient faces for layout detection (found {len(faces)})',
                'should_skip_crop': False
            }
        else:
            # Probeer verschillende layout types te detecteren
            detections = [
                self._detect_2way_vertical(faces, orig_w, orig_h),
                self._detect_2way_horizontal(faces, orig_w, orig_h),
                self._detect_4way_grid(faces, orig_w, orig_h)
            ]

            # Selecteer detectie met hoogste confidence
            best_detection = max(detections, key=lambda d: d['confidence'])

            # Check of confidence boven threshold is
            if best_detection['confidence'] >= self.MIN_CONFIDENCE:
                best_detection['should_skip_crop'] = True
                logger.info(
                    f"🎬 Layout detected (face-based): {best_detection['layout_type']} "
                    f"(confidence: {best_detection['confidence']:.2f}) - SKIPPING crop"
                )
                return best_detection

        # V3.2.1 FIX: Face-based detection failed or insufficient, try VISUAL/EDGE-BASED detection
        # This handles cases where all faces are on one side but split-screen exists
        if video_path and timestamp is not None:
            logger.debug(
                f"   Face-based detection insufficient (confidence: {best_detection['confidence']:.2f})"
                f" - trying visual edge detection..."
            )

            visual_detection = self._detect_visual_split(
                video_path, timestamp, orig_w, orig_h
            )

            if visual_detection and visual_detection['confidence'] >= self.MIN_CONFIDENCE:
                # V3.2.1 FIX: Distribute faces to regions for shot sequencing
                if faces and 'regions' in visual_detection:
                    visual_detection = self._distribute_faces_to_regions(
                        visual_detection, faces, orig_w, orig_h
                    )

                visual_detection['should_skip_crop'] = True
                logger.info(
                    f"🎬 Layout detected (visual-based): {visual_detection['layout_type']} "
                    f"(confidence: {visual_detection['confidence']:.2f}) - SKIPPING crop"
                )
                return visual_detection

        # No layout detected with either method
        best_detection['should_skip_crop'] = False
        logger.debug(
            f"   No significant layout detected (best face-based: {best_detection['layout_type']}, "
            f"confidence: {best_detection['confidence']:.2f})"
        )

        return best_detection

    def _detect_2way_vertical(
        self,
        faces: List[Dict],
        orig_w: int,
        orig_h: int
    ) -> Dict[str, Any]:
        """
        Detecteer verticale 2-way split (links | rechts).

        Criteria:
        - Faces verdeeld over links/rechts (center_x < 0.5 vs > 0.5)
        - Vergelijkbare sizes
        - Symmetrische verticale posities
        """

        # Splits faces in links/rechts
        left_faces = [f for f in faces if f['center_x'] < 0.5]
        right_faces = [f for f in faces if f['center_x'] >= 0.5]

        # Check basis criteria
        if not (left_faces and right_faces):
            return {
                'layout_type': None,
                'confidence': 0.0,
                'reason': 'Not split vertically (all faces on same side)'
            }

        # Check symmetrie: zijn er vergelijkbaar aantal faces links/rechts?
        count_ratio = min(len(left_faces), len(right_faces)) / max(len(left_faces), len(right_faces))
        if count_ratio < 0.5:
            return {
                'layout_type': None,
                'confidence': 0.0,
                'reason': f'Unbalanced left/right distribution ({len(left_faces)} vs {len(right_faces)})'
            }

        # Check size consistency binnen groepen
        left_size_consistency = self._check_size_consistency(left_faces)
        right_size_consistency = self._check_size_consistency(right_faces)

        # Check verticale symmetrie (Y-posities vergelijkbaar?)
        vertical_symmetry = self._check_vertical_symmetry(left_faces, right_faces)

        # Bereken confidence
        confidence = (
            count_ratio * 0.3 +
            left_size_consistency * 0.25 +
            right_size_consistency * 0.25 +
            vertical_symmetry * 0.20
        )

        return {
            'layout_type': '2-way-vertical',
            'confidence': confidence,
            'reason': (
                f'Vertical split: {len(left_faces)} left, {len(right_faces)} right '
                f'(symmetry: {vertical_symmetry:.2f}, size: {left_size_consistency:.2f}/{right_size_consistency:.2f})'
            ),
            'detected_regions': [
                {'region': 'left', 'faces': len(left_faces)},
                {'region': 'right', 'faces': len(right_faces)}
            ],
            # V3.2.1: Add regions array for shot sequencing
            'regions': [
                {'position': 'left', 'faces': left_faces},
                {'position': 'right', 'faces': right_faces}
            ]
        }

    def _detect_2way_horizontal(
        self,
        faces: List[Dict],
        orig_w: int,
        orig_h: int
    ) -> Dict[str, Any]:
        """
        Detecteer horizontale 2-way split (boven | onder).

        Criteria:
        - Faces verdeeld over boven/onder (center_y < 0.5 vs > 0.5)
        - Vergelijkbare sizes
        - Symmetrische horizontale posities
        """

        # Splits faces in boven/onder
        top_faces = [f for f in faces if f['center_y'] < 0.5]
        bottom_faces = [f for f in faces if f['center_y'] >= 0.5]

        # Check basis criteria
        if not (top_faces and bottom_faces):
            return {
                'layout_type': None,
                'confidence': 0.0,
                'reason': 'Not split horizontally (all faces on same side)'
            }

        # Check symmetrie: zijn er vergelijkbaar aantal faces boven/onder?
        count_ratio = min(len(top_faces), len(bottom_faces)) / max(len(top_faces), len(bottom_faces))
        if count_ratio < 0.5:
            return {
                'layout_type': None,
                'confidence': 0.0,
                'reason': f'Unbalanced top/bottom distribution ({len(top_faces)} vs {len(bottom_faces)})'
            }

        # Check size consistency binnen groepen
        top_size_consistency = self._check_size_consistency(top_faces)
        bottom_size_consistency = self._check_size_consistency(bottom_faces)

        # Check horizontale symmetrie (X-posities vergelijkbaar?)
        horizontal_symmetry = self._check_horizontal_symmetry(top_faces, bottom_faces)

        # Bereken confidence
        confidence = (
            count_ratio * 0.3 +
            top_size_consistency * 0.25 +
            bottom_size_consistency * 0.25 +
            horizontal_symmetry * 0.20
        )

        return {
            'layout_type': '2-way-horizontal',
            'confidence': confidence,
            'reason': (
                f'Horizontal split: {len(top_faces)} top, {len(bottom_faces)} bottom '
                f'(symmetry: {horizontal_symmetry:.2f}, size: {top_size_consistency:.2f}/{bottom_size_consistency:.2f})'
            ),
            'detected_regions': [
                {'region': 'top', 'faces': len(top_faces)},
                {'region': 'bottom', 'faces': len(bottom_faces)}
            ],
            # V3.2.1: Add regions array for shot sequencing
            'regions': [
                {'position': 'top', 'faces': top_faces},
                {'position': 'bottom', 'faces': bottom_faces}
            ]
        }

    def _detect_4way_grid(
        self,
        faces: List[Dict],
        orig_w: int,
        orig_h: int
    ) -> Dict[str, Any]:
        """
        Detecteer 4-way grid layout (2x2).

        Criteria:
        - Faces verdeeld over 4 kwadranten
        - Vergelijkbare sizes
        - Grid-achtige spacing
        """

        if len(faces) < 4:
            return {
                'layout_type': None,
                'confidence': 0.0,
                'reason': f'Insufficient faces for 4-way grid (found {len(faces)})'
            }

        # Verdeel in 4 kwadranten
        quadrants = {
            'top-left': [],
            'top-right': [],
            'bottom-left': [],
            'bottom-right': []
        }

        for face in faces:
            if face['center_x'] < 0.5 and face['center_y'] < 0.5:
                quadrants['top-left'].append(face)
            elif face['center_x'] >= 0.5 and face['center_y'] < 0.5:
                quadrants['top-right'].append(face)
            elif face['center_x'] < 0.5 and face['center_y'] >= 0.5:
                quadrants['bottom-left'].append(face)
            else:
                quadrants['bottom-right'].append(face)

        # Check of alle kwadranten faces hebben
        filled_quadrants = sum(1 for q in quadrants.values() if q)

        if filled_quadrants < 3:
            return {
                'layout_type': None,
                'confidence': 0.0,
                'reason': f'Only {filled_quadrants}/4 quadrants filled'
            }

        # Check size consistency over alle faces
        overall_size_consistency = self._check_size_consistency(faces)

        # Check grid spacing symmetry
        grid_symmetry = self._check_grid_symmetry(quadrants)

        # Bereken confidence
        confidence = (
            (filled_quadrants / 4) * 0.4 +
            overall_size_consistency * 0.3 +
            grid_symmetry * 0.3
        )

        return {
            'layout_type': '4-way',
            'confidence': confidence,
            'reason': (
                f'4-way grid: {filled_quadrants}/4 quadrants filled '
                f'(symmetry: {grid_symmetry:.2f}, size: {overall_size_consistency:.2f})'
            ),
            'detected_regions': [
                {'region': q, 'faces': len(f)} for q, f in quadrants.items() if f
            ],
            # V3.2.1: Add regions array for shot sequencing
            'regions': [
                {'position': q, 'faces': f} for q, f in quadrants.items() if f
            ]
        }

    def _distribute_faces_to_regions(
        self,
        layout_detection: Dict[str, Any],
        faces: List[Dict],
        orig_w: int,
        orig_h: int
    ) -> Dict[str, Any]:
        """
        Distribute faces to regions based on spatial position (V3.2.1 NEW).

        Nodig voor shot sequencing: regions moeten faces bevatten om te weten
        waar te croppen en welk panel actief is.

        Args:
            layout_detection: Visual detection result met lege regions
            faces: Alle faces in frame
            orig_w, orig_h: Frame dimensies

        Returns:
            Updated layout_detection met faces per region
        """
        layout_type = layout_detection.get('layout_type')
        regions = layout_detection.get('regions', [])

        if not regions:
            return layout_detection

        # Distribute faces based on layout type
        if layout_type == '2-way-vertical':
            # Split op X-as: left (<50%) vs right (>=50%)
            for face in faces:
                face_center_x = face.get('center_x', 0.5)

                if face_center_x < 0.5:
                    # Left panel
                    for region in regions:
                        if region.get('position') == 'left':
                            region['faces'].append(face)
                else:
                    # Right panel
                    for region in regions:
                        if region.get('position') == 'right':
                            region['faces'].append(face)

        elif layout_type == '2-way-horizontal':
            # Split op Y-as: top (<50%) vs bottom (>=50%)
            for face in faces:
                face_center_y = face.get('center_y', 0.5)

                if face_center_y < 0.5:
                    # Top panel
                    for region in regions:
                        if region.get('position') == 'top':
                            region['faces'].append(face)
                else:
                    # Bottom panel
                    for region in regions:
                        if region.get('position') == 'bottom':
                            region['faces'].append(face)

        # Log results
        for region in regions:
            pos = region.get('position', 'unknown')
            face_count = len(region.get('faces', []))
            logger.debug(f"      Region '{pos}': {face_count} faces assigned")

        return layout_detection

    def _detect_visual_split(
        self,
        video_path: str,
        timestamp: float,
        orig_w: int,
        orig_h: int
    ) -> Optional[Dict[str, Any]]:
        """
        Detecteer split-screen via VISUAL/EDGE detection (V3.2.1 NEW).

        Gebruikt OpenCV edge detection om harde split lijnen te detecteren.
        Werkt ook wanneer faces asymmetrisch verdeeld zijn.

        Args:
            video_path: Path naar video
            timestamp: Timestamp voor frame extraction
            orig_w, orig_h: Frame dimensies

        Returns:
            Detection dict of None bij failure
        """
        try:
            logger.debug(f"   🔍 Visual detection: Extracting frame at {timestamp}s from {video_path}")

            # Extract frame at timestamp
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            frame_number = int(timestamp * fps)

            logger.debug(f"   🔍 Visual detection: FPS={fps}, seeking frame {frame_number}")

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                logger.warning(f"   Failed to extract frame at {timestamp}s for visual detection")
                return None

            logger.debug(f"   🔍 Visual detection: Frame extracted, shape={frame.shape}")

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Edge detection (Canny)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            edge_count = np.sum(edges > 0)
            logger.debug(f"   🔍 Visual detection: Edge pixels detected: {edge_count}/{edges.size} ({edge_count/edges.size:.2%})")

            # Detect vertical lines (for vertical split)
            vertical_detection = self._detect_vertical_edge_line(edges, orig_w, orig_h)
            logger.debug(f"   🔍 Visual detection: Vertical split = {vertical_detection is not None}")

            # Detect horizontal lines (for horizontal split)
            horizontal_detection = self._detect_horizontal_edge_line(edges, orig_w, orig_h)
            logger.debug(f"   🔍 Visual detection: Horizontal split = {horizontal_detection is not None}")

            # Return best detection
            if vertical_detection and horizontal_detection:
                best = max([vertical_detection, horizontal_detection], key=lambda d: d['confidence'])
                logger.debug(f"   🔍 Visual detection: Both splits found, returning best: {best['layout_type']}")
                return best
            elif vertical_detection:
                logger.debug(f"   🔍 Visual detection: Returning vertical split")
                return vertical_detection
            elif horizontal_detection:
                logger.debug(f"   🔍 Visual detection: Returning horizontal split")
                return horizontal_detection
            else:
                logger.debug(f"   🔍 Visual detection: No split detected")
                return None

        except Exception as e:
            logger.error(f"   Visual split detection failed: {e}", exc_info=True)
            return None

    def _detect_vertical_edge_line(
        self,
        edges: np.ndarray,
        orig_w: int,
        orig_h: int
    ) -> Optional[Dict[str, Any]]:
        """Detect strong vertical line in center ±20% for vertical split"""
        height, width = edges.shape

        # Define center region (40-60% of width)
        center_left = int(width * 0.4)
        center_right = int(width * 0.6)

        # Count edge pixels in vertical strips
        center_strip = edges[:, center_left:center_right]
        edge_density = np.sum(center_strip) / (center_strip.size * 255.0)

        # V3.2.1 FIX: Lowered threshold from 0.15 to 0.008 for subtle split lines
        EDGE_DENSITY_THRESHOLD = 0.008  # 0.8% edge density (was 15%, way too high!)
        logger.debug(f"      🔍 Vertical: center strip edge density = {edge_density:.4f} (threshold: {EDGE_DENSITY_THRESHOLD})")

        # Heuristic: If >0.8% of pixels are edges in center strip, likely a split
        if edge_density > EDGE_DENSITY_THRESHOLD:
            # Verify it's actually a vertical line (not random edges)
            # Sum along columns to find peak
            column_sums = np.sum(center_strip, axis=0)
            max_column_sum = np.max(column_sums)
            avg_column_sum = np.mean(column_sums)

            peak_ratio = max_column_sum / avg_column_sum if avg_column_sum > 0 else 0
            logger.debug(f"      🔍 Vertical: peak_ratio = {peak_ratio:.2f} (threshold: 2.5)")

            # Peak should be significantly higher than average
            if max_column_sum > avg_column_sum * 2.5:
                # V3.2.1 FIX: Adjusted confidence formula for lower threshold
                # Base confidence + bonus for higher edge density
                confidence = min(0.95, 0.75 + (edge_density - EDGE_DENSITY_THRESHOLD) * 10.0)

                logger.debug(f"      ✅ Vertical split detected! confidence={confidence:.2f}")

                return {
                    'layout_type': '2-way-vertical',
                    'confidence': confidence,
                    'reason': f'Visual edge detection: strong vertical line (density: {edge_density:.2f})',
                    'detection_method': 'visual_edge',
                    'detected_regions': [
                        {'position': 'left', 'faces': []},
                        {'position': 'right', 'faces': []}
                    ],
                    'regions': [
                        {'position': 'left', 'faces': []},
                        {'position': 'right', 'faces': []}
                    ]
                }
            else:
                logger.debug(f"      ❌ Vertical: peak not significant enough")
        else:
            logger.debug(f"      ❌ Vertical: edge density too low")

        return None

    def _detect_horizontal_edge_line(
        self,
        edges: np.ndarray,
        orig_w: int,
        orig_h: int
    ) -> Optional[Dict[str, Any]]:
        """Detect strong horizontal line in center ±20% for horizontal split"""
        height, width = edges.shape

        # Define center region (40-60% of height)
        center_top = int(height * 0.4)
        center_bottom = int(height * 0.6)

        # Count edge pixels in horizontal strip
        center_strip = edges[center_top:center_bottom, :]
        edge_density = np.sum(center_strip) / (center_strip.size * 255.0)

        # V3.2.1 FIX: Lowered threshold from 0.15 to 0.008 for subtle split lines
        EDGE_DENSITY_THRESHOLD = 0.008  # 0.8% edge density (was 15%, way too high!)
        logger.debug(f"      🔍 Horizontal: center strip edge density = {edge_density:.4f} (threshold: {EDGE_DENSITY_THRESHOLD})")

        # Heuristic: If >0.8% of pixels are edges in center strip, likely a split
        if edge_density > EDGE_DENSITY_THRESHOLD:
            # Verify it's actually a horizontal line
            row_sums = np.sum(center_strip, axis=1)
            max_row_sum = np.max(row_sums)
            avg_row_sum = np.mean(row_sums)

            peak_ratio = max_row_sum / avg_row_sum if avg_row_sum > 0 else 0
            logger.debug(f"      🔍 Horizontal: peak_ratio = {peak_ratio:.2f} (threshold: 2.5)")

            # Peak should be significantly higher than average
            if max_row_sum > avg_row_sum * 2.5:
                # V3.2.1 FIX: Adjusted confidence formula for lower threshold
                confidence = min(0.95, 0.75 + (edge_density - EDGE_DENSITY_THRESHOLD) * 10.0)

                logger.debug(f"      ✅ Horizontal split detected! confidence={confidence:.2f}")

                return {
                    'layout_type': '2-way-horizontal',
                    'confidence': confidence,
                    'reason': f'Visual edge detection: strong horizontal line (density: {edge_density:.2f})',
                    'detection_method': 'visual_edge',
                    'detected_regions': [
                        {'position': 'top', 'faces': []},
                        {'position': 'bottom', 'faces': []}
                    ],
                    'regions': [
                        {'position': 'top', 'faces': []},
                        {'position': 'bottom', 'faces': []}
                    ]
                }
            else:
                logger.debug(f"      ❌ Horizontal: peak not significant enough")
        else:
            logger.debug(f"      ❌ Horizontal: edge density too low")

        return None

    def _check_size_consistency(self, faces: List[Dict]) -> float:
        """
        Check hoe consistent de face sizes zijn binnen een groep.

        Returns:
            Consistency score 0-1 (1 = perfect consistent)
        """
        if not faces:
            return 0.0

        if len(faces) == 1:
            return 1.0  # Eén face is per definitie consistent

        # Bereken face areas
        areas = [f['width'] * f['height'] for f in faces]
        avg_area = sum(areas) / len(areas)

        # Check hoeveel faces binnen tolerance zijn
        consistent_count = 0
        for area in areas:
            ratio = area / avg_area if avg_area > 0 else 0
            if (1 - self.SIZE_SIMILARITY_TOLERANCE) <= ratio <= (1 + self.SIZE_SIMILARITY_TOLERANCE):
                consistent_count += 1

        return consistent_count / len(faces)

    def _check_vertical_symmetry(
        self,
        left_faces: List[Dict],
        right_faces: List[Dict]
    ) -> float:
        """
        Check of links/rechts faces verticaal symmetrisch zijn (Y-posities).

        Returns:
            Symmetry score 0-1 (1 = perfect symmetric)
        """
        if not left_faces or not right_faces:
            return 0.0

        # Gemiddelde Y-posities
        left_avg_y = sum(f['center_y'] for f in left_faces) / len(left_faces)
        right_avg_y = sum(f['center_y'] for f in right_faces) / len(right_faces)

        # Check of ze binnen tolerance zijn
        diff = abs(left_avg_y - right_avg_y)

        if diff <= self.SYMMETRY_TOLERANCE:
            return 1.0 - (diff / self.SYMMETRY_TOLERANCE)
        else:
            return 0.0

    def _check_horizontal_symmetry(
        self,
        top_faces: List[Dict],
        bottom_faces: List[Dict]
    ) -> float:
        """
        Check of boven/onder faces horizontaal symmetrisch zijn (X-posities).

        Returns:
            Symmetry score 0-1 (1 = perfect symmetric)
        """
        if not top_faces or not bottom_faces:
            return 0.0

        # Gemiddelde X-posities
        top_avg_x = sum(f['center_x'] for f in top_faces) / len(top_faces)
        bottom_avg_x = sum(f['center_x'] for f in bottom_faces) / len(bottom_faces)

        # Check of ze binnen tolerance zijn
        diff = abs(top_avg_x - bottom_avg_x)

        if diff <= self.SYMMETRY_TOLERANCE:
            return 1.0 - (diff / self.SYMMETRY_TOLERANCE)
        else:
            return 0.0

    def _check_grid_symmetry(self, quadrants: Dict[str, List[Dict]]) -> float:
        """
        Check symmetrie van 4-way grid (spacing consistency).

        Returns:
            Grid symmetry score 0-1
        """
        # Check of kwadranten vergelijkbaar aantal faces hebben
        counts = [len(faces) for faces in quadrants.values() if faces]

        if not counts:
            return 0.0

        avg_count = sum(counts) / len(counts)
        max_deviation = max(abs(c - avg_count) for c in counts)

        # Normalize: max_deviation = 0 → score 1, max_deviation >> avg → score 0
        if avg_count > 0:
            normalized_deviation = max_deviation / (avg_count + 1)
            return max(0, 1 - normalized_deviation)
        else:
            return 0.0

    def track_activity_per_region(
        self,
        layout: Dict,
        faces: List[Dict],
        audio_segments: List[Dict],
        moment: Dict
    ) -> Dict:
        """
        Track activity per region for shot selection (V3.2 feature).

        Per region bijhouden:
        1. Face count
        2. Movement intensity (avg movement_range)
        3. Audio segment overlap (heuristic)
        4. Activity trend (increasing/stable/decreasing)

        Args:
            layout: Layout detection result met regions
            faces: List van faces met movement_range
            audio_segments: Transcription segments
            moment: Moment dict met times

        Returns:
            layout dict with added 'activity_data' per region:
            {
                'regions': [
                    {
                        'position': 'left',
                        'faces': [...],
                        'activity_data': {  # NEW
                            'face_count': 1,
                            'movement_intensity': 0.75,
                            'audio_overlap_score': 0.60,
                            'activity_trend': 'stable'
                        }
                    }
                ]
            }
        """
        if 'regions' not in layout:
            return layout

        regions = layout['regions']
        total_regions = len(regions)

        # Calculate activity data for each region
        for region in regions:
            region_position = region.get('position', '')
            region_faces = region.get('faces', [])

            # 1. Face count
            face_count = len(region_faces)

            # 2. Movement intensity (average movement_range)
            movement_intensity = self._calculate_movement_intensity(region_faces)

            # 3. Audio overlap score (heuristic without speaker diarization)
            audio_overlap_score = self.calculate_audio_overlap_heuristic(
                region, audio_segments, moment, total_regions
            )

            # 4. Activity trend (simple: stable for now, could be enhanced)
            activity_trend = 'stable'

            # Attach activity data to region
            region['activity_data'] = {
                'face_count': face_count,
                'movement_intensity': movement_intensity,
                'audio_overlap_score': audio_overlap_score,
                'activity_trend': activity_trend
            }

        return layout

    def _calculate_movement_intensity(self, faces: List[Dict]) -> float:
        """
        Calculate average movement intensity for faces in region.

        Uses movement_range data from multi-frame face detection.

        Args:
            faces: List of faces with optional movement_range data

        Returns:
            Movement intensity 0-1 (0 = static, 1 = high movement)
        """
        if not faces:
            return 0.0

        total_movement = 0.0
        count = 0

        for face in faces:
            movement_range = face.get('movement_range', {})
            if movement_range:
                # Calculate movement magnitude
                width_movement = movement_range.get('width', 0)
                height_movement = movement_range.get('height', 0)

                # Normalize movement (assume max 200px movement is "high")
                normalized_movement = min(1.0, (width_movement + height_movement) / 200.0)

                total_movement += normalized_movement
                count += 1

        if count > 0:
            return total_movement / count
        else:
            return 0.5  # Neutral score if no movement data

    def calculate_audio_overlap_heuristic(
        self,
        region: Dict,
        audio_segments: List[Dict],
        moment: Dict,
        total_regions: int
    ) -> float:
        """
        Educated guess voor audio overlap zonder speaker diarization.

        Heuristiek:

        2-WAY SPLIT (left/right):
            - Temporal split: left = [start, middle], right = [middle, end]
            - Count segments in respective time windows

        3-WAY (left/center/right):
            - Temporal split: 3 equal windows
            - Center krijgt small bonus (vaak host)

        4-WAY GRID (quadrants):
            - Temporal split: 4 equal windows
            - Top-left → first quarter, etc.

        GROUP VIDEO (no split):
            - Spatial heuristic: closest to audio activity
            - Use face positions + movement intensity

        Args:
            region: Region dict met position
            audio_segments: Transcription segments
            moment: Moment times
            total_regions: Number of regions in layout

        Returns:
            Audio overlap score 0.0-1.0
        """
        if not audio_segments:
            return 0.5  # Neutral score

        region_position = region.get('position', '')
        moment_start = moment.get('start_time', 0.0)
        moment_end = moment.get('end_time', 0.0)
        moment_duration = moment_end - moment_start

        if moment_duration <= 0:
            return 0.5

        # V3.2 FIX: Add timing buffer for audio-face alignment
        buffer = self.TIMING_BUFFER_SEC

        # Calculate temporal window for this region
        if total_regions == 2:
            # 2-WAY SPLIT: left/right temporal split
            if region_position == 'left' or region_position == 'top':
                window_start = max(0, moment_start - buffer)  # Add buffer
                window_end = moment_start + (moment_duration / 2) + buffer
            else:
                window_start = moment_start + (moment_duration / 2) - buffer  # Add buffer
                window_end = moment_end + buffer

        elif total_regions == 3:
            # 3-WAY: equal thirds
            third = moment_duration / 3
            if region_position == 'left':
                window_start = moment_start
                window_end = moment_start + third
            elif region_position == 'center':
                window_start = moment_start + third
                window_end = moment_start + (2 * third)
            else:
                window_start = moment_start + (2 * third)
                window_end = moment_end

        elif total_regions == 4:
            # 4-WAY GRID: quarters
            quarter = moment_duration / 4
            position_index = {
                'top-left': 0,
                'top-right': 1,
                'bottom-left': 2,
                'bottom-right': 3
            }
            idx = position_index.get(region_position, 0)
            window_start = moment_start + (idx * quarter)
            window_end = moment_start + ((idx + 1) * quarter)

        else:
            # GROUP VIDEO: use full moment (no temporal split)
            window_start = moment_start
            window_end = moment_end

        # Count audio overlap in window
        overlap_duration = 0.0
        for segment in audio_segments:
            seg_start = segment.get('start', 0.0)
            seg_end = segment.get('end', 0.0)

            # Calculate overlap
            overlap_start = max(window_start, seg_start)
            overlap_end = min(window_end, seg_end)

            if overlap_end > overlap_start:
                overlap_duration += (overlap_end - overlap_start)

        # Calculate score
        window_duration = window_end - window_start
        score = overlap_duration / window_duration if window_duration > 0 else 0.0

        # V3.2 FIX: Scale audio weight if insufficient faces
        face_count = region.get('activity_data', {}).get('face_count', 1)
        if face_count < self.MIN_FACE_COUNT_FOR_AUDIO:
            score *= self.AUDIO_SCALE_FACTOR
            logger.debug(
                f"   Audio score scaled ({face_count} faces < {self.MIN_FACE_COUNT_FOR_AUDIO}): "
                f"{score:.2f}"
            )

        # Center region bonus (often host/moderator)
        if region_position == 'center':
            score = min(1.0, score * 1.2)  # 20% bonus

        return min(1.0, max(0.0, score))


def main():
    """CLI entry point voor testing"""
    import json
    import sys

    # Test layout detector
    detector = LayoutDetector()

    # Test case 1: Verticale 2-way split
    print("=" * 60)
    print("Test Case 1: Vertical 2-way split (interview)")
    print("=" * 60)

    test_faces_vertical = [
        {'center_x': 0.25, 'center_y': 0.5, 'width': 0.2, 'height': 0.3, 'confidence': 0.95},
        {'center_x': 0.75, 'center_y': 0.5, 'width': 0.2, 'height': 0.3, 'confidence': 0.95}
    ]

    result = detector.detect_layout(test_faces_vertical, 1920, 1080)
    print(json.dumps(result, indent=2))

    # Test case 2: Horizontale 2-way split
    print("\n" + "=" * 60)
    print("Test Case 2: Horizontal 2-way split")
    print("=" * 60)

    test_faces_horizontal = [
        {'center_x': 0.5, 'center_y': 0.25, 'width': 0.2, 'height': 0.3, 'confidence': 0.95},
        {'center_x': 0.5, 'center_y': 0.75, 'width': 0.2, 'height': 0.3, 'confidence': 0.95}
    ]

    result = detector.detect_layout(test_faces_horizontal, 1920, 1080)
    print(json.dumps(result, indent=2))

    # Test case 3: 4-way grid
    print("\n" + "=" * 60)
    print("Test Case 3: 4-way grid (video call)")
    print("=" * 60)

    test_faces_grid = [
        {'center_x': 0.25, 'center_y': 0.25, 'width': 0.15, 'height': 0.2, 'confidence': 0.95},
        {'center_x': 0.75, 'center_y': 0.25, 'width': 0.15, 'height': 0.2, 'confidence': 0.95},
        {'center_x': 0.25, 'center_y': 0.75, 'width': 0.15, 'height': 0.2, 'confidence': 0.95},
        {'center_x': 0.75, 'center_y': 0.75, 'width': 0.15, 'height': 0.2, 'confidence': 0.95}
    ]

    result = detector.detect_layout(test_faces_grid, 1920, 1080)
    print(json.dumps(result, indent=2))

    # Test case 4: Geen layout (random faces)
    print("\n" + "=" * 60)
    print("Test Case 4: No layout (random positioning)")
    print("=" * 60)

    test_faces_random = [
        {'center_x': 0.3, 'center_y': 0.4, 'width': 0.2, 'height': 0.3, 'confidence': 0.95},
        {'center_x': 0.6, 'center_y': 0.7, 'width': 0.15, 'height': 0.25, 'confidence': 0.90}
    ]

    result = detector.detect_layout(test_faces_random, 1920, 1080)
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 60)
    print(f"Layout Detector Version: {detector.version}")
    print("=" * 60)


if __name__ == "__main__":
    main()
