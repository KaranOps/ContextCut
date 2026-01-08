import sys
import os
import json
import logging
from typing import List, Dict, Any

# Add the backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

from app.services.timeline_generator import TimelineGenerator
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_validation_logic():
    print("\n--- Testing Validation Logic (Unit Test) ---")
    generator = TimelineGenerator()
    
    # Mock Transcript
    transcript = [
        {"start": 0.0, "end": 5.0, "text": "Segment 1 (5s)"},
        {"start": 5.0, "end": 10.0, "text": "Segment 2 (5s)"},
        {"start": 10.0, "end": 12.0, "text": "Segment 3 (2s)"}, # Too short for cool-down gap check if next one follows immediately?
        {"start": 12.0, "end": 17.0, "text": "Segment 4 (5s)"},
        {"start": 17.0, "end": 25.0, "text": "Segment 5 (8s)"},
    ] # Total end: 25.0
    
    # Mock Raw Timeline from "LLM"
    raw_response = {
        "timeline": [
            # 1. Valid
            {
                "a_roll_start": 0.0,
                "duration_sec": 5.0, 
                "b_roll_id": "clip_a.mp4",
                "confidence": 0.9
            },
            # 2. Violation: Cool-down (Ends at 5.0, next starts at 5.0. Gap=0 < 5.0)
            {
                "a_roll_start": 5.0,
                "duration_sec": 5.0,
                "b_roll_id": "clip_b.mp4",
                "confidence": 0.95
            },
             # 3. Violation: Min Duration (Assuming segment 3 is 2s, but let's say config is 1.5. This IS valid duration, 
             # but check if it violates cool-down from the previous accepted one.)
             # If Segment 2 was dropped, last end is 5.0. Segment 3 starts at 10.0. Gap = 5.0. Equal to 5.0. So this should pass?
            {
                "a_roll_start": 10.0,
                "duration_sec": 2.0,
                "b_roll_id": "clip_c.mp4",
                "confidence": 0.8
            },
            # 4. Violation: Diversity (clip_a used at 0.0, repeated at 12.0. Window is 30s)
            {
                "a_roll_start": 12.0,
                "duration_sec": 5.0,
                "b_roll_id": "clip_a.mp4",
                "confidence": 0.9
            },
            # 5. Violation: Low Confidence
            {
                "a_roll_start": 17.0,
                "duration_sec": 3.0,
                "b_roll_id": "clip_d.mp4",
                "confidence": 0.6
            }
        ]
    }
    
    print(f"Config: Cool-down={settings.BROLL_COOL_DOWN_SECONDS}s, Diversity={settings.BROLL_DIVERSITY_WINDOW_SECONDS}s, MinDuration={settings.MIN_BROLL_DURATION}s")

    result = generator._validate_and_fix_timeline(transcript, raw_response)
    events = result["timeline"]
    
    print(f"\nInput Events: {len(raw_response['timeline'])}")
    print(f"Validated Events: {len(events)}")
    
    for i, ev in enumerate(events):
        print(f"Event {i}: Start={ev['a_roll_start']}, Dur={ev['duration_sec']}, ID={ev.get('b_roll_id')}")

    # Assertions
    assert len(events) >= 1
    assert events[0]['a_roll_start'] == 0.0
    
    assert events[1]['a_roll_start'] == 10.0
    
    
    assert len(events) == 2, f"Expected 2 events, got {len(events)}"
    print("\nUnit Test Passed: logic handled cool-down, diversity, and confidence correctly.")
    

def run_e2e_test():
    print("\n--- Running End-to-End Test (LLM Integration) ---")
    generator = TimelineGenerator()
    
    # Paths to real data
    base_dir = os.path.dirname(__file__)
    transcript_path = os.path.join(base_dir, "../../data/processed/final_transcription_result_gpt-oss-120b.json")
    vision_path = os.path.join(base_dir, "../../data/processed/vision_results.json")
    
    # Load A-roll Transcript
    if not os.path.exists(transcript_path):
        print(f"Error: Transcript file not found at {transcript_path}")
        return

    with open(transcript_path, "r") as f:
        transcript_data = json.load(f)
        # Handle structure: checks if it has 'segments', otherwise assumes it's a list
        if isinstance(transcript_data, dict) and "segments" in transcript_data:
            transcript = transcript_data["segments"]
        elif isinstance(transcript_data, list):
            transcript = transcript_data
        else:
             print("Error: Unknown transcript format.")
             return

    # Load B-roll Catalog
    if not os.path.exists(vision_path):
        print(f"Error: Vision results file not found at {vision_path}")
        return
        
    with open(vision_path, "r") as f:
        broll_catalog = json.load(f)
    
    print(f"Loaded {len(transcript)} transcript segments.")
    print(f"Loaded {len(broll_catalog)} B-roll entries.")

    try:
        timeline = generator.generate_timeline(transcript, broll_catalog)
        print("\n--- Generated Timeline ---")
        print(json.dumps(timeline, indent=2))
        
        # Basic constraints check on result
        events = timeline.get("timeline", [])
        last_end = -100
        used_ids = {}
        
        for ev in events:
            # Check Confidence
            if ev.get("confidence", 0) < settings.MIN_LLM_CONFIDENCE:
                 print("FAILED: Low confidence event found.")
                 return
            
            # Check Cool-down
            start = ev["a_roll_start"]
            if start - last_end < settings.BROLL_COOL_DOWN_SECONDS - 0.1: # tolerance
                if last_end != -100: # ignore first
                     print(f"FAILED: Cool-down violation. Start {start}, Last End {last_end}")
                     
            
            last_end = start + ev["duration_sec"]
            
            # Check Diversity
            bid = ev.get("b_roll_id")
            if bid:
                if bid in used_ids:
                    if start - used_ids[bid] < settings.BROLL_DIVERSITY_WINDOW_SECONDS:
                        print(f"FAILED: Diversity violation for {bid}")
                used_ids[bid] = start
        
        print("\nE2E Test Constraints Checked.")

        # Save Output
        output_dir = os.path.join(base_dir, "../../data/outputs")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "timeline.json")
        
        with open(output_path, "w") as f:
            json.dump(timeline, f, indent=2)
        print(f"\nSaved timeline to: {output_path}")
        
    except Exception as e:
        print(f"Error generating timeline: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # test_validation_logic()
    # Run real LLM call if not in CI/CD (assumed manual usage)
    run_e2e_test() 

