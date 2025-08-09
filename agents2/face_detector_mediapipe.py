#!/usr/bin/env python3
"""
Simple Face Detector Agent - Based on clipper_intelligent.py
============================================================

Simplified face detection using MediaPipe from the working backup.
Falls back gracefully when MediaPipe is not available.
"""

import json
import sys
import os
import time

# MediaPipe imports with fallback
try:
    import cv2
    import mediapipe as mp
    FACE_DETECTION_AVAILABLE = True
except ImportError:
    FACE_DETECTION_AVAILABLE = False

class SimpleFaceDetector:
    """
    Simple face detector using MediaPipe (based on working clipper_intelligent.py)
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.face_detection = None
        self.face_detection_available = False
        
        if FACE_DETECTION_AVAILABLE:
            try:
                # Initialize MediaPipe Face Detection (same as clipper_intelligent)
                self.mp_face_detection = mp.solutions.face_detection
                self.face_detection = self.mp_face_detection.FaceDetection(
                    model_selection=1,  # Full-range model
                    min_detection_confidence=0.5
                )
                self.face_detection_available = True
            except Exception:
                self.face_detection_available = False
    
    def detect_faces(self, input_data):
        """
        Detect faces in image/video.
        
        Args:
            input_data: {
                "image_path": str,          # path to image file
                "output_path": str,         # output path for result
                "draw_boxes": bool,         # draw bounding boxes (default: True)
                "confidence": float         # detection confidence (default: 0.5)
            }
            
        Returns:
            {
                "success": bool,
                "faces_detected": int,
                "faces": List[{
                    "x": int, "y": int, "width": int, "height": int,
                    "confidence": float,
                    "center_x": float, "center_y": float
                }],
                "output_image": str,        # path to output image with boxes
                "processing_time": float,
                "method_used": str,
                "agent_version": str
            }
        """
        
        start_time = time.time()
        
        try:
            # Validate input
            if not input_data.get("image_path"):
                return self._error("image_path is required")
                
            image_path = input_data["image_path"]
            if not os.path.exists(image_path):
                return self._error(f"Image file not found: {image_path}")
            
            output_path = input_data.get("output_path", "faces_detected.jpg")
            draw_boxes = input_data.get("draw_boxes", True)
            confidence_threshold = input_data.get("confidence", 0.5)
            
            # Detect faces
            if self.face_detection_available:
                faces = self._detect_with_mediapipe(image_path, confidence_threshold)
                method_used = "mediapipe"
            else:
                # Fallback: return mock data
                faces = self._mock_detection(image_path)
                method_used = "mock"
            
            # Draw boxes if requested
            output_image_path = None
            if draw_boxes and faces:
                output_image_path = self._draw_face_boxes(image_path, faces, output_path)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "faces_detected": len(faces),
                "faces": faces,
                "output_image": output_image_path or output_path,
                "processing_time": processing_time,
                "method_used": method_used,
                "agent_version": self.version
            }
            
        except Exception as e:
            return self._error(f"Face detection failed: {str(e)}")
    
    def _detect_with_mediapipe(self, image_path, confidence_threshold):
        """Detect faces using MediaPipe (same logic as clipper_intelligent)"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return []
            
            frame_h, frame_w = image.shape[:2]
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Detect faces
            results = self.face_detection.process(rgb_image)
            
            if not results.detections:
                return []
            
            faces = []
            for detection in results.detections:
                if detection.score[0] < confidence_threshold:
                    continue
                    
                bbox = detection.location_data.relative_bounding_box
                
                # Convert normalized coordinates to pixel coordinates
                x = int(bbox.xmin * frame_w)
                y = int(bbox.ymin * frame_h)
                w = int(bbox.width * frame_w)
                h = int(bbox.height * frame_h)
                
                # Calculate center
                center_x = (x + w / 2) / frame_w
                center_y = (y + h / 2) / frame_h
                
                faces.append({
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "confidence": float(detection.score[0]),
                    "center_x": center_x,
                    "center_y": center_y
                })
            
            return faces
            
        except Exception as e:
            print(f"MediaPipe detection error: {e}", file=sys.stderr)
            return []
    
    def _mock_detection(self, image_path):
        """Mock face detection for when MediaPipe is not available"""
        return [{
            "x": 100,
            "y": 100,
            "width": 200,
            "height": 200,
            "confidence": 0.95,
            "center_x": 0.5,
            "center_y": 0.4,
            "note": "Mock face detection - MediaPipe not available"
        }]
    
    def _draw_face_boxes(self, image_path, faces, output_path):
        """Draw bounding boxes around detected faces"""
        try:
            if not FACE_DETECTION_AVAILABLE:
                return output_path
                
            image = cv2.imread(image_path)
            if image is None:
                return output_path
            
            # Draw boxes
            for face in faces:
                x, y, w, h = face["x"], face["y"], face["width"], face["height"]
                confidence = face["confidence"]
                
                # Draw rectangle
                cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Add confidence text
                text = f"{confidence:.2f}"
                cv2.putText(image, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Save image
            cv2.imwrite(output_path, image)
            return output_path
            
        except Exception as e:
            print(f"Error drawing boxes: {e}", file=sys.stderr)
            return output_path
    
    def _error(self, message):
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "FACE_DETECTION_ERROR",
            "faces_detected": 0,
            "faces": [],
            "output_image": "",
            "processing_time": 0.0,
            "method_used": "error",
            "agent_version": self.version
        }

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python face_detector_simple.py '<json_input>'",
            "error_code": "USAGE_ERROR"
        }))
        sys.exit(1)
    
    try:
        input_data = json.loads(sys.argv[1])
        detector = SimpleFaceDetector()
        result = detector.detect_faces(input_data)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success", False) else 1)
        
    except json.JSONDecodeError:
        print(json.dumps({
            "success": False,
            "error": "Invalid JSON input",
            "error_code": "JSON_ERROR"
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()