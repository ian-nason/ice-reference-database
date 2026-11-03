import importlib.metadata,json,sys
from pathlib import Path
from build_safety import require
import datapond,datapond.registry as registry,duckdb
registry.REGISTRY_URL=sys.argv[1]
registry.CACHE_DIR=Path(sys.argv[2]);registry.CACHE_FILE=registry.CACHE_DIR/'registry.json'
require(datapond.list()==['ice-reference'], "Smoke check failed")
con=datapond.connect('ice-reference',quiet=True)
try:
    con.execute("SET memory_limit='128MiB'");con.execute('SET threads=1');con.execute("SET max_temp_directory_size='0B'")
    for table,expected in {'facilities': 878, 'offices': 275, 'aor': 26, 'county_aor': 3231}.items():
        require(con.execute('SELECT count(*) FROM "'+table+'"').fetchone()[0]==expected, "Smoke check failed")
    require(con.execute('SELECT count(*) FROM _metadata').fetchone()[0]==4, "Smoke check failed")
    for sql,expected in [('SELECT count(*) FROM facilities WHERE detention_facility_code IS NULL', 1), ("SELECT count(*) FROM aor WHERE ST_AsText(ST_GeomFromWKB(geometry_wkb)) LIKE '%EMPTY'", 1), ("SELECT count(*) FROM county_aor WHERE ST_AsText(ST_GeomFromWKB(geometry_wkb)) LIKE '%EMPTY'", 1), ('SELECT count(*) FROM offices WHERE latitude IS NULL AND longitude IS NULL', 5)]:require(con.execute(sql).fetchone()[0]==expected, "Smoke check failed")
    example=con.execute('SELECT state, count(*) AS facilities FROM facilities GROUP BY state ORDER BY facilities DESC, state LIMIT 5').fetchall()
    print(json.dumps({'passed':True,'client':'Python datapond','version':importlib.metadata.version('datapond'),'duckdb':duckdb.__version__,'example':example},default=str))
finally:con.close()
