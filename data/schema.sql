PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS subreddit_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reddit_candidates (
    reddit_post_id TEXT PRIMARY KEY,
    subreddit TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    author TEXT,
    created_utc INTEGER NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS candidate_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reddit_post_id TEXT NOT NULL,
    comment_id TEXT NOT NULL UNIQUE,
    body TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    author TEXT,
    created_utc INTEGER,
    FOREIGN KEY (reddit_post_id) REFERENCES reddit_candidates(reddit_post_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS candidate_scores (
    reddit_post_id TEXT PRIMARY KEY,
    keep INTEGER NOT NULL CHECK (keep IN (0, 1)),
    reject_reason TEXT NOT NULL DEFAULT '',
    reaction_potential INTEGER NOT NULL CHECK (reaction_potential BETWEEN 1 AND 10),
    laugh_factor INTEGER NOT NULL CHECK (laugh_factor BETWEEN 1 AND 10),
    story_payoff INTEGER NOT NULL CHECK (story_payoff BETWEEN 1 AND 10),
    clarity_after_rewrite INTEGER NOT NULL CHECK (clarity_after_rewrite BETWEEN 1 AND 10),
    comment_bonus INTEGER NOT NULL CHECK (comment_bonus BETWEEN 1 AND 10),
    overall_score REAL NOT NULL,
    one_line_summary TEXT NOT NULL,
    host_angle TEXT NOT NULL,
    best_comment_ids_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT NOT NULL DEFAULT '',
    scored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reddit_post_id) REFERENCES reddit_candidates(reddit_post_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_date TEXT NOT NULL,
    status TEXT NOT NULL,
    title TEXT,
    description TEXT,
    script_path TEXT,
    audio_path TEXT,
    video_path TEXT,
    youtube_video_id TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS episode_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER NOT NULL,
    reddit_post_id TEXT NOT NULL,
    segment_order INTEGER NOT NULL,
    used_comments_json TEXT NOT NULL DEFAULT '[]',
    role_in_episode TEXT NOT NULL CHECK (role_in_episode IN ('primary', 'backup')),
    FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE,
    FOREIGN KEY (reddit_post_id) REFERENCES reddit_candidates(reddit_post_id) ON DELETE CASCADE,
    UNIQUE (episode_id, reddit_post_id),
    UNIQUE (episode_id, segment_order, role_in_episode)
);

CREATE TABLE IF NOT EXISTS host_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host_key TEXT NOT NULL UNIQUE,
    host_name TEXT NOT NULL,
    voice_id TEXT,
    persona_prompt_path TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_candidates_subreddit_created_utc
    ON reddit_candidates(subreddit, created_utc DESC);

CREATE INDEX IF NOT EXISTS idx_candidates_fetched_at
    ON reddit_candidates(fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_scores_overall_score
    ON candidate_scores(overall_score DESC);

CREATE INDEX IF NOT EXISTS idx_scores_keep_overall
    ON candidate_scores(keep, overall_score DESC);

CREATE INDEX IF NOT EXISTS idx_comments_candidate
    ON candidate_comments(reddit_post_id);

CREATE INDEX IF NOT EXISTS idx_episode_items_episode
    ON episode_items(episode_id);

CREATE INDEX IF NOT EXISTS idx_run_logs_run_date_stage
    ON run_logs(run_date, stage);
