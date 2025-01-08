CREATE TABLE IF NOT EXISTS diary (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    content TEXT
);

CREATE TABLE IF NOT EXISTS checklist (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    task VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending'
);
