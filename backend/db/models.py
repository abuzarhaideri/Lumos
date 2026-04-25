SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source_doc_name TEXT,
    source_doc_text TEXT,
    status TEXT DEFAULT 'pending',
    iteration_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS curricula (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    lesson_plan JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lessons (
    id UUID PRIMARY KEY,
    curriculum_id UUID REFERENCES curricula(id),
    sequence_order INT,
    title TEXT,
    content JSONB,
    quiz JSONB,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS student_attempts (
    id UUID PRIMARY KEY,
    lesson_id UUID REFERENCES lessons(id),
    attempt_number INT,
    score FLOAT,
    confusion_log JSONB,
    passed BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
