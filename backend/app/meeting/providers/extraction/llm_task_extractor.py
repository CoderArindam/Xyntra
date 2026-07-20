"""LLM Task Extractor implementation."""

import json
import logging
import asyncio
from typing import List, Optional, Any
from pydantic import BaseModel, Field

from app.meeting.contracts.extraction import TaskExtractor
from app.meeting.artifacts.speaker import ParticipantAttributedTranscript, ParticipantRoster
from app.meeting.artifacts.task import ExtractedTask
from app.ai.gateway.ai_gateway import AIGateway
from app.ai.exceptions import ParsingError
from app.meeting.config import meeting_config

logger = logging.getLogger("meeting.extraction.llm")



from datetime import datetime, timezone

class LLMExtractedTaskPayload(BaseModel):
    """Pydantic validation schema for raw LLM JSON items."""
    title: str = Field(..., description="Actionable title summarizing the work item")
    description: Optional[str] = Field(default="", description="Technical context and details from meeting")
    priority: Optional[str] = Field(default="MEDIUM", description="Task priority (LOW, MEDIUM, HIGH, URGENT)")
    due_date: Optional[str] = Field(default=None, description="ISO date string (YYYY-MM-DD) if target deadline mentioned, else null")
    suggested_assignee_name: Optional[str] = Field(default=None, description="Name or full name of person designated to perform or receive the task (e.g. 'Arindam Mukherjee')")
    suggested_speaker_label: Optional[str] = Field(default=None, description="Speaker name or label responsible")
    suggested_board_name: Optional[str] = Field(default=None, description="Exact name of target board if clearly mentioned, or null")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence rating between 0 and 1")
    source_transcript_quote: Optional[str] = Field(default=None, description="Direct quote supporting action item")


class LLMTaskExtractorResponse(BaseModel):
    """Container schema for structured LLM response validation."""
    tasks: List[LLMExtractedTaskPayload] = Field(default_factory=list)


class LLMTaskExtractor(TaskExtractor):
    """Extracts candidate action items from attributed meeting transcripts via LLM."""

    def __init__(self, gateway: Optional[AIGateway] = None):
        self.gateway = gateway or AIGateway()

    async def extract(
        self,
        insights: Any,
        roster: Optional[ParticipantRoster] = None,
        boards: Optional[List[dict]] = None,
        users: Optional[List[dict]] = None
    ) -> List[ExtractedTask]:
        """Extract task items from attributed transcript or meeting insights."""
        transcript: Optional[ParticipantAttributedTranscript] = None

        if isinstance(insights, ParticipantAttributedTranscript):
            transcript = insights
        elif hasattr(insights, "attributed_transcript"):
            transcript = getattr(insights, "attributed_transcript")
        
        if not transcript or not hasattr(transcript, "segments") or not transcript.segments:
            logger.info("Empty or missing transcript provided to LLMTaskExtractor.")
            return []

        # 1. Format transcript into readable text block with speaker attribution
        formatted_lines = []
        for seg in transcript.segments:
            speaker_name = seg.participant_name or seg.speaker_label or "Unknown Speaker"
            timestamp = f"[{seg.start_time:.1f}s]" if hasattr(seg, "start_time") and seg.start_time is not None else ""
            formatted_lines.append(f"{timestamp} {speaker_name}: {seg.text}")

        full_transcript_text = "\n".join(formatted_lines)

        board_names = [b["name"] for b in (boards or []) if b.get("name")]
        board_instruction = ""
        if board_names:
            board_instruction = (
                f"Active project boards in this organization: {json.dumps(board_names)}.\n"
                "For each extracted task, if the transcript clearly references one of these boards or the project it represents, set suggested_board_name to that exact board name.\n"
                "If ambiguous or not mentioned, set suggested_board_name to null.\n\n"
            )
        else:
            board_instruction = "Set suggested_board_name to null.\n\n"

        team_names = [f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() for u in (users or []) if u.get("first_name")]
        team_instruction = ""
        if team_names:
            team_instruction = f"Active team members in this organization: {json.dumps(team_names)}.\n\n"

        current_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        system_prompt = (
            "You are an expert AI software project manager analyzing a video meeting transcript.\n"
            "Your job is to identify and extract real, actionable work items and software tasks discussed in the meeting.\n\n"
            f"Context: Today's date is {current_date_str}.\n"
            f"{board_instruction}"
            f"{team_instruction}"
            "CRITICAL INSTRUCTIONS FOR EXTRACTION:\n"
            "1. TITLE:\n"
            "   - Write a concise, professional task title summarizing the ACTUAL WORK to be done (e.g., 'Influencer Campaign & Brand Endorsement Outreach').\n"
            "   - ABSOLUTELY FORBIDDEN IN TITLES: Never use meta instructions or creation phrases ('Create task for...', 'Assign task to...', 'Set priority...').\n"
            "2. DESCRIPTION (MUST BE A FORMAL ENGINEERING/PRODUCT SPECIFICATION):\n"
            "   - Write a clean, professional product specification focused purely on domain deliverables, technical requirements, and execution scope.\n"
            "   - ABSOLUTELY FORBIDDEN IN DESCRIPTIONS: Never use meta conversation or task creation phrases (DO NOT WRITE: 'Create a task for...', 'Create tasks under...', 'Assign to...', 'Ask him to...', 'This task should include...').\n"
            "   - Write directly about the actual work item (e.g., 'Engage target influencers for brand endorsement, define outreach scope, and prepare campaign requirements.').\n"
            "3. PRIORITY:\n"
            "   - Extract priority level based on urgency cues in transcript ('high', 'urgent', 'asap' -> 'High'; 'low' -> 'Low'; default 'Medium').\n"
            "4. DUE DATE:\n"
            "   - If a target deadline, relative date ('today', 'tomorrow', 'end of week'), or specific date is mentioned, calculate the date relative to today's date ({current_date_str}) in YYYY-MM-DD format. Otherwise set to null.\n"
            "5. ASSIGNEE / OWNER:\n"
            "   - CRITICAL: Pay close attention to who the task is designated FOR in conversation (e.g., if speaker says 'assign to me', set suggested_assignee_name to speaker's name; if speaker says 'assign to [Name]' or 'create a task for [Name]', set suggested_assignee_name to that person's name). Match against the active team members list if available.\n"
            "6. TARGET BOARD:\n"
            "   - Match the target project board mentioned in conversation to one of the provided active project board names in the organization.\n\n"
            "7. Return ONLY valid JSON matching this schema:\n"
            "{\n"
            '  "tasks": [\n'
            "    {\n"
            '      "title": "Concise task title summarizing actual work item",\n'
            '      "description": "Domain deliverables, technical scope, and requirements without meta phrases",\n'
            '      "priority": "High",\n'
            '      "due_date": "YYYY-MM-DD or null",\n'
            '      "suggested_assignee_name": "Full name of designated assigned person",\n'
            '      "suggested_speaker_label": "Name of speaker",\n'
            '      "suggested_board_name": "Exact or closest matching board name from provided list, or null",\n'
            '      "confidence_score": 0.85,\n'
            '      "source_transcript_quote": "Direct quote from speaker"\n'
            "    }\n"
            "  ]\n"
            "}\n"
        )

        user_prompt = f"Here is the meeting transcript:\n\n{full_transcript_text}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        max_retries = getattr(meeting_config, "EXTRACTION_MAX_RETRIES", 3)
        attempt = 0
        backoff = 1.0

        while attempt <= max_retries:
            try:
                attempt += 1
                response = await self.gateway.execute_prompt(
                    messages=messages,
                    org_ai_enabled=True,
                    user_has_permission=True,
                    response_schema=LLMTaskExtractorResponse
                )

                raw_tasks: List[LLMExtractedTaskPayload] = []
                if isinstance(response, LLMTaskExtractorResponse):
                    raw_tasks = response.tasks
                elif isinstance(response, dict):
                    content = response.get("content", "")
                    raw_tasks = self._parse_json_fallback(content)

                # Map to ExtractedTask objects and resolve speaker & board
                extracted_tasks: List[ExtractedTask] = []
                for item in raw_tasks:
                    assignee_id = self._match_assignee(item.suggested_assignee_name, item.suggested_speaker_label, roster, users)
                    board_id, board_conf, board_src = self._resolve_board(item.suggested_board_name, boards)
                    
                    sanitized_title = self._sanitize_title(item.title)
                    sanitized_desc = self._sanitize_description(item.description, sanitized_title)

                    extracted_task = ExtractedTask(
                        meeting_id=getattr(transcript, "meeting_id", ""),
                        title=sanitized_title,
                        description=sanitized_desc,
                        priority=self._normalize_priority(item.priority),
                        due_date=item.due_date,
                        suggested_speaker_label=item.suggested_speaker_label,
                        suggested_assignee_id=assignee_id,
                        suggested_board_name=item.suggested_board_name,
                        suggested_board_id=board_id,
                        board_confidence=board_conf,
                        board_source=board_src,
                        confidence_score=max(0.0, min(1.0, float(item.confidence_score))),
                        source_transcript_quote=item.source_transcript_quote,
                        raw_llm_payload=item.model_dump()
                    )
                    extracted_tasks.append(extracted_task)

                return extracted_tasks


            except ParsingError as pe:
                # Malformed output parsing error — log and skip, do not retry
                logger.warning(f"LLM output parsing error (malformed JSON): {pe}. Returning empty proposal list.")
                return []
            except Exception as exc:
                err_str = str(exc)
                if ("rate_limit" in err_str.lower() or "429" in err_str or "overloaded" in err_str.lower()) and attempt <= max_retries:
                    logger.warning(f"LLM extraction attempt {attempt} hit rate limit / transient error: {exc}. Retrying in {backoff:.1f}s...")
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                else:
                    logger.error(f"LLM task extraction failed on attempt {attempt}: {exc}")
                    return []

        return []

    def _parse_json_fallback(self, content: str) -> List[LLMExtractedTaskPayload]:
        """Fallback JSON parser for raw string responses with robust commentary stripping."""
        if not content:
            return []

        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        elif clean_content.startswith("```"):
            clean_content = clean_content[3:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
        clean_content = clean_content.strip()

        # Extract first valid JSON object or array structure if extra commentary exists
        import re
        json_match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', clean_content)
        if json_match:
            candidate = json_match.group(1).strip()
        else:
            candidate = clean_content

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "tasks" in parsed:
                items = parsed["tasks"]
            elif isinstance(parsed, list):
                items = parsed
            else:
                items = []

            results = []
            for item in items:
                try:
                    results.append(LLMExtractedTaskPayload.model_validate(item))
                except Exception:
                    pass
            return results
        except Exception as e:
            logger.warning(f"Fallback JSON parsing failed: {e}")
            return []

    def _normalize_name(self, text: Optional[str]) -> str:
        """Normalizes name strings by stripping accents and diacritics."""
        if not text:
            return ""
        import unicodedata
        normalized = unicodedata.normalize('NFKD', text)
        ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
        return ascii_text.lower().strip()

    def _match_assignee(
        self,
        assignee_name: Optional[str],
        speaker_label: Optional[str],
        roster: Optional[ParticipantRoster],
        users: Optional[List[dict]]
    ) -> Optional[int]:
        """Matches extracted assignee name or speaker label against organization users and roster with accent normalization."""
        targets = [t.strip() for t in [assignee_name, speaker_label] if t and t.strip()]
        if not targets:
            return None

        # 1. Match against database users list
        if users:
            for target in targets:
                clean_target = self._normalize_name(target)
                target_tokens = set(clean_target.replace("-", " ").split())
                
                # First pass: Exact full name or email match
                for u in users:
                    first = self._normalize_name(u.get("first_name"))
                    last = self._normalize_name(u.get("last_name"))
                    full = f"{first} {last}".strip()
                    email = (u.get("email") or "").strip().lower()

                    if full and (full == clean_target or clean_target.startswith(full) or clean_target.endswith(full)):
                        return u["id"]
                    if email and (email.split("@")[0] == clean_target):
                        return u["id"]

                # Second pass: Word-boundary token match for first or last name
                for u in users:
                    first = self._normalize_name(u.get("first_name"))
                    last = self._normalize_name(u.get("last_name"))
                    
                    first_tokens = set(first.replace("-", " ").split())
                    last_tokens = set(last.replace("-", " ").split())

                    if first and (first in target_tokens or first_tokens.intersection(target_tokens)):
                        return u["id"]
                    if last and (last in target_tokens or last_tokens.intersection(target_tokens)):
                        return u["id"]

        # 2. Fallback to roster matching
        if roster:
            for target in targets:
                res = self._match_speaker_to_roster(target, roster)
                if res is not None:
                    return res

        return None

    def _match_speaker_to_roster(self, speaker_label: Optional[str], roster: Optional[ParticipantRoster]) -> Optional[int]:
        """Matches a speaker name/label to a user ID in the participant roster."""
        if not speaker_label or not roster or not roster.participants:
            return None

        clean_label = speaker_label.strip().lower()
        for participant in roster.participants:
            display_name = getattr(participant, "display_name", "") or ""
            normalized_name = getattr(participant, "normalized_name", "") or ""
            user_id = getattr(participant, "user_id", None) or getattr(participant, "id", None)

            if display_name and (display_name.lower() in clean_label or clean_label in display_name.lower()):
                if isinstance(user_id, int):
                    return user_id
                elif isinstance(user_id, str) and user_id.isdigit():
                    return int(user_id)

            if normalized_name and (normalized_name.lower() in clean_label or clean_label in normalized_name.lower()):
                if isinstance(user_id, int):
                    return user_id
                elif isinstance(user_id, str) and user_id.isdigit():
                    return int(user_id)

        return None

    def _resolve_board(
        self,
        suggested_name: Optional[str],
        boards: Optional[List[dict]]
    ) -> tuple[Optional[int], Optional[float], Optional[str]]:
        """Resolves suggested board name using exact or fuzzy case-insensitive matching."""
        if not suggested_name or not boards:
            return None, None, None

        clean_suggested = suggested_name.strip().lower()
        
        # 1. Exact match
        for b in boards:
            b_name = (b.get("name") or "").strip().lower()
            if b_name and b_name == clean_suggested:
                return b.get("id"), 1.0, "llm_matched"

        # 2. Token overlap & substring match (e.g., 'marketing side v 2' -> 'Marketing Site v2', 'hero mobile website' -> 'hero')
        for b in boards:
            b_name = (b.get("name") or "").strip().lower()
            if not b_name:
                continue
            
            # Substring match
            if len(b_name) >= 3 and (b_name in clean_suggested or clean_suggested in b_name):
                return b.get("id"), 0.90, "llm_matched"
                
            # Token overlap match
            b_tokens = set(b_name.split())
            s_tokens = set(clean_suggested.split())
            common = b_tokens.intersection(s_tokens)
            if common:
                # Filter out generic stop words
                significant = [w for w in common if w not in {"board", "project", "side", "v2", "v1", "the", "a", "an", "for", "on", "site"}]
                if significant:
                    return b.get("id"), 0.85, "llm_matched"

        return None, None, None

    def _normalize_priority(self, val: Optional[str]) -> str:
        """Normalizes priority string to standard Title Case (High, Medium, Low)."""
        if not val:
            return "Medium"
        clean = val.strip().lower()
        if "high" in clean or "urgent" in clean or "critical" in clean:
            return "High"
        elif "low" in clean:
            return "Low"
        return "Medium"

    def _sanitize_title(self, raw_title: str) -> str:
        """Strips meta creation prefixes from titles."""
        if not raw_title:
            return "Untitled Work Item"
        clean = raw_title.strip()
        import re
        meta_patterns = [
            r"^(?:create|add|assign)\s+(?:a\s+)?task\s+(?:for|to|under|within|about)?\s*",
            r"^(?:task\s+for|task\s+to|action\s+item\s+for)\s*"
        ]
        for pattern in meta_patterns:
            clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip()
        if clean:
            return clean[0].upper() + clean[1:]
        return "Untitled Work Item"

    def _sanitize_description(self, raw_desc: str, title: str) -> str:
        """Strips conversational meta phrases and ensures professional domain description."""
        if not raw_desc:
            return f"Execute technical work and deliverables for {title}."
        
        clean = raw_desc.strip()
        import re
        
        # Remove literal meta prefixes
        meta_prefixes = [
            r"^(?:create|add)\s+(?:a\s+)?tasks?\s+(?:under|within|for|in|on)?\s+(?:the\s+)?[\w\s]+\s+board\s+to\s*",
            r"^(?:create|add)\s+(?:a\s+)?tasks?\s+(?:for|to|under|within|about)?\s*",
            r"^(?:assign|ask)\s+[\w\s]+\s+to\s+",
            r"^this\s+task\s+(?:is\s+to|should\s+include)\s*",
        ]
        for pattern in meta_prefixes:
            clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip()
            
        if clean:
            clean = clean[0].upper() + clean[1:]
        else:
            clean = f"Execute technical work and deliverables for {title}."
            
        return clean

