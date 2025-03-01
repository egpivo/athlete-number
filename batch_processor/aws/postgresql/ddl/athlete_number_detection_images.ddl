CREATE TABLE athlete_number_detection_images (
    image_key TEXT PRIMARY KEY,
    status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'failed', 'processed'
    ingestion_timestamp TIMESTAMP DEFAULT NOW(),
    processed_timestamp TIMESTAMP NULL
);
