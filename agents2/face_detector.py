#!/usr/bin/env python3
"""
Face Detector Agent - PLACEHOLDER VERSION
Voor WSL/no-GPU environments
"""

import json
import sys
import os
import time
import random

def main():
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python face_detector.py '<json_input>'"
        }))
        sys.exit(1)
    
    try:
        input_data = json.loads(sys.argv[1])
        video_path = input_data.get('video_path')
        
        if not video_path:
            raise ValueError("Missing video_path in input")
        
        # Placeholder face detection - genereer fake data
        faces = []
        num_faces = random.randint(1, 3)
        
        for i in range(num_faces):
            faces.append({
                "person_id": f"person_{i+1}",
                "confidence": round(random.uniform(0.85, 0.99), 2),
                "appearances": [
                    {
                        "timestamp": t,
                        "bbox": {
                            "x": random.randint(100, 300),
                            "y": random.randint(100, 300),
                            "width": random.randint(150, 250),
                            "height": random.randint(150, 250)
                        }
                    }
                    for t in range(10, 120, 30)
                ],
                "total_screen_time": random.randint(30, 90)
            })
        
        result = {
            "success": True,
            "faces": faces,
            "total_faces_detected": len(faces),
            "video_path": video_path,
            "processing_note": "Placeholder face detection for WSL environment"
        }
        
        print(json.dumps(result, indent=2))
        sys.exit(0)
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()