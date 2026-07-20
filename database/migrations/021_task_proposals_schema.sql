-- 021_task_proposals_schema.sql
-- Staging table and enum for AI-extracted meeting task proposals

-- Enum for task proposal status
DO $$ BEGIN
    CREATE TYPE task_proposal_status AS ENUM ('pending', 'approved', 'rejected');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Pre-requisite table for meeting sessions if not already present
CREATE TABLE IF NOT EXISTS meeting_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_url TEXT,
    session_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'completed',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Staging table for task proposals
CREATE TABLE IF NOT EXISTS task_proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
    meeting_session_id UUID NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    suggested_assignee_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    confidence_score NUMERIC(3,2) CHECK (confidence_score BETWEEN 0 AND 1),
    source_transcript_quote TEXT,
    status task_proposal_status NOT NULL DEFAULT 'pending',
    raw_llm_payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL
);

-- Indexes for efficient querying by org, session, and status
CREATE INDEX IF NOT EXISTS idx_task_proposals_org_id ON task_proposals(org_id);
CREATE INDEX IF NOT EXISTS idx_task_proposals_meeting_session_id ON task_proposals(meeting_session_id);
CREATE INDEX IF NOT EXISTS idx_task_proposals_status ON task_proposals(status);
