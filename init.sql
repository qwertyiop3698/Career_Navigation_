-- pgvector 확장
CREATE EXTENSION IF NOT EXISTS vector;

-- users
CREATE TABLE users (
    id UUID PRIMARY KEY,
    job_target TEXT,
    experience_level TEXT,
    goal_period INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- skills
CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- user_skills
CREATE TABLE user_skills (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    skill_id INT REFERENCES skills(id) ON DELETE CASCADE
);

-- job_postings
CREATE TABLE job_postings (
    id SERIAL PRIMARY KEY,
    company TEXT,
    title TEXT,
    description TEXT,
    source TEXT,
    created_at TIMESTAMP
);

-- job_skills
CREATE TABLE job_skills (
    id SERIAL PRIMARY KEY,
    job_id INT REFERENCES job_postings(id) ON DELETE CASCADE,
    skill_id INT REFERENCES skills(id) ON DELETE CASCADE
);

-- skill_trends
CREATE TABLE skill_trends (
    id SERIAL PRIMARY KEY,
    skill_id INT REFERENCES skills(id),
    global_score FLOAT,
    domestic_score FLOAT,
    time_lag INT,
    growth_rate FLOAT,
    updated_at TIMESTAMP
);

-- predictions
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    job_role TEXT,
    probability FLOAT,
    diffusion_time FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- roadmaps
CREATE TABLE roadmaps (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    content JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- documents
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    source TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- embeddings
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    document_id INT REFERENCES documents(id) ON DELETE CASCADE,
    embedding VECTOR(1536)
);