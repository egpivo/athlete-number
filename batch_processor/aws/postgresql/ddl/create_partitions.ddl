CREATE TABLE allsports_bib_number_detection_2025_02
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE allsports_bib_number_detection_2025_03
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

CREATE TABLE allsports_bib_number_detection_2025_04
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');

CREATE TABLE allsports_bib_number_detection_2025_05
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');

CREATE TABLE allsports_bib_number_detection_2025_06
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE TABLE allsports_bib_number_detection_2025_07
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');

CREATE TABLE allsports_bib_number_detection_2025_08
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');

CREATE TABLE allsports_bib_number_detection_2025_09
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');

CREATE TABLE allsports_bib_number_detection_2025_10
PARTITION OF allsports_bib_number_detection
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
