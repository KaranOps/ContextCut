import cv2
import base64
import time
import os
import json
from typing import List, Dict, Optional
from openai import OpenAI, RateLimitError
from app.core.config import settings

class VisionProcessor:
    def __init__(self):
        self.provider = settings.VISION_PROVIDER
        self.model = settings.VISION_MODEL
        self.client = None
        
        if self.provider == "openai" and settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "groq" and settings.GROQ_API_KEY:
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )
        
        # Log initialization
        print(f"VisionProcessor initialized with Provider: {self.provider}, Model: {self.model}")

    def _encode_image(self, frame) -> str:
        """Encodes an OpenCV frame to a Base64 string."""
        _, buffer = cv2.imencode(".jpg", frame)
        return base64.b64encode(buffer).decode("utf-8")

    def process_video(self, video_path: str) -> List[Dict]:
        """
        Extracts frames from the video at a configured interval and describes them using the Vision API.
        
        Args:
            video_path: Absolute path to the video file.
            
        Returns:
            A list of dictionaries containing timestamp and description.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        if self.provider == "local":
             # Placeholder for local vision models (e.g., LLaVA) if integrated
             print("Local vision processing specific logic not implemented. Returning empty.")
             return []

        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_interval = settings.VISION_FRAME_INTERVAL
        
        # Calculate frame step based on FPS and interval
        if fps <= 0: fps = 30 # Fallback
        frame_step = int(fps * frame_interval)
        
        descriptions = []
        current_frame = 0
        
        try:
            while video.isOpened():
                ret, frame = video.read()
                if not ret:
                    break
                
                # Only process frames at the interval
                if current_frame % frame_step == 0:
                    timestamp = current_frame / fps
                    
                    try:
                        description = self._describe_frame(frame)
                        descriptions.append({
                            "timestamp": round(timestamp, 2),
                            "description": description
                        })
                        
                        # Rate limiting - sleep for RPM limits
                        # Optimize: Maybe make this configurable or adaptive
                        time.sleep(1) 
                        
                    except Exception as e:
                        print(f"Error processing frame at {timestamp}s: {e}")
                        # Continue to next frame even if one fails
                
                current_frame += 1
                
        finally:
            video.release()
            
        return descriptions

    def _describe_frame(self, frame) -> Dict:
        """Sends a frame to the Vision API for description."""
        base64_image = self._encode_image(frame)
        prompt = '''
        # System Instruction
        You are a Cinematic Data Scientist and Video Indexing Expert. Your task is to extract frame-accurate semantic metadata for an automated non-linear editing (NLE) system called "ContextCut."

        # Task
        Identify the technical and narrative attributes of the provided frame. Your analysis must be optimized for a vector-based retrieval system (RAG).

        # Analysis Framework
        1. **Dynamic Activity**: Use "Subject is [Verb]-ing [Object]" format. Describe the most prominent motion (e.g., 'Liquid is shimmering while being poured').
        2. **Technical Shot Attributes**:
            - **Framing**: Wide, Medium, Close-up, Macro, POV.
            - **Camera Movement**: Static, Pan, Tilt, Zoom, Handheld, Drone.
        3. **Environmental Context**: Define the lighting and vibe (e.g., 'Studio lit, minimalist', 'Natural sunlight, outdoor market').
        4. **Keyword Expansion**: Provide 5 synonyms or related concepts for better semantic search (e.g., if activity is 'frying', keywords could be 'sizzle, kitchen, chef, heat, cooking').

        # Output Schema (Return ONLY JSON)
        {
        "activity": "Detailed present-progressive action sentence.",
        "category": "High-level domain (e.g., Healthcare, Gastronomy, IT).",
        "intent": "Narrative utility (e.g., Transition, Detail, Hero, Establishing).",
        "technical": {
            "shot_type": "string",
            "camera_movement": "string",
            "lighting": "string"
        },
        "search_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
        }

        # Example Output
        {
        "activity": "Surgeon is precisely suturing an incision under bright theatre lights.",
        "category": "Medical",
        "intent": "Process Detail",
        "technical": {
            "shot_type": "Macro",
            "camera_movement": "Static",
            "lighting": "Clinical, High-brightness"
        },
        "search_tags": ["surgery", "hospital", "precision", "healthcare", "operation"]
        }
        '''

        raw_content = ""
        try:
            raw_content = self._make_api_call(base64_image, prompt)
            
            # Clean up the response to extract JSON
            clean_content = raw_content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()

            return json.loads(clean_content)
            
        except RateLimitError:
            print("Rate limit hit. Waiting 10 seconds before retrying...")
            time.sleep(10)
            return self._describe_frame(frame) # Recursive retry
        except Exception as e:
            print(f"Error parsing vision response: {e}")
            print(f"Raw content: {raw_content}")
            return {
                "activity": raw_content,
                "category": "Unknown",
                "intent": "Error parsing response"
            }

    def _make_api_call(self, base64_image: str, prompt: str) -> str:
        if not self.client:
             raise RuntimeError("Vision API Client not initialized.")

        # Note: API format is compatible for OpenAI and Groq (Llama vision)
        response = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model=self.model,
        )
        return response.choices[0].message.content.strip()
