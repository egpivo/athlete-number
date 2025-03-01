CREATE TABLE athlete_number_detection_images (
    image_key TEXT NOT NULL,           -- Unique identifier for the processed image
    cutoff_date DATE NOT NULL,         -- Cutoff date for processing
    status TEXT DEFAULT 'pending',  -- 'pending', 'processing', 'failed', 'processed'
    ingestion_timestamp TIMESTAMP DEFAULT NOW(),
    processed_timestamp TIMESTAMP NULL,
    PRIMARY KEY (image_key, cutoff_date) -- Composite primary key
);
