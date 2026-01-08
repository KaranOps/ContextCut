import sys
import os

# Add the backend directory to sys.path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"), encoding="utf-8")

from app.services.vision_processor import VisionProcessor
from app.core.config import settings

def main():
    print("Initializing VisionProcessor...")
    processor = VisionProcessor()
    
    # Try to find the uploads directory
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/uploads"))
    ]
    
    uploads_dir = None
    for path in possible_paths:
        if os.path.exists(path):
            uploads_dir = path
            break
            
    if not uploads_dir:
        print("No 'uploads' directory found.")
        print(f"Checked: {possible_paths}")
        return

    # Find all b-roll videos
    video_files = [f for f in os.listdir(uploads_dir) if f.startswith("broll") and f.endswith(".mp4")]
    
    if not video_files:
        print(f"No 'broll' videos found in {uploads_dir}")
        return

    print(f"Found {len(video_files)} videos to process in {uploads_dir}")
    
    all_results = {}
    
    for video_file in video_files:
        video_path = os.path.join(uploads_dir, video_file)
        print(f"\nProcessing video: {video_file}")
        print(f"Frame Interval: {settings.VISION_FRAME_INTERVAL} seconds")
        
        try:
            descriptions = processor.process_video(video_path)
            all_results[video_file] = descriptions
            
            print(f"Completed {video_file}: {len(descriptions)} descriptions generated.")
            # Print preview of first description
            if descriptions:
                desc = descriptions[0]['description']
                print(f"Type of description: {type(desc)}")
                print(f"Preview: {desc}")
                
        except Exception as e:
            print(f"Error processing {video_file}: {e}")
            all_results[video_file] = {"error": str(e)}

    # Save results to JSON
    import json
    
    # Determine output path (try to invoke 'data/processed' or similar)
    output_dir = os.path.abspath(os.path.join(uploads_dir, "../processed"))
    if not os.path.exists(output_dir):
        # Fallback to local 'processed' if the data struct is different or create it
        try:
            os.makedirs(output_dir, exist_ok=True)
        except:
             output_dir = os.path.join(os.path.dirname(__file__), "processed")
             os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "vision_results.json")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved all results to: {output_path}")
    except Exception as e:
        print(f"\nFailed to save results: {e}")

if __name__ == "__main__":
    main()
