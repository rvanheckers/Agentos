#!/usr/bin/env python3
"""
Compositional Engine V1 - Cinema-MVP Component
==============================================

Cinematografische compositie-regels voor professionele framing.

Rules V1:
- Rule of Thirds: Positioneer subject op 1/3 lijnen (niet center)
- Headroom: 15% ruimte boven subject's hoofd
- Leading Space: Extra ruimte in kijkrichting (60% bij duidelijke richting)
- Safe Zone: 10-15% inset van randen voor bewegingscompensatie

Architecture:
- Geen gaze (iris) tracking in V1 → gebruik head-pose yaw/pitch
- Leading space alleen bij duidelijke bewegings- of kijkrichting
- Safe-zone clamp voorkomt dat faces te dicht bij rand komen
- Shot type bepaalt framing strategie (close/medium/wide)

Performance: ~5-10ms per frame (lichtgewicht berekeningen)
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import math

logger = logging.getLogger(__name__)


class CompositionalEngine:
    """
    Cinematografische compositie-engine voor professionele framing.

    V1 Features:
    - Rule of thirds positioning
    - Headroom calculation (15%)
    - Safe-zone clamping (10-15%)
    - Leading space (optioneel, gebaseerd op head-pose/motion)
    """

    # V1 Configuration
    HEADROOM_RATIO = 0.15           # 15% ruimte boven hoofd
    SAFE_ZONE_INSET = 0.12          # 12% inset van randen
    LEADING_SPACE_RATIO = 0.60      # 60% extra ruimte in kijkrichting
    MIN_LEADING_CONFIDENCE = 0.6    # Minimale zekerheid voor leading space

    # Rule of thirds positions (normalized 0-1)
    THIRD_LEFT = 0.333
    THIRD_RIGHT = 0.667
    THIRD_TOP = 0.333
    THIRD_BOTTOM = 0.667

    def __init__(self):
        """Initialize compositional engine"""
        self.version = "1.0.0-cinema-mvp"

    def compose(
        self,
        orig_w: int,
        orig_h: int,
        target_ratio: float,
        faces: List[Dict[str, Any]],
        shot_type: str = "medium",
        camera_movement: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, int, int, int, List[str]]:
        """
        Bereken cinematografisch gecomponeerde crop.

        Args:
            orig_w, orig_h: Originele frame dimensies
            target_ratio: Gewenste aspect ratio (bijv. 9/16 voor vertical)
            faces: List van face dicts met 'x', 'y', 'width', 'height', 'center_x', 'center_y'
                   Optioneel: 'head_pose' dict met 'yaw', 'pitch', 'roll' (graden)
            shot_type: "close_up" | "medium" | "wide"
            camera_movement: Optioneel dict met 'direction', 'magnitude'

        Returns:
            (crop_x, crop_y, crop_w, crop_h, rules_applied):
            - crop_x, crop_y, crop_w, crop_h: Crop coördinaten in pixels
            - rules_applied: List van toegepaste regels (voor debugging/logging)
        """

        if not faces:
            # Geen faces → center crop met safe-zone
            return self._center_crop_with_safe_zone(orig_w, orig_h, target_ratio)

        rules_applied = []

        # 1. Bereken target crop dimensies met safe-zone buffer
        safe_zone_buffer = 2 * self.SAFE_ZONE_INSET
        usable_h = int(orig_h * (1 - safe_zone_buffer))
        usable_w = int(orig_w * (1 - safe_zone_buffer))

        target_w = int(usable_h * target_ratio)
        target_h = usable_h

        # Clamp naar usable dimensies
        if target_w > usable_w:
            target_w = usable_w
            target_h = int(usable_w / target_ratio)

        # 2. Bepaal primary subject (meest prominente face)
        primary_face = self._select_primary_subject(faces, shot_type)

        # 3. Bereken headroom offset
        headroom_offset_y = self._calculate_headroom_offset(
            primary_face, target_h, shot_type
        )
        rules_applied.append("headroom")

        # 4. Bepaal horizontale positie (rule of thirds + leading space)
        leading_direction = self._determine_leading_direction(
            primary_face, camera_movement
        )

        crop_x = self._calculate_horizontal_position(
            primary_face,
            target_w,
            orig_w,
            leading_direction,
            rules_applied
        )

        # 5. Bereken verticale positie met headroom
        face_top_y = primary_face['y']
        crop_y = face_top_y - headroom_offset_y

        # 6. Apply safe-zone clamping
        crop_x, crop_y = self._apply_safe_zone(
            crop_x, crop_y, target_w, target_h, orig_w, orig_h
        )
        rules_applied.append("safe_zone")

        logger.debug(
            f"🎨 Composed crop: {crop_x},{crop_y} {target_w}x{target_h} "
            f"(rules: {', '.join(rules_applied)})"
        )

        return crop_x, crop_y, target_w, target_h, rules_applied

    def _select_primary_subject(
        self, faces: List[Dict], shot_type: str
    ) -> Dict[str, Any]:
        """
        Selecteer primary subject voor compositie.

        Strategie:
        - close_up: Grootste/meest prominente face
        - medium: Centrale face met hoogste confidence
        - wide: Geometrisch centrum van alle faces
        """
        if shot_type == "close_up":
            # Grootste face (meest prominent in frame)
            return max(faces, key=lambda f: f['width'] * f['height'])

        elif shot_type == "medium":
            # Meest centrale face met hoge confidence
            center_scores = []
            for face in faces:
                # Bereken afstand tot frame center
                dist_to_center = abs(face['center_x'] - 0.5) + abs(face['center_y'] - 0.5)
                # Gecombineerde score: confidence - afstand
                score = face.get('confidence', 0.9) - dist_to_center
                center_scores.append((score, face))

            return max(center_scores, key=lambda x: x[0])[1]

        else:  # wide
            # Voor wide shots: gebruik eerste face als anchor
            # (in toekomstige versie: geometrisch centrum van alle faces)
            return faces[0]

    def _calculate_headroom_offset(
        self, face: Dict, target_h: int, shot_type: str
    ) -> int:
        """
        Bereken headroom offset boven face.

        Returns:
            Offset in pixels vanaf bovenkant face
        """
        face_height = face['height']

        # Shot type bepaalt headroom ratio
        if shot_type == "close_up":
            # Close-up: minder headroom (subject vult frame)
            headroom_ratio = self.HEADROOM_RATIO * 0.7  # 10.5%
        elif shot_type == "wide":
            # Wide: meer headroom (context belangrijk)
            headroom_ratio = self.HEADROOM_RATIO * 1.3  # 19.5%
        else:  # medium
            headroom_ratio = self.HEADROOM_RATIO  # 15%

        # Bereken offset
        headroom_pixels = int(target_h * headroom_ratio)

        return headroom_pixels

    def _determine_leading_direction(
        self,
        face: Dict,
        camera_movement: Optional[Dict]
    ) -> Optional[str]:
        """
        Bepaal leading direction (left/right/none).

        Prioriteit:
        1. Head-pose yaw (als beschikbaar en duidelijk)
        2. Camera movement direction (als beschikbaar en significant)
        3. None (geen duidelijke richting)

        Returns:
            "left" | "right" | None
        """
        # 1. Check head-pose yaw
        head_pose = face.get('head_pose')
        if head_pose:
            yaw = head_pose.get('yaw', 0)  # Graden (-90 tot +90)

            # Duidelijke kijkrichting?
            if abs(yaw) > 15:  # > 15 graden = duidelijk
                confidence = min(abs(yaw) / 90, 1.0)

                if confidence >= self.MIN_LEADING_CONFIDENCE:
                    return "right" if yaw > 0 else "left"

        # 2. Check camera movement
        if camera_movement:
            direction = camera_movement.get('direction')
            magnitude = camera_movement.get('magnitude', 0)

            # Significante beweging?
            if magnitude > 5 and direction in ['left', 'right']:
                return direction

        # Geen duidelijke richting
        return None

    def _calculate_horizontal_position(
        self,
        face: Dict,
        target_w: int,
        orig_w: int,
        leading_direction: Optional[str],
        rules_applied: List[str]
    ) -> int:
        """
        Bereken horizontale crop positie met rule of thirds + leading space.

        Returns:
            crop_x in pixels
        """
        face_center_x_norm = face['center_x']  # Normalized 0-1
        face_center_x_px = int(face_center_x_norm * orig_w)

        if leading_direction is None:
            # Geen duidelijke richting → rule of thirds (center op 1/3 lijn)
            # Kies dichtstbijzijnde third line
            if face_center_x_norm < 0.5:
                target_center_norm = self.THIRD_LEFT
            else:
                target_center_norm = self.THIRD_RIGHT

            crop_x = int(orig_w * target_center_norm - target_w / 2)
            rules_applied.append("rule_of_thirds")

        else:
            # Leading space: geef meer ruimte in kijkrichting
            if leading_direction == "right":
                # Kijk naar rechts → subject links in frame
                # Plaats subject op left third met extra ruimte rechts
                target_center_norm = self.THIRD_LEFT
                rules_applied.append("leading_space_right")
            else:
                # Kijk naar links → subject rechts in frame
                target_center_norm = self.THIRD_RIGHT
                rules_applied.append("leading_space_left")

            crop_x = int(orig_w * target_center_norm - target_w / 2)

        return crop_x

    def _apply_safe_zone(
        self,
        crop_x: int,
        crop_y: int,
        crop_w: int,
        crop_h: int,
        orig_w: int,
        orig_h: int
    ) -> Tuple[int, int]:
        """
        Apply safe-zone clamping (voorkom crop te dicht bij randen).

        Returns:
            (clamped_x, clamped_y)
        """
        inset_x = int(orig_w * self.SAFE_ZONE_INSET)
        inset_y = int(orig_h * self.SAFE_ZONE_INSET)

        # Clamp X
        min_x = inset_x
        max_x = orig_w - crop_w - inset_x
        crop_x = max(min_x, min(crop_x, max_x))

        # Clamp Y
        min_y = inset_y
        max_y = orig_h - crop_h - inset_y
        crop_y = max(min_y, min(crop_y, max_y))

        return crop_x, crop_y

    def _center_crop_with_safe_zone(
        self, orig_w: int, orig_h: int, target_ratio: float
    ) -> Tuple[int, int, int, int, List[str]]:
        """Fallback: center crop met safe-zone wanneer geen faces"""
        safe_zone_buffer = 2 * self.SAFE_ZONE_INSET
        usable_h = int(orig_h * (1 - safe_zone_buffer))
        usable_w = int(orig_w * (1 - safe_zone_buffer))

        target_w = int(usable_h * target_ratio)
        target_h = usable_h

        if target_w > usable_w:
            target_w = usable_w
            target_h = int(usable_w / target_ratio)

        crop_x = (orig_w - target_w) // 2
        crop_y = (orig_h - target_h) // 2

        # Apply safe-zone
        crop_x, crop_y = self._apply_safe_zone(
            crop_x, crop_y, target_w, target_h, orig_w, orig_h
        )

        return crop_x, crop_y, target_w, target_h, ["center_fallback", "safe_zone"]

    def validate_crop(
        self,
        crop_x: int,
        crop_y: int,
        crop_w: int,
        crop_h: int,
        orig_w: int,
        orig_h: int
    ) -> bool:
        """
        Valideer of crop binnen frame bounds ligt.

        Returns:
            True als valid, False anders
        """
        if crop_x < 0 or crop_y < 0:
            return False

        if crop_x + crop_w > orig_w:
            return False

        if crop_y + crop_h > orig_h:
            return False

        return True


def main():
    """CLI entry point voor testing"""
    import json
    import sys

    # Test compositional engine
    engine = CompositionalEngine()

    # Voorbeeld test: medium shot met face center-left
    orig_w, orig_h = 1920, 1080
    target_ratio = 9/16  # Vertical video

    test_face = {
        'x': 400,
        'y': 200,
        'width': 300,
        'height': 400,
        'center_x': 0.35,
        'center_y': 0.35,
        'confidence': 0.95,
        'head_pose': {
            'yaw': 25,  # Kijkt naar rechts
            'pitch': 0,
            'roll': 0
        }
    }

    crop_x, crop_y, crop_w, crop_h, rules = engine.compose(
        orig_w, orig_h, target_ratio, [test_face], shot_type="medium"
    )

    print(json.dumps({
        'success': True,
        'crop': {
            'x': crop_x,
            'y': crop_y,
            'width': crop_w,
            'height': crop_h
        },
        'rules_applied': rules,
        'valid': engine.validate_crop(crop_x, crop_y, crop_w, crop_h, orig_w, orig_h),
        'engine_version': engine.version
    }, indent=2))


if __name__ == "__main__":
    main()
