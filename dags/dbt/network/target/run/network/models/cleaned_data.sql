
  
    

    create or replace table `stately-node-363801`.`network`.`cleaned_data`
      
    
    

    OPTIONS()
    as (
      
-- Menghapus komentar yang ada pada kolom tertentu 

WITH cleaned_data AS (
  SELECT 
  SUBSTR(GENERATE_UUID(), 1, 12) AS primary_key,
  *
  FROM 
    `stately-node-363801`.`network`.`network_data_raw`
  WHERE StartTime IS NOT NULL
    AND Dur IS NOT NULL
    AND `Proto` IS NOT NULL
    AND SrcAddr IS NOT NULL
    AND Sport IS NOT NULL
    AND Dir IS NOT NULL
    AND DstAddr IS NOT NULL
    AND Dport IS NOT NULL
    AND `State` IS NOT NULL
    AND sTos IS NOT NULL
    AND dTos IS NOT NULL
    AND TotPkts IS NOT NULL
    AND TotBytes IS NOT NULL
    AND SrcBytes IS NOT NULL
    AND Label IS NOT NULL
),
mode_dTos AS (
  SELECT dTos
  FROM (
    SELECT dTos, COUNT(*) AS freq
    FROM cleaned_data
    WHERE dTos IS NOT NULL
    GROUP BY dTos
    ORDER BY freq DESC
    LIMIT 1
  )
)
SELECT
  primary_key,
  Dur as duration,
  `Proto` as protocol,
  SrcAddr as source_address,
  Sport as source_port,
  Dir as direction,
  DstAddr as destination_address,
  Dport as destination_port,
  State as state,
  sTos as source_tos,
  IFNULL(dTos, (SELECT dTos FROM mode_dTos)) AS destination_tos,
  TotPkts as total_packets,
  TotBytes as total_bytes,
  SrcBytes as source_bytes,
  REGEXP_REPLACE(Label, r'flow=', '') AS label,
  SAFE_CAST(SPLIT(StartTime, ':')[OFFSET(0)] AS INT64) AS minutes,
  SAFE_CAST(SPLIT(SPLIT(StartTime, ':')[OFFSET(1)], '.')[OFFSET(0)] AS INT64) AS seconds,
  SAFE_CAST(SPLIT(StartTime, '.')[OFFSET(1)] AS INT64) AS microseconds
  -- Add more columns as necessary
FROM cleaned_data
    );
  