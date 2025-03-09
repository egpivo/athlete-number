CREATE TABLE athlete_number_detection_processed_image (
    image_key TEXT NOT NULL,           -- Unique identifier for the processed image
    race_id TEXT DEFAULT NULL,
    cutoff_date DATE NOT NULL,         -- Cutoff date for processing
    env TEXT NOT NULL CHECK (env IN ('test', 'production')),  -- New column to store the environment
    processed_at TIMESTAMP DEFAULT NOW(), -- Auto-fills with the current timestamp
    PRIMARY KEY (image_key, cutoff_date) -- Composite primary key
);
