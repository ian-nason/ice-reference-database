SELECT state, count(*) AS facilities FROM facilities GROUP BY state ORDER BY facilities DESC, state LIMIT 5
