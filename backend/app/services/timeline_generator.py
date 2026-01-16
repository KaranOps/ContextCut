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
        self.provider = settings.DIRECTOR_PROVIDER
        self.model = settings.DIRECTOR_MODEL
        self.client = None

        logger.info(f"Initializing TimelineGenerator. Provider: {self.provider}, Model: {self.model}")

        if self.provider == "openai" and settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "groq" and settings.GROQ_API_KEY:
             self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=settings.GROQ_API_KEY
            )
        
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

        if not self.client and self.provider != "local":
             # If provider is local, we might need a local LLM call or mock?
             # For now, if no client, we can't generate.
             logger.error("No Director client available.")
             return {"timeline": []}

        # Index the catalog first (Idempotent)
        self.vector_service.index_catalog(broll_catalog)

        # Pre-filter candidates for each segment
        transcript_with_options = []
        
        for idx, segment in enumerate(transcript):
            text = segment.get("text", "")
            candidates = self.vector_service.get_best_matches(text)
            
            seg_info = segment.copy()
            if candidates:
                seg_info["available_broll"] = candidates
            else:
                seg_info["available_broll"] = [] 
            
            transcript_with_options.append(seg_info)

        system_prompt = self._construct_system_prompt()
        
        user_content = json.dumps({
            "A-Roll Transcript with Options": transcript_with_options,
        }, indent=2)

        try:
            # Handle o1-series constraints if applicable (no system role? no temperature?)
            # o1-mini supports temperature=1 fixed essentially.
            # We'll set temperature=0.2 generally, but for o1 we might need to adjust or let API handle ignore.
            
            # Prepare base params
            api_params = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the input data:\n{user_content}"}
                ],
                "model": self.model,
            }

            # Add temperature only if NOT an o-series reasoning model (which often have fixed temp or distinct params)
            # e.g. o1-mini, o3-mini
            if not self.model.startswith("o"): 
                 api_params["temperature"] = 0.2

            # Basic call
            response = self.client.chat.completions.create(**api_params) 
            
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
            
        ordered_transcript_starts = [t["start"] for t in transcript]
        def find_segment(start_time):
             # Simple proximity search
             for seg in transcript:
                if abs(seg["start"] - start_time) < 0.15: 
                    return seg
             return None

        total_video_end = transcript[-1]["end"]

        for event in raw_events:
            # Confidence Threshold
            if event.get("confidence", 0) < settings.MIN_LLM_CONFIDENCE:
                logger.debug(f"Dropping event due to low confidence: {event}")
                continue

            a_roll_start = event.get("a_roll_start")
            a_roll_seg = find_segment(a_roll_start)
            
            if not a_roll_seg:
                logger.warning(f"Dropping event: Start time {a_roll_start} does not match any A-roll segment.")
                continue

            # Strict Duration Enforcement
            actual_duration = a_roll_seg["end"] - a_roll_seg["start"]
            event["duration_sec"] = actual_duration 
            
            # Overlap Protection
            if a_roll_start + actual_duration > total_video_end + 0.1:
                logger.warning(f"Dropping event: Segment exceeds total video duration.")
                continue

            # Minimum Cut Duration
            if actual_duration < settings.MIN_BROLL_DURATION:
                logger.debug(f"Dropping event: Duration {actual_duration:.2f}s < {settings.MIN_BROLL_DURATION}s")
                continue

            # Cool-down Check
            time_since_last = a_roll_start - last_broll_end
            if time_since_last < settings.BROLL_COOL_DOWN_SECONDS:
                logger.debug(f"Dropping event: Cool-down violation. gap={time_since_last:.2f}s")
                continue

            # Visual Diversity Check
            b_roll_id = event.get("b_roll_id")
            if b_roll_id:
                # Check if this ID was used recently
                past_usages = used_broll_timestamps.get(b_roll_id, [])
                if any(abs(a_roll_start - t) < settings.BROLL_DIVERSITY_WINDOW_SECONDS for t in past_usages):
                    logger.debug(f"Dropping event: Diversity violation for {b_roll_id}")
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
               # Role: Lead Narrative Director & AI Video Editor (System: SemanticSync)
                You are the high-level intelligence responsible for the "Final Cut." Your goal is to transform a raw A-roll transcript into a visually engaging, professionally paced video by surgically inserting B-roll candidates based on semantic, technical, and narrative logic.

                # Narrative Context
                - **A-Roll (Primary)**: The speaker's verbal journey and emotional beats.
                - **B-Roll (Secondary)**: Visual metadata including `activity`, `category`, `technical` (shot_type, camera_movement, lighting), and `search_tags`.

                # Decision-Making Framework
                ## 1. Semantic Resonance (The "Why")
                - Priority 1: Direct Match (The speaker mentions a specific object or action).
                - Priority 2: Metaphorical Match (The speaker discusses 'growth'; show a 'panning shot of a skyline' or 'time-lapse of a sprout').
                - Use the `search_tags` to bridge the gap between spoken words and visual descriptors.

                ## 2. Cinematic Continuity (The "Flow")
                - **Pacing Anchor**: Match the B-roll's `camera_movement` to the speaker's tempo. 
                    - Fast, punchy sentences = Handheld, Panning, or Zooming shots.
                    - Calm, instructional sentences = Static or Tilt shots.
                - **Visual Flow**: Avoid "Visual Jarring." If the current segment uses a 'Macro' shot, try to follow it with a 'Medium' shot rather than a 'Wide' shot to maintain a natural optical progression.

                ## 3. Strict Operational Constraints (The "Rules")
                - **Candidate Integrity**: You MUST ONLY select from the provided `available_broll` list for each segment. If a segment has no candidates or none are relevant, return "b_roll_id": null.
                - **Cool-Down Enforcement**: Ensure at least {settings.BROLL_COOL_DOWN_SECONDS}s of A-roll is visible between B-roll clips. Do not over-edit.
                - **Visual Diversity**: If `broll_1.mp4` was used at 10.0s, it cannot be used again until {settings.BROLL_DIVERSITY_WINDOW_SECONDS}s have passed.
                - **Duration Accuracy**: `duration_sec` must precisely match `a_roll_end - a_roll_start`. Do not truncate or extend.

                # Final Output Instruction
                Return ONLY a valid JSON object. No preamble. No "Here is your timeline." Just the raw JSON.

                {{
                "timeline": [
                    {{
                    "a_roll_start": float,
                    "duration_sec": float,
                    "b_roll_id": "string",
                    "b_roll_start_offset": 0.0,
                    "confidence": float (0.0 to 1.0),
                    "reason": "Technical rationale: I chose [BROLL_ID] because the [SHOT_TYPE] reinforces the [TEXT] while the [LIGHTING] maintains the established mood."
                    }}
                ]
                }}

                # Example Reasoning
                "Chose broll_05 because the speaker discussed 'surgical precision' and the visual shows a 'Macro Close-up' of 'suturing,' which provides the exact detail required for this instructional beat."
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
