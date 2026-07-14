from typing import List
from app.meeting.artifacts import MeetingRecording, TaskProposal
from app.meeting.contracts import (
    AudioProcessor,
    SpeechToTextProvider,
    DiarizationProvider,
    TranscriptNormalizer,
    TranscriptBuilder,
    MeetingIntelligenceProvider,
    TaskExtractor,
)


class MeetingProcessingPipeline:
    """Orchestrator for the entire Meeting Intelligence pipeline.
    Executes stages as a dependency graph.
    """

    def __init__(
        self,
        audio_processor: AudioProcessor,
        stt_provider: SpeechToTextProvider,
        diarization_provider: DiarizationProvider,
        transcript_normalizer: TranscriptNormalizer,
        transcript_builder: TranscriptBuilder,
        intelligence_provider: MeetingIntelligenceProvider,
        task_extractor: TaskExtractor,
        # assignment_engine, approval_engine omitted for brevity but conceptually part of the flow
    ):
        self.audio_processor = audio_processor
        self.stt_provider = stt_provider
        self.diarization_provider = diarization_provider
        self.transcript_normalizer = transcript_normalizer
        self.transcript_builder = transcript_builder
        self.intelligence_provider = intelligence_provider
        self.task_extractor = task_extractor

    async def run(self, recording: MeetingRecording) -> List[TaskProposal]:
        """Execute the full meeting processing pipeline."""
        
        # 1. Audio Processing
        processed_audio = await self.audio_processor.process(recording)
        
        # 2. Independent branches: Speech-To-Text & Diarization
        # In a real implementation, these would run via asyncio.gather()
        raw_transcript = await self.stt_provider.transcribe(processed_audio)
        speakers = await self.diarization_provider.diarize(processed_audio)
        
        # 3. Transcript Normalization
        normalized_transcript = await self.transcript_normalizer.normalize(raw_transcript)
        
        # 4. Transcript Building (Merge)
        final_transcript = await self.transcript_builder.build(normalized_transcript, speakers)
        
        # 5. Meeting Intelligence
        insights = await self.intelligence_provider.analyze(final_transcript)
        
        # 6. Task Extraction
        extracted_tasks = await self.task_extractor.extract(insights)
        
        # 7. Assignment (Stub for future engine)
        # proposals = await self.assignment_engine.assign(extracted_tasks)
        proposals = []
        
        return proposals
