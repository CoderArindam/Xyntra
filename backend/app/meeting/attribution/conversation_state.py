"""Conversation State Model (Phase 2.6).

Immutable state representation tracking ongoing conversation dynamics across transcript segments.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    """Immutable snapshot of conversation dynamics at segment t."""

    current_active_speaker: Optional[str] = None
    previous_speaker: Optional[str] = None
    speaker_momentum: Dict[str, float] = Field(default_factory=dict)
    recent_alternation_history: List[str] = Field(default_factory=list)
    conversation_ownership: Optional[str] = None
    interruption_stack: List[str] = Field(default_factory=list)
    expected_responder: Optional[str] = None
    participant_last_spoke: Dict[str, float] = Field(default_factory=dict)
    consecutive_turns: int = 0
    total_turns_processed: int = 0
    last_segment_end_time: float = 0.0

    def transition(
        self,
        winner_pid: Optional[str],
        start_time: float,
        end_time: float,
        is_interruption: bool = False,
        next_expected_responder: Optional[str] = None,
    ) -> ConversationState:
        """Produce next state snapshot after resolving a segment."""
        new_history = list(self.recent_alternation_history)
        if winner_pid:
            new_history.append(winner_pid)
            if len(new_history) > 10:
                new_history = new_history[-10:]

        # Update momentum (decay existing, boost winner)
        new_momentum = {k: max(0.0, v * 0.85) for k, v in self.speaker_momentum.items()}
        if winner_pid:
            new_momentum[winner_pid] = new_momentum.get(winner_pid, 0.0) + 1.0

        # Update ownership (strongest momentum participant)
        new_ownership = self.conversation_ownership
        if new_momentum:
            top_speaker = max(new_momentum.items(), key=lambda x: x[1])
            if top_speaker[1] >= 2.0:
                new_ownership = top_speaker[0]

        # Update interruption stack
        new_interruption_stack = list(self.interruption_stack)
        if is_interruption and self.current_active_speaker and self.current_active_speaker != winner_pid:
            if self.current_active_speaker not in new_interruption_stack:
                new_interruption_stack.append(self.current_active_speaker)
        elif winner_pid and winner_pid in new_interruption_stack:
            # Winner resumed speech; remove from stack
            new_interruption_stack.remove(winner_pid)

        # Update consecutive turns
        if winner_pid == self.current_active_speaker:
            new_consecutive = self.consecutive_turns + 1
        else:
            new_consecutive = 1 if winner_pid else 0

        # Update last spoke timestamps
        new_last_spoke = dict(self.participant_last_spoke)
        if winner_pid:
            new_last_spoke[winner_pid] = end_time

        return ConversationState.model_construct(
            current_active_speaker=winner_pid,
            previous_speaker=self.current_active_speaker,
            speaker_momentum=new_momentum,
            recent_alternation_history=new_history,
            conversation_ownership=new_ownership,
            interruption_stack=new_interruption_stack,
            expected_responder=next_expected_responder,
            participant_last_spoke=new_last_spoke,
            consecutive_turns=new_consecutive,
            total_turns_processed=self.total_turns_processed + 1,
            last_segment_end_time=end_time,
        )
