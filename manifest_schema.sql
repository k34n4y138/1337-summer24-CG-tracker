CREATE TABLE IF NOT EXISTS codingamer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    intra_login TEXT NULL,
    intra_campus TEXT NULL,

    cg_uuid TEXT NOT NULL,
    cg_username TEXT NULL NOT NULL
);


CREATE TABLE IF NOT EXISTS rankscrap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    codingamer_id INTEGER,
    online_since DATETIME,

    session_uuid TEXT,
    submission_time DATETIME,
    stability_percentage INTEGER,

    score INTEGER,
    language_used TEXT,
    
    league_id INTEGER,
    global_rank INTEGER,
    school_rank INTEGER
);
