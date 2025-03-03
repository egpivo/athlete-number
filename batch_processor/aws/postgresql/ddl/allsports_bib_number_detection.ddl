CREATE TABLE allsports_bib_number_detection (
    eid TEXT NOT NULL,
    cid TEXT NOT NULL,
    photonum TEXT NOT NULL,
    tag TEXT NOT NULL,

    cutoff_date DATE NOT NULL,  -- Partition Key
    env TEXT NOT NULL CHECK (env IN ('test', 'production')),  -- New column to store the environment

    created_at TIMESTAMPTZ DEFAULT NOW(),
    modified_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (eid, cid, photonum, tag, cutoff_date, env)
) PARTITION BY RANGE (cutoff_date);
