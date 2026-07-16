import time
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
from pathlib import Path
import json

from app.meeting.artifacts.speaker import (
    ParticipantRoster,
    SpeakerMapping,
    SpeakerMappingEntry,
    SpeakerTimeline,
    ParticipantPresenceTimeline,
)
from app.meeting.config import meeting_config
from app.meeting.logger import get_logger
from .strategy import SpeakerMappingStrategy

log = get_logger("attribution.mapping.strategy")


class JoinOrderMappingStrategy(SpeakerMappingStrategy):
    """Production strategy: maps participants using eligibility filtering, presence windows, and scoring."""

    @property
    def strategy_name(self) -> str:
        return "join_order"

    async def build_mapping(
        self,
        timeline: SpeakerTimeline,
        roster: Optional[ParticipantRoster],
    ) -> SpeakerMapping:
        start_dt = datetime.now(timezone.utc)
        t0 = time.monotonic()

        # Try to load ParticipantPresenceTimeline from disk to get precise presence windows
        presence_timeline = None
        timeline_path = Path(meeting_config.RECORDING_OUTPUT_DIR) / timeline.meeting_id / "participant_presence_timeline.json"
        if timeline_path.exists():
            try:
                with open(timeline_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    presence_timeline = ParticipantPresenceTimeline.model_validate(data)
            except Exception as exc:
                log.warning("failed to load presence timeline from disk", error=str(exc))

        # Determine the recording start time reference
        rec_start_str = None
        if presence_timeline:
            rec_start_str = presence_timeline.recording_started_at or presence_timeline.timeline_started_at or presence_timeline.meeting_started_at
            
        if not rec_start_str:
            # Try to read MeetingRecording artifact from the processing directory
            recording_path = Path(meeting_config.PROCESSING_OUTPUT_DIR) / timeline.meeting_id / "meeting_recording.json"
            if recording_path.exists():
                try:
                    from app.meeting.artifacts.recording import MeetingRecording
                    with open(recording_path, "r", encoding="utf-8") as f:
                        rec_data = json.load(f)
                        recording = MeetingRecording.model_validate(rec_data)
                        rec_start_str = recording.recording_start_time
                except Exception as exc:
                    log.warning("failed to load recording from disk", error=str(exc))
                    
        # Parse recording start time as datetime
        rec_start = None
        if rec_start_str:
            try:
                rec_start = datetime.fromisoformat(rec_start_str.replace("Z", "+00:00"))
            except Exception:
                pass

        if not rec_start and presence_timeline and presence_timeline.events:
            # Fallback to the earliest event timestamp as rec_start
            event_timestamps = []
            for event in presence_timeline.events:
                try:
                    dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                    event_timestamps.append(dt)
                except Exception:
                    continue
            if event_timestamps:
                rec_start = min(event_timestamps)

        # Build intervals dict: participant_id -> list of (start_rel_seconds, end_rel_seconds)
        intervals: Dict[str, List[Tuple[float, float]]] = {}
        
        if rec_start and presence_timeline:
            # Sort events by sequence number
            sorted_events = sorted(presence_timeline.events, key=lambda e: e.sequence_number)
            open_intervals = {}
            for event in sorted_events:
                pid = event.participant_id
                try:
                    event_dt = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                    event_rel = (event_dt - rec_start).total_seconds()
                except Exception:
                    continue
                    
                if event.event_type in ("ParticipantJoined", "ParticipantRejoined"):
                    if pid not in open_intervals:
                        open_intervals[pid] = event_rel
                elif event.event_type == "ParticipantLeft":
                    if pid in open_intervals:
                        start_rel = open_intervals.pop(pid)
                        intervals.setdefault(pid, []).append((start_rel, event_rel))
            # Close any remaining open intervals
            for pid, start_rel in open_intervals.items():
                intervals.setdefault(pid, []).append((start_rel, float('inf')))

        # Roster-based fallback for any missing/remaining participants
        if roster:
            for p in roster.participants:
                if p.participant_id not in intervals:
                    join_rel = 0.0
                    if rec_start:
                        try:
                            p_join = datetime.fromisoformat(p.join_time.replace("Z", "+00:00"))
                            join_rel = (p_join - rec_start).total_seconds()
                        except Exception:
                            pass
                    
                    leave_rel = float('inf')
                    if p.leave_time and rec_start:
                        try:
                            p_leave = datetime.fromisoformat(p.leave_time.replace("Z", "+00:00"))
                            leave_rel = (p_leave - rec_start).total_seconds()
                        except Exception:
                            pass
                            
                    intervals[p.participant_id] = [(join_rel, leave_rel)]

        # Build eligible participants list
        eligible_participants = []
        excluded_bots_count = 0
        if roster:
            for p in roster.participants:
                is_bot = p.is_bot or p.display_name.lower().strip() in (meeting_config.BOT_NAME.lower().strip(), "kai bot")
                if is_bot:
                    log.info("Participant excluded", participant_id=p.participant_id, display_name=p.display_name, reason="is_bot=True")
                    excluded_bots_count += 1
                    continue
                if not p.participant_id or p.participant_id.strip() == "":
                    log.info("Participant excluded", participant_id=p.participant_id, display_name=p.display_name, reason="invalid_participant_id")
                    continue
                eligible_participants.append(p)

        # Collect unique speaker labels and their turns
        speaker_first_appearance = {}
        speaker_turns_map = {}
        for turn in timeline.turns:
            speaker_first_appearance.setdefault(turn.speaker_label, turn.start_time)
            speaker_turns_map.setdefault(turn.speaker_label, []).append(turn)

        sorted_speaker_labels = sorted(speaker_first_appearance.keys(), key=lambda lbl: speaker_first_appearance[lbl])

        entries = []
        resolved = 0
        unresolved = 0

        log.info("speaker.mapping.started", eligible_participants=len(eligible_participants), excluded_bots=excluded_bots_count)

        # First, calculate scores for every (speaker, candidate) pair
        speaker_candidates_map = {}
        global_candidate_pairs = []

        for label in sorted_speaker_labels:
            turns = speaker_turns_map.get(label, [])
            candidates_scores = []

            for p in eligible_participants:
                score = 100  # Base human score
                overlapping_turns = 0
                overlapping_duration = 0.0

                for turn in turns:
                    overlaps = False
                    for p_start, p_end in intervals.get(p.participant_id, []):
                        overlap_start = max(p_start, turn.start_time)
                        overlap_end = min(p_end, turn.end_time)
                        if overlap_start < overlap_end:
                            overlaps = True
                            overlapping_duration += (overlap_end - overlap_start)

                    if overlaps:
                        overlapping_turns += 1

                if overlapping_turns > 0:
                    score += 40
                else:
                    score -= 1000  # Penalty for no overlap

                if len(turns) > 0 and overlapping_turns >= (len(turns) / 2):
                    score += 20

                # Earlier human join order bonus (+10 for join_order=1, decaying)
                if p.join_order > 0:
                    score += (10.0 / p.join_order)

                candidates_scores.append({
                    "participant_id": p.participant_id,
                    "participant": p,
                    "score": score,
                    "overlapping_duration": overlapping_duration,
                    "join_order": p.join_order,
                    "name": p.display_name
                })
                
            speaker_candidates_map[label] = candidates_scores
            
            # Log all candidates' scores for this speaker
            log.info("Candidate scores", speaker_label=label, scores={c["name"]: round(c["score"], 2) for c in candidates_scores})

            # Add valid candidates (score > 0) to the global candidate pair matching list
            for c in candidates_scores:
                if c["score"] > 0:
                    global_candidate_pairs.append({
                        "speaker_label": label,
                        "participant_id": c["participant_id"],
                        "participant": c["participant"],
                        "score": c["score"],
                        "overlapping_duration": c["overlapping_duration"],
                        "join_order": c["join_order"],
                        "name": c["name"]
                    })

        # Sort global candidate pairs by:
        # 1. score (descending)
        # 2. overlapping_duration (descending)
        # 3. join_order (ascending)
        global_candidate_pairs.sort(key=lambda x: (-x["score"], -x["overlapping_duration"], x["join_order"]))

        # Greedily match speakers to participants one-to-one
        matched_speakers = {}  # speaker_label -> participant
        matched_participants = set()  # participant_id

        for pair in global_candidate_pairs:
            lbl = pair["speaker_label"]
            pid_candidate = pair["participant_id"]
            if lbl not in matched_speakers and pid_candidate not in matched_participants:
                matched_speakers[lbl] = pair["participant"]
                matched_participants.add(pid_candidate)

        for label in sorted_speaker_labels:
            turns = speaker_turns_map.get(label, [])
            total_duration = sum(t.end_time - t.start_time for t in turns)
            candidates_scores = speaker_candidates_map[label]

            # Get valid candidates (score > 0) sorted for confidence calculation
            valid_candidates = [c for c in candidates_scores if c["score"] > 0]
            valid_candidates.sort(key=lambda c: (-c["score"], -c["overlapping_duration"], c["join_order"]))

            pid = "UNKNOWN_PARTICIPANT"
            pname = "Unknown Participant"
            confidence = 0.0

            matched_p = matched_speakers.get(label)

            if matched_p and valid_candidates:
                # Find matching candidate dict in valid_candidates
                best = next(c for c in valid_candidates if c["participant_id"] == matched_p.participant_id)
                best_dur = best["overlapping_duration"]
                best_ratio = best_dur / total_duration if total_duration > 0 else 0.0

                # Check for equal score ties
                if len(valid_candidates) > 1:
                    second_best = valid_candidates[1]
                    if abs(best["score"] - second_best["score"]) < 0.01:
                        log.info("Fallback strategy used", speaker_label=label, reason="Equal confidence")

                # Confidence calculation comparing best against other candidates
                valid_others = [c for c in valid_candidates if c["participant_id"] != matched_p.participant_id]
                
                if not valid_others:
                    if best_ratio >= 0.9:
                        confidence = 0.98
                    elif best_ratio >= 0.5:
                        confidence = 0.85
                    else:
                        confidence = 0.55
                else:
                    second = valid_others[0]
                    if abs(best["score"] - second["score"]) < 0.01:
                        confidence = 0.25
                    else:
                        if best_ratio >= 0.9:
                            if len(valid_others) == 1:
                                confidence = 0.91
                            else:
                                confidence = 0.74
                        elif best_ratio >= 0.5:
                            confidence = 0.65
                        else:
                            confidence = 0.55

                # Check confidence threshold
                if confidence >= 0.3:
                    pid = matched_p.participant_id
                    pname = matched_p.display_name
                    resolved += 1
                else:
                    log.info("Speaker unmapped: confidence below threshold", speaker_label=label, confidence=confidence)
                    unresolved += 1
            else:
                unresolved += 1

            log.info("Selected mapping", speaker_label=label, selected=pname, confidence=confidence)

            entries.append(
                SpeakerMappingEntry(
                    speaker_label=label,
                    participant_id=pid,
                    participant_name=pname,
                    mapping_confidence=confidence,
                    mapping_source=self.strategy_name,
                )
            )

        end_dt = datetime.now(timezone.utc)
        duration_ms = int((time.monotonic() - t0) * 1000)

        return SpeakerMapping(
            meeting_id=timeline.meeting_id,
            parent_speaker_timeline_id=timeline.id,
            parent_participant_roster_id=roster.id if roster else None,
            mapping_strategy=self.strategy_name,
            entries=entries,
            resolved_count=resolved,
            unresolved_count=unresolved,
            participant_count=len(eligible_participants),
            speaker_count=len(sorted_speaker_labels),
            mapping_started_at=start_dt.isoformat(),
            mapping_completed_at=end_dt.isoformat(),
            mapping_duration_ms=duration_ms,
            processing_version=meeting_config.MAPPING_PROCESSING_VERSION,
        )
