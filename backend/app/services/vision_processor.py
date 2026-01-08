import cv2
import base64
import time
import os
from typing import List, Dict, Optional
from openai import OpenAI, RateLimitError
from app.core.config import settings

class VisionProcessor:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "meta-llama/llama-4-maverick-17b-128e-instruct"

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

        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        frame_interval = settings.VISION_FRAME_INTERVAL
        
        # Calculate frame step based on FPS and interval
        # If FPS is 30 and interval is 5s, we need every 150th frame
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
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"Error processing frame at {timestamp}s: {e}")
                        import traceback
                        traceback.print_exc()
                        # Continue to next frame even if one fails
                
                current_frame += 1
                
        finally:
            video.release()
            
        return descriptions

    def _describe_frame(self, frame) -> Dict:
        """Sends a frame to the Groq Vision API for description."""
        base64_image = self._encode_image(frame)
        prompt = '''
        # System Instruction
            You are a Professional Media Analyst and Video Editor. Your task is to catalog video B-roll footage by describing the primary activity and semantic context of each frame.

            # Task
            Analyze the provided image frame and generate a concise, high-level description of the specific activity occurring. 

            # Constraints
            1. Focus strictly on the "Interaction" or "Activity" (e.g., 'trading on a terminal', 'applying moisturizer', 'flipping a burger').
            2. Avoid generic descriptors like "a person is there" or describing static backgrounds/colors unless they define the activity (e.g., 'stock market tickers on screen').
            3. Use the Present Tense exclusively (e.g., "Person is washing face" NOT "Person washed face").
            4. Be specific to the domain (e.g., use "candlestick chart" for finance, "skincare routine" for cosmetics).

            # Few-Shot Examples for Guidance:
            - Fast Food: "Chef is assembling a burger on a prep table."
            - Cosmetics: "Close-up of hands applying serum to skin."
            - Hygiene: "Person is scrubbing hands with soap under running water."
            - Finance: "Digital display showing real-time green and red stock market candles."
            - Retail: "Customer is tapping a credit card on a payment terminal."

            # Output Format
            Return ONLY a JSON object:
            {
            "activity": "Detailed activity description",
            "category": "Detected domain (e.g., Food, Finance, etc.)",
            "intent": "The likely purpose of this shot (e.g., 'Product Demo', 'Atmospheric Background')"
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

            import json
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
