INSERT INTO allsports_bib_number_detection (eid, cid, photonum, tag, cutoff_date, env, created_at, modified_at)
SELECT eid, cid, photonum, tag,
       '2025-02-25'::DATE AS cutoff_date,
       'test' AS env,
       created_at, modified_at
FROM allsports_bib_number_detection_backup;
