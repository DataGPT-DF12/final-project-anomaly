
  
    

    create or replace table `stately-node-363801`.`network`.`clean_network`
      
    
    

    OPTIONS()
    as (
      

SELECT
  COUNT(label) AS label_count
FROM
  `stately-node-363801`.`network`.`network_data_raw`
    );
  