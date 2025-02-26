CREATE TABLE allsports_bib_number_detection (
    eid TEXT NOT NULL,        -- Event ID
    cid TEXT NOT NULL,        -- Customer ID
    photonum TEXT NOT NULL,   -- Photo Number
    tag TEXT NOT NULL,        -- Detected bib number or empty string if none

    created_at TIMESTAMPTZ DEFAULT NOW(),  -- Stores the record creation timestamp (UTC)
    modified_at TIMESTAMPTZ DEFAULT NOW(),  -- Stores the last modification timestamp (UTC)

    PRIMARY KEY (eid, cid, photonum)  -- Composite Primary Key to prevent duplicates
);
