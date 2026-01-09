import json
import logging
import os
from typing import List, Dict, Any

from openai import OpenAI
from app.core.config import settings
from app.services.vector_service import VectorService

# Configure module-level logger
logger = logging.getLogger(__name__)

class TimelineGenerator:
    """
    Generates a video timeline by matching A-roll audio segments with B-roll visual clips
    based on semantic relevance and pacing constraints.
    """

    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        self.model = "llama-3.3-70b-versatile"
        self.vector_service = VectorService()

    def generate_timeline(self, transcript: List[Dict[str, Any]], broll_catalog: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates the editing timeline using an LLM.

        Args:
            transcript: List of A-roll segments with 'start', 'end', 'text'.
            broll_catalog: Dictionary of B-roll clips and their metadata.

        Returns:
            JSON object containing the 'timeline' list.
        """
        logger.info("Generating timeline from transcript and B-roll catalog.")

        # Index the catalog first (Idempotent)
        self.vector_service.index_catalog(broll_catalog)

        # Pre-filter candidates for each segment
        filtered_catalog_map = {} # segment_index -> list of candidates
        
        # We need to map segments to their filtered options to show the LLM
        transcript_with_options = []
        
        for idx, segment in enumerate(transcript):
            text = segment.get("text", "")
            candidates = self.vector_service.get_best_matches(text)
            
            seg_info = segment.copy()
            if candidates:
                # Limit to top 3 for brevity in prompt if many
                # But VectorService usually returns TOP_K (5). 
                # Let's pass all valid candidates.
                seg_info["available_broll"] = candidates
            else:
                seg_info["available_broll"] = [] 
            
            transcript_with_options.append(seg_info)

        system_prompt = self._construct_system_prompt()
        
        # We no longer send the FULL broll_catalog to the LLM. 
        # We send the transcript where each segment HAS the allowed b-roll options.
        user_content = json.dumps({
            "A-Roll Transcript with Options": transcript_with_options,
        }, indent=2)

        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the input data:\n{user_content}"}
                ],
                model=self.model,
                temperature=0.2,
            ) 
            
            raw_content = response.choices[0].message.content.strip()
            parsed_timeline = self._parse_json_response(raw_content)
            
            # Post-process and validate the timeline
            return self._validate_and_fix_timeline(transcript, parsed_timeline)

        except Exception as e:
            logger.exception(f"Failed to generate timeline: {e}")
            raise

    def _validate_and_fix_timeline(self, transcript: List[Dict[str, Any]], raw_timeline: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforces strict pacing, overlap constraints, and confidence thresholds.
        Any B-roll segment violating these rules is DROPPED.
        """
        validated_events = []
        last_broll_end = -float('inf')
        used_broll_timestamps: Dict[str, List[float]] = {} 

        # Lookup for A-roll segments
        # To handle potential floating point mismatches, we might want a tolerance, 
        # but for now we'll assume strict matching or index alignment if the LLM followed instructions.
        
        raw_events = raw_timeline.get("timeline", [])
        
        # Sort raw events by start time 
        raw_events.sort(key=lambda x: x.get("a_roll_start", 0))

        # Check for total duration of A-roll to prevent overlaps beyond end
        if not transcript:
            return {"timeline": []}
            
        # Helper to find relevant A-roll segment for a given start time
        def find_segment(start_time):
            for seg in transcript:
                if abs(seg["start"] - start_time) < 0.1: # 100ms tolerance
                    return seg
            return None

        total_video_end = transcript[-1]["end"]

        for event in raw_events:
            # Confidence Threshold
            if event.get("confidence", 0) < settings.MIN_LLM_CONFIDENCE:
                logger.info(f"Dropping event due to low confidence: {event}")
                continue

            a_roll_start = event.get("a_roll_start")
            a_roll_seg = find_segment(a_roll_start)
            
            if not a_roll_seg:
                logger.warning(f"Dropping event: Start time {a_roll_start} does not match any A-roll segment.")
                continue

            # Strict Duration Enforcement
            # The B-roll must exactly match the A-roll segment duration
            actual_duration = a_roll_seg["end"] - a_roll_seg["start"]
            event["duration_sec"] = actual_duration 
            
            # Overlap Protection
            # Ensure the clip doesn't go beyond total video length
            if a_roll_start + actual_duration > total_video_end + 0.1:
                logger.warning(f"Dropping event: Segment exceeds total video duration.")
                continue

            # Minimum Cut Duration
            if actual_duration < settings.MIN_BROLL_DURATION:
                logger.info(f"Dropping event: Duration {actual_duration:.2f}s < {settings.MIN_BROLL_DURATION}s")
                continue

            # Cool-down Check
            # Time since the last B-roll ended must be >= COOL_DOWN
            # 'last_broll_end' tracks the end of the previous accepted B-roll
            time_since_last = a_roll_start - last_broll_end
            if time_since_last < settings.BROLL_COOL_DOWN_SECONDS:
                logger.info(f"Dropping event: Cool-down violation. gap={time_since_last:.2f}s < {settings.BROLL_COOL_DOWN_SECONDS}s")
                continue

            # Visual Diversity Check
            b_roll_id = event.get("b_roll_id")
            if b_roll_id:
                # Check if this ID was used recently
                past_usages = used_broll_timestamps.get(b_roll_id, [])
                if any(abs(a_roll_start - t) < settings.BROLL_DIVERSITY_WINDOW_SECONDS for t in past_usages):
                    logger.info(f"Dropping event: Diversity violation for {b_roll_id}")
                    continue
            
            # If all checks pass, accept the event
            validated_events.append(event)
            last_broll_end = a_roll_start + actual_duration
            
            if b_roll_id:
                if b_roll_id not in used_broll_timestamps:
                    used_broll_timestamps[b_roll_id] = []
                used_broll_timestamps[b_roll_id].append(a_roll_start)

        return {"timeline": validated_events}

    def _construct_system_prompt(self) -> str:
        """Constructs the system prompt with dynamic config values."""
        return f"""
                # Role: Senior AI Video Editor & Narrative Director
                You are the primary intelligence for "SemanticSync," an automated video editing system. Your goal is to generate a precise JSON timeline that overlays B-roll footage onto a primary A-roll video based on semantic relevance and professional pacing.

                # Context
                The A-roll is the speaker talking; the B-roll consists of various clips described by their visual activity, category, and intent.

                # Core Directives
                1. **Semantic Resonance**: Prioritize clips where the B-roll's `activity` matches the A-roll's `text` conceptually.
                2. **Strict Candidate Usage**: You are provided with "available_broll" for each transcript segment. You MUST ONLY use clips from this list for that specific segment. If the list is empty, DO NOT place any B-roll there.
                3. **Intent Matching**: Use "Product Demo" or "Showcase" intents for descriptive sentences, and "Establishing" or "Atmospheric" intents for general transitions.
                4. **Pacing Constraints**:
                    - **Duration Logic**: `duration_sec` MUST equal `a_roll_end - a_roll_start`.
                    - **Minimum Cut**: Never insert a clip shorter than {settings.MIN_BROLL_DURATION} seconds. If a segment is shorter, skip it or merge it.
                    - **Visual Diversity**: Do not use the same B-roll clip twice within {settings.BROLL_DIVERSITY_WINDOW_SECONDS} seconds.
                    - **Cool-down**: Leave at least {settings.BROLL_COOL_DOWN_SECONDS} seconds of "breathing room" (A-roll only) between B-roll insertions to avoid over-stimulating the viewer.

                # Output Schema
                Return ONLY a valid JSON object. No conversational text.
                            {{
            "timeline": [
                {{
                "a_roll_start": float,
                "duration_sec": float,
                "b_roll_id": "string",
                "b_roll_start_offset": 0.0,
                "confidence": float (0.0 to 1.0),
                "reason": "Explain why this visual category/activity specifically reinforces this script line."
                }}
            ]
            }}
            """

    def _parse_json_response(self, raw_content: str) -> Dict[str, Any]:
        """Cleans and parses the LLM response into a dictionary."""
        clean_content = raw_content.strip()
        
        # Strip markdown code fences if present
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        elif clean_content.startswith("```"):
            clean_content = clean_content[3:]
        
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
            
        clean_content = clean_content.strip()

        try:
            return json.loads(clean_content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {raw_content[:200]}...")
            raise ValueError("Invalid JSON response from model")
