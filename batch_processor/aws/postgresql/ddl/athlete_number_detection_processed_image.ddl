CREATE TABLE athlete_number_detection_processed_image (
    image_key TEXT PRIMARY KEY,        -- Unique identifier for the processed image
    processed_at TIMESTAMP DEFAULT NOW()  -- Auto-fills with the current timestamp
);
