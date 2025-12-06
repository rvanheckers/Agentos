#!/usr/bin/env python3
"""
Comprehensive Test Suite for IntelligentCropper V2
=================================================

Tests for AI-powered smart cropping with:
- SecureVideoAgent integration
- FaceDetectorV2 integration
- Temporal smoothing
- Rule of thirds composition
- Multi-aspect ratio optimization
- Backward compatibility
"""

import sys
import os
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agents2.intelligent_cropping.intelligent_cropper import IntelligentCropper


class TestIntelligentCropperV2Security(unittest.TestCase):
    """Test security features inherited from SecureVideoAgent"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_inherits_from_secure_video_agent(self):
        """Verify IntelligentCropper inherits from SecureVideoAgent"""
        from agents2.base.secure_agent import SecureVideoAgent
        self.assertIsInstance(self.cropper, SecureVideoAgent)

    def test_has_security_validators(self):
        """Verify security validators are initialized"""
        self.assertTrue(hasattr(self.cropper, 'validator'))
        self.assertTrue(hasattr(self.cropper, 'path_sanitizer'))
        self.assertTrue(hasattr(self.cropper, 'resource_limiter'))

    def test_process_video_safely_method_exists(self):
        """Verify process_video_safely method is available"""
        self.assertTrue(hasattr(self.cropper, 'process_video_safely'))
        self.assertTrue(callable(self.cropper.process_video_safely))


class TestIntelligentCropperV2Integration(unittest.TestCase):
    """Test FaceDetectorV2 integration"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_face_detector_initialized(self):
        """Verify FaceDetectorV2 is initialized"""
        from agents2.face_detection.face_detector_v2 import FaceDetectorV2
        self.assertIsInstance(self.cropper.face_detector, FaceDetectorV2)

    def test_extract_faces_from_persons(self):
        """Test conversion of person-grouped faces to flat list"""
        persons = [
            {
                "person_id": "person_1",
                "appearances": [
                    {
                        "bbox": {"x": 100, "y": 100, "width": 50, "height": 50},
                        "confidence": 0.9,
                        "timestamp": 1.0,
                        "frame_index": 30
                    },
                    {
                        "bbox": {"x": 105, "y": 102, "width": 52, "height": 52},
                        "confidence": 0.85,
                        "timestamp": 1.5,
                        "frame_index": 45
                    }
                ]
            }
        ]

        faces = self.cropper._extract_faces_from_persons(persons)

        self.assertEqual(len(faces), 2)
        self.assertEqual(faces[0]["bbox"]["x"], 100)
        self.assertEqual(faces[0]["confidence"], 0.9)
        self.assertEqual(faces[1]["bbox"]["x"], 105)
        self.assertEqual(faces[1]["confidence"], 0.85)

    def test_extract_faces_empty_persons(self):
        """Test extraction with empty persons list"""
        faces = self.cropper._extract_faces_from_persons([])
        self.assertEqual(len(faces), 0)


class TestIntelligentCropperV2SmartCrop(unittest.TestCase):
    """Test smart crop algorithm V2"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_calculate_optimal_crop_v2_face_based(self):
        """Test face-based crop calculation"""
        faces = [
            {
                "bbox": {"x": 400, "y": 300, "width": 100, "height": 100},
                "confidence": 0.9
            }
        ]

        crop = self.cropper._calculate_optimal_crop_v2(
            orig_width=1920,
            orig_height=1080,
            target_ratio=9/16,  # Vertical video
            faces=faces,
            padding=0.1,
            priority="faces",
            video_path="/dummy/path.mp4"  # Won't be accessed in unit test
        )

        # Verify crop dimensions match aspect ratio
        expected_height = 1080
        expected_width = int(1080 * (9/16))
        self.assertEqual(crop["width"], expected_width)
        self.assertEqual(crop["height"], expected_height)

        # Verify crop is within bounds
        self.assertGreaterEqual(crop["x"], 0)
        self.assertGreaterEqual(crop["y"], 0)
        self.assertLessEqual(crop["x"] + crop["width"], 1920)
        self.assertLessEqual(crop["y"] + crop["height"], 1080)

    def test_calculate_optimal_crop_v2_center_fallback(self):
        """Test fallback to center crop when no faces"""
        crop = self.cropper._calculate_optimal_crop_v2(
            orig_width=1920,
            orig_height=1080,
            target_ratio=16/9,  # Horizontal video
            faces=[],
            padding=0.1,
            priority="faces",
            video_path="/dummy/path.mp4"
        )

        # Should be centered
        expected_x = (1920 - 1920) // 2
        expected_y = (1080 - 1080) // 2
        self.assertEqual(crop["x"], expected_x)
        self.assertEqual(crop["y"], expected_y)

    def test_face_based_crop_v2_weighted_centroid(self):
        """Test face-based crop with multiple faces (weighted by confidence)"""
        faces = [
            {
                "bbox": {"x": 200, "y": 200, "width": 100, "height": 100},
                "confidence": 0.9  # High confidence
            },
            {
                "bbox": {"x": 800, "y": 400, "width": 100, "height": 100},
                "confidence": 0.3  # Low confidence
            }
        ]

        x, y = self.cropper._calculate_face_based_crop_v2(
            orig_width=1920,
            orig_height=1080,
            crop_width=607,  # 9:16 crop
            crop_height=1080,
            faces=faces,
            padding=0.1
        )

        # Crop should be biased towards high-confidence face (200, 200)
        # rather than being exactly centered between both faces
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)


class TestIntelligentCropperV2RuleOfThirds(unittest.TestCase):
    """Test rule of thirds compositional scoring"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_apply_rule_of_thirds_bias(self):
        """Test rule of thirds bias calculation"""
        # Position at 500px in 1920px width
        position = 500
        dimension = 1920
        crop_dimension = 607

        biased_pos = self.cropper._apply_rule_of_thirds_bias(
            position, dimension, crop_dimension
        )

        # Should snap to nearest third line
        third_1 = 1920 / 3  # 640
        third_2 = 2 * 1920 / 3  # 1280

        # 500 is closer to 640 than 1280
        self.assertEqual(biased_pos, third_1)

    def test_rule_of_thirds_bias_second_third(self):
        """Test bias towards second third line"""
        position = 1000  # Closer to 1280
        dimension = 1920
        crop_dimension = 607

        biased_pos = self.cropper._apply_rule_of_thirds_bias(
            position, dimension, crop_dimension
        )

        third_2 = 2 * 1920 / 3
        self.assertEqual(biased_pos, third_2)


class TestIntelligentCropperV2TemporalSmoothing(unittest.TestCase):
    """Test temporal smoothing for stable crops"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_temporal_smoothing_first_frame(self):
        """Test temporal smoothing with no history (first frame)"""
        crop_coords = {"x": 100, "y": 100, "width": 607, "height": 1080}

        smoothed = self.cropper._apply_temporal_smoothing(crop_coords)

        # First frame should return original coordinates
        self.assertEqual(smoothed["x"], 100)
        self.assertEqual(smoothed["y"], 100)

    def test_temporal_smoothing_second_frame(self):
        """Test temporal smoothing with history"""
        # First frame
        crop1 = {"x": 100, "y": 100, "width": 607, "height": 1080}
        self.cropper._apply_temporal_smoothing(crop1)

        # Second frame with different position
        crop2 = {"x": 200, "y": 150, "width": 607, "height": 1080}
        smoothed = self.cropper._apply_temporal_smoothing(crop2)

        # Should be smoothed (between 100 and 200)
        # With alpha=0.4: smoothed_x = 0.4 * 200 + 0.6 * 100 = 80 + 60 = 140
        self.assertGreater(smoothed["x"], 100)
        self.assertLess(smoothed["x"], 200)
        self.assertEqual(smoothed["x"], 140)

    def test_temporal_smoothing_preserves_dimensions(self):
        """Test that smoothing doesn't change crop dimensions"""
        crop1 = {"x": 100, "y": 100, "width": 607, "height": 1080}
        self.cropper._apply_temporal_smoothing(crop1)

        crop2 = {"x": 200, "y": 150, "width": 607, "height": 1080}
        smoothed = self.cropper._apply_temporal_smoothing(crop2)

        # Dimensions should remain unchanged
        self.assertEqual(smoothed["width"], 607)
        self.assertEqual(smoothed["height"], 1080)


class TestIntelligentCropperV2AspectRatios(unittest.TestCase):
    """Test multi-aspect ratio support"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_aspect_ratio_9_16_vertical(self):
        """Test 9:16 vertical aspect ratio (social media portrait)"""
        ratio = self.cropper._parse_aspect_ratio("9:16")
        self.assertEqual(ratio, 9/16)

    def test_aspect_ratio_16_9_horizontal(self):
        """Test 16:9 horizontal aspect ratio (widescreen)"""
        ratio = self.cropper._parse_aspect_ratio("16:9")
        self.assertEqual(ratio, 16/9)

    def test_aspect_ratio_1_1_square(self):
        """Test 1:1 square aspect ratio"""
        ratio = self.cropper._parse_aspect_ratio("1:1")
        self.assertEqual(ratio, 1.0)

    def test_aspect_ratio_invalid(self):
        """Test invalid aspect ratio handling"""
        ratio = self.cropper._parse_aspect_ratio("invalid")
        self.assertIsNone(ratio)


class TestIntelligentCropperV2BackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with V1 API"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_calculate_crop_method_exists(self):
        """Verify legacy calculate_crop method still exists"""
        self.assertTrue(hasattr(self.cropper, 'calculate_crop'))
        self.assertTrue(callable(self.cropper.calculate_crop))

    def test_legacy_face_based_crop_exists(self):
        """Verify legacy face-based crop method exists"""
        self.assertTrue(hasattr(self.cropper, '_calculate_face_based_crop'))
        self.assertTrue(callable(self.cropper._calculate_face_based_crop))

    def test_legacy_optimal_crop_exists(self):
        """Verify legacy optimal crop method exists"""
        self.assertTrue(hasattr(self.cropper, '_calculate_optimal_crop'))
        self.assertTrue(callable(self.cropper._calculate_optimal_crop))

    @patch('agents2.intelligent_cropping.intelligent_cropper.IntelligentCropper.process_video_safely')
    def test_calculate_crop_delegates_to_process_video_safely(self, mock_process):
        """Test that calculate_crop delegates to process_video_safely"""
        mock_process.return_value = {"success": True, "crop_coordinates": {}}

        input_data = {"video_path": "/test/video.mp4"}
        result = self.cropper.calculate_crop(input_data)

        # Verify delegation occurred
        mock_process.assert_called_once_with(input_data)


class TestIntelligentCropperV2Statistics(unittest.TestCase):
    """Test statistics tracking"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_statistics_initialized(self):
        """Verify statistics are initialized"""
        self.assertIn("face_based_crops", self.cropper.stats)
        self.assertIn("motion_based_crops", self.cropper.stats)
        self.assertIn("center_fallback_crops", self.cropper.stats)
        self.assertIn("total_crops", self.cropper.stats)

        # All should start at 0
        self.assertEqual(self.cropper.stats["face_based_crops"], 0)
        self.assertEqual(self.cropper.stats["motion_based_crops"], 0)
        self.assertEqual(self.cropper.stats["center_fallback_crops"], 0)
        self.assertEqual(self.cropper.stats["total_crops"], 0)


class TestIntelligentCropperV2Version(unittest.TestCase):
    """Test version upgrade"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_version_is_v2_1(self):
        """Verify version is upgraded to 2.1.0-per-moment-faces"""
        self.assertEqual(self.cropper.version, "2.1.0-per-moment-faces")


class TestIntelligentCropperV2PerMomentCropping(unittest.TestCase):
    """Test per-moment face filtering (V2.1 - CRITICAL FIX)"""

    def setUp(self):
        self.cropper = IntelligentCropper()

    def test_per_moment_faces_statistics_initialized(self):
        """Verify per_moment_crops statistic is initialized"""
        self.assertIn("per_moment_crops", self.cropper.stats)
        self.assertEqual(self.cropper.stats["per_moment_crops"], 0)

    def test_per_moment_cropping_mode(self):
        """Test per-moment cropping with relevant_faces attached to moments - unit test level"""
        # Test at unit level (bypassing SecureVideoAgent validation which needs real paths)

        # Mock moments with relevant_faces (simulating tasks/video_processing.py filtering)
        moments = [
            {
                "start_time": 0.0,
                "end_time": 5.0,
                "relevant_faces": [
                    {"bbox": {"x": 200, "y": 200, "width": 100, "height": 100}, "confidence": 0.9, "timestamp": 2.0}
                ]
            },
            {
                "start_time": 10.0,
                "end_time": 15.0,
                "relevant_faces": [
                    {"bbox": {"x": 800, "y": 400, "width": 100, "height": 100}, "confidence": 0.85, "timestamp": 12.0}
                ]
            }
        ]

        input_data = {
            "use_per_moment_faces": True,
            "moments": moments,
            "target_aspect_ratio": "9:16",
            "padding": 0.1,
            "priority": "faces",
            "use_ai_detection": False
        }

        metadata = {
            "width": 1920,
            "height": 1080,
            "duration": 30.0
        }

        # Test _process_validated_video directly (unit test level)
        result = self.cropper._process_validated_video(
            video_path="/dummy/video.mp4",
            output_path=None,
            metadata=metadata,
            input_data=input_data
        )

        # Verify per-moment mode was used
        self.assertTrue(result["success"], f"Failed: {result.get('error')}")
        self.assertEqual(result["crop_mode"], "per_moment")
        self.assertIn("crops_per_moment", result)
        self.assertEqual(len(result["crops_per_moment"]), 2)

        # Verify each moment has its own crop
        crop1 = result["crops_per_moment"][0]
        crop2 = result["crops_per_moment"][1]

        self.assertEqual(crop1["moment_start"], 0.0)
        self.assertEqual(crop1["moment_end"], 5.0)
        self.assertEqual(crop1["faces_used"], 1)

        self.assertEqual(crop2["moment_start"], 10.0)
        self.assertEqual(crop2["moment_end"], 15.0)
        self.assertEqual(crop2["faces_used"], 1)

        # Verify statistics updated
        self.assertEqual(self.cropper.stats["per_moment_crops"], 2)

    def test_legacy_mode_when_per_moment_disabled(self):
        """Test that legacy single-crop mode is used when per-moment is disabled - unit test level"""

        input_data = {
            "faces": [{"bbox": {"x": 400, "y": 300, "width": 100, "height": 100}, "confidence": 0.9}],
            "use_per_moment_faces": False,  # Disabled
            "use_ai_detection": False,
            "target_aspect_ratio": "9:16",
            "priority": "faces",
            "padding": 0.1
        }

        metadata = {
            "width": 1920,
            "height": 1080,
            "duration": 30.0
        }

        # Test _process_validated_video directly (unit test level)
        result = self.cropper._process_validated_video(
            video_path="/dummy/video.mp4",
            output_path=None,
            metadata=metadata,
            input_data=input_data
        )

        # Verify legacy mode was used
        self.assertTrue(result["success"], f"Failed: {result.get('error')}")
        self.assertEqual(result["crop_mode"], "single")
        self.assertIn("crop_coordinates", result)
        self.assertNotIn("crops_per_moment", result)

    def test_per_moment_with_no_faces(self):
        """Test per-moment cropping with moments that have no relevant faces (fallback) - unit test level"""

        moments = [
            {
                "start_time": 0.0,
                "end_time": 5.0,
                "relevant_faces": []  # No faces detected in this moment
            }
        ]

        input_data = {
            "moments": moments,
            "use_per_moment_faces": True,
            "use_ai_detection": False,
            "target_aspect_ratio": "9:16",
            "priority": "faces",
            "padding": 0.1
        }

        metadata = {
            "width": 1920,
            "height": 1080,
            "duration": 30.0
        }

        # Test _process_validated_video directly (unit test level)
        result = self.cropper._process_validated_video(
            video_path="/dummy/video.mp4",
            output_path=None,
            metadata=metadata,
            input_data=input_data
        )

        # Should still succeed with center crop fallback
        self.assertTrue(result["success"], f"Failed: {result.get('error')}")
        self.assertEqual(result["crop_mode"], "per_moment")
        self.assertEqual(len(result["crops_per_moment"]), 1)
        self.assertEqual(result["crops_per_moment"][0]["faces_used"], 0)


def run_tests():
    """Run all tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2Security))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2Integration))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2SmartCrop))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2RuleOfThirds))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2TemporalSmoothing))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2AspectRatios))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2BackwardCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2Statistics))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2Version))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentCropperV2PerMomentCropping))  # NEW: V2.1 per-moment tests

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
