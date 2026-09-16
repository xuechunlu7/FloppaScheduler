import sys
import os
import json
from dotenv import load_dotenv

from src.utils.vision_parser import extract_schedule_from_image

def main():
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python test_vision.py <image_path>")
        sys.exit(1)
        
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"Error: File '{image_path}' not found.")
        sys.exit(1)
        
    print(f"Testing vision parser with image: {image_path}")
    print("-" * 50)
    
    result = extract_schedule_from_image(image_path)
    
    print("\n--- Extracted Schedule JSON ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
