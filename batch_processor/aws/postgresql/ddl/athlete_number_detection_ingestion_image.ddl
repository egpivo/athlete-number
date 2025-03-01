CREATE TABLE athlete_number_detection_ingestion (
    image_key TEXT NOT NULL,           -- Unique identifier for the processed image
    cutoff_date DATE NOT NULL,         -- Cutoff date for processing
    ingestion_timestamp TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (image_key, cutoff_date) -- Composite primary key
);
