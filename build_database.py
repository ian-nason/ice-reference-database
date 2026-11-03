"""Build a source-preserving frozen ICE companion; no overwrite or publication."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,os,shutil,tempfile,threading,time
import duckdb
from build_safety import require,refuse_existing,check_budget
from datapond_build import ensure_metadata,build_columns_table
REPO=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path)
parser.add_argument('--validate-only',action='store_true')
parser.add_argument('--report',type=Path,help='New validation-only JSON path; existing files are refused')
args=parser.parse_args()
args.dataset='reference'
name='ice-reference'
OUTPUT=(args.output or REPO/(name+'.duckdb')).resolve()
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
REPORT=(args.report or REPO/'validation-only.json').resolve()
require(args.validate_only or args.report is None,'--report applies only to --validate-only')
if args.validate_only and (REPORT.exists() or REPORT.is_symlink()):raise FileExistsError(REPORT)
RESERVE=512*1024**2
BUDGET=(128 if args.dataset=='reference' else 32)*1024**2
CONFIG={'memory_limit':'128MiB','threads':'1','max_temp_directory_size':'0B','preserve_insertion_order':'true','autoinstall_known_extensions':'false'}
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(1024**2),b''):h.update(b)
    return h.hexdigest()
def q(name):return '"'+name.replace('"','""')+'"'
tables=json.loads((REPO/'source-lock.json').read_text())['tables']
for item in tables:item['path']=REPO/item['local_path']
for item in tables:
    require(item['path'].stat().st_size==item['bytes'] and digest(item['path'])==item['sha256'],f'Pinned source integrity failed: {item["path"]}')
if not args.validate_only:
    refuse_existing(OUTPUT)
    if shutil.disk_usage(OUTPUT.parent).free < RESERVE+BUDGET:raise RuntimeError(f'Require {RESERVE+BUDGET:,} free bytes for reserve plus measured small-build budget')
    WORK=Path(tempfile.mkdtemp(prefix='.'+name+'-build-',dir=OUTPUT.parent));working_output=WORK/OUTPUT.name
else:WORK=None;working_output=':memory:'
con=duckdb.connect(str(working_output),config=CONFIG)
# Preserve older GeoParquet 0.1.0 WKB without invoking the modern metadata
# decoder. Original metadata is copied verbatim; no CRS is relabelled.
con.execute('SET enable_geoparquet_conversion=false')
stop=threading.Event();budget_errors=[]
def monitor():
    while not stop.wait(.1):
        try:
            if WORK:check_budget(WORK,OUTPUT.parent,BUDGET,RESERVE)
        except Exception as error:
            budget_errors.append(str(error));con.interrupt();return
watch=threading.Thread(target=monitor,daemon=True);watch.start()
report={'dataset':name,'built_utc':datetime.now(timezone.utc).isoformat(),'validate_only':args.validate_only,'config':CONFIG,'physical_free_before':shutil.disk_usage(OUTPUT.parent).free,'reserve_bytes':RESERVE,'working_budget_bytes':BUDGET,'tables':{},'source_hashes_verified':True,'duckdb':duckdb.__version__}
try:
    con.execute('CREATE TABLE _provenance(table_name VARCHAR,source_url VARCHAR,source_commit VARCHAR,source_member VARCHAR,sha256 VARCHAR,source_bytes BIGINT,license VARCHAR)')
    con.execute('CREATE TABLE _geometry_metadata(table_name VARCHAR,metadata_key VARCHAR,metadata_value VARCHAR)')
    for item in tables:
        table=item['table'];path=item['path'];source=item['source']
        schema=con.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(path)]).fetchall();source_columns=[x[0] for x in schema]
        if 'geometry' in source_columns:
            geometry_type=next(x[1] for x in schema if x[0]=='geometry')
            geometry_expr='ST_AsWKB(geometry)::BLOB' if geometry_type.startswith('GEOMETRY') else 'geometry'
            select='* EXCLUDE(geometry),'+geometry_expr+' AS geometry_wkb'
        else:select='*'
        ordinal_select=select.replace('* EXCLUDE(geometry)','* EXCLUDE(geometry,file_row_number)') if 'geometry' in source_columns else '* EXCLUDE(file_row_number)'
        source_query=f'SELECT file_row_number+1 AS _source_row,{ordinal_select} FROM read_parquet(?,file_row_number=true)'
        con.execute(f'CREATE TABLE {q(table)} AS '+source_query,[str(path)])
        actual=con.execute(f'SELECT count(*) FROM {q(table)}').fetchone()[0];require(actual==item['rows'],f'Wrong row count for {table}: {actual}')
        diff=con.execute(f'''SELECT count(*) FROM ((SELECT * EXCLUDE(_source_row) FROM {q(table)} EXCEPT ALL SELECT {select} FROM read_parquet(?)) UNION ALL (SELECT {select} FROM read_parquet(?) EXCEPT ALL SELECT * EXCLUDE(_source_row) FROM {q(table)}))''',[str(path)]*2).fetchone()[0];require(diff==0,f'Source equality failed for {table}')
        ordinal_diff=con.execute(f'SELECT count(*) FROM ((SELECT * FROM {q(table)} EXCEPT ALL {source_query}) UNION ALL ({source_query} EXCEPT ALL SELECT * FROM {q(table)}))',[str(path)]*2).fetchone()[0]
        require(ordinal_diff==0,f'Source ordinal/value equality failed for {table}')
        con.execute('INSERT INTO _provenance VALUES (?,?,?,?,?,?,?)',[table,source['url'],source['commit'],item['file'],item['sha256'],item['bytes'],'CC0-1.0 data; upstream code not copied'])
        if 'geometry' in source_columns:
            for _,key,value in con.execute('SELECT * FROM parquet_kv_metadata(?)',[str(path)]).fetchall():con.execute('INSERT INTO _geometry_metadata VALUES (?,?,?)',[table,key.decode(),value.decode()])
        cols=con.execute(f'DESCRIBE {q(table)}').fetchall()
        nulls={col:con.execute(f'SELECT count(*) FILTER(WHERE {q(col)} IS NULL) FROM {q(table)}').fetchone()[0] for col,*_ in cols}
        entry={'rows':actual,'schema':cols,'null_counts':nulls,'source_equality_differences':diff,'source_ordinal_differences':ordinal_diff,'unit':item['unit'],'temporal_semantics':item['temporal_semantics'],'candidate_key':item.get('candidate_keys_from_parser')}
        if entry['candidate_key']:
            keys=','.join(q(k) for k in entry['candidate_key']);entry['duplicate_key_groups']=con.execute(f'SELECT count(*) FROM (SELECT {keys} FROM {q(table)} GROUP BY {keys} HAVING count(*)>1)').fetchone()[0]
        if 'geometry' in source_columns:
            entry['empty_geometry']=con.execute(f"SELECT count(*) FROM {q(table)} WHERE ST_AsText(ST_GeomFromWKB(geometry_wkb)) LIKE '%EMPTY'").fetchone()[0]
            entry['wkb_roundtrip_differences']=con.execute(f'SELECT count(*) FROM {q(table)} WHERE ST_AsWKB(ST_GeomFromWKB(geometry_wkb))::BLOB<>geometry_wkb').fetchone()[0]
            require(entry['wkb_roundtrip_differences']==0,f'WKB roundtrip failed for {table}')
        date_columns=[col for col,type,*_ in cols if type=='DATE']
        entry['date_ranges']={col:con.execute(f'SELECT min({q(col)}),max({q(col)}) FROM {q(table)}').fetchone() for col in date_columns}
        if 'file_date' in source_columns and 'pull_date' in source_columns:entry['file_before_pull_rows']=con.execute(f'SELECT count(*) FROM {q(table)} WHERE file_date<pull_date').fetchone()[0]
        if table=='facilities' and args.dataset=='reference':
            entry['duplicate_nonnull_facility_codes']=con.execute('SELECT count(*) FROM (SELECT detention_facility_code FROM facilities WHERE detention_facility_code IS NOT NULL GROUP BY 1 HAVING count(*)>1)').fetchone()[0]
        if table=='county_aor':entry['duplicate_nonnull_geoids']=con.execute('SELECT count(*) FROM (SELECT GEOID FROM county_aor WHERE GEOID IS NOT NULL GROUP BY 1 HAVING count(*)>1)').fetchone()[0]
        if 'latitude' in source_columns:
            entry['coordinate_range_errors']=con.execute(f'SELECT count(*) FROM {q(table)} WHERE latitude NOT BETWEEN -90 AND 90 OR longitude NOT BETWEEN -180 AND 180 OR (latitude IS NULL)<>(longitude IS NULL)').fetchone()[0]
            require(entry['coordinate_range_errors']==0,f'Invalid coordinates in {table}')
        if table=='dtm_currently_detained_by_criminality':
            comparisons,mismatches=con.execute('''SELECT count(*),count(*) FILTER(WHERE abs(x.share_of_total-x.n_detained/t.n_detained)>0.005) FROM dtm_currently_detained_by_criminality x JOIN dtm_currently_detained_by_criminality t ON x.pull_date=t.pull_date AND x.criminality=t.criminality WHERE t.arresting_agency='Total' AND x.share_of_total IS NOT NULL AND t.n_detained>0''').fetchone()
            entry['share_denominator_comparisons']=comparisons;entry['share_denominator_mismatches']=mismatches
            require(comparisons==1024 and mismatches==0,'Criminality-category share denominator check failed')
        report['tables'][table]=entry
        if budget_errors:raise RuntimeError('Physical disk budget exceeded')
    descriptions={i['table']:i['unit']+'; '+i['temporal_semantics'] for i in tables}
    ensure_metadata(con,tables=list(descriptions),descriptions=descriptions,source_url='https://deportationdata.org/data/processed/ice.html',license='CC0-1.0 data')
    build_columns_table(con,tables=list(descriptions),join_hints={'_source_row':'Ordinal within the pinned source member, not an entity identifier across releases.','geometry_wkb':'Source WKB; office/AOR CRS is NAD83 EPSG:4269. Metadata in _geometry_metadata.','detention_facility_code':'Source code, possibly NULL; historical joins require coverage checks.','pull_date':'Source extract date; snapshot series cannot be summed across pulls.','file_date':'Source-derived workbook release date, distinct from the observation period and repository commit.','share_of_total':'Arresting-agency share of the combined ICE+CBP population within the same criminality category and pull_date; source rounding retained.'})
    if not args.validate_only:con.execute('CHECKPOINT')
finally:
    stop.set();watch.join(timeout=2);con.close()
if budget_errors:raise RuntimeError(str(budget_errors))
report['status']='passed source-preserving ingestion; source anomalies retained for review'
report['physical_free_after']=shutil.disk_usage(OUTPUT.parent).free
if not args.validate_only:
    check_budget(WORK,OUTPUT.parent,BUDGET,RESERVE)
    report['database_bytes']=working_output.stat().st_size;report['database_sha256']=digest(working_output)
    report['final_budget_check']=check_budget(WORK,OUTPUT.parent,BUDGET,RESERVE)
    refuse_existing(OUTPUT)
    os.link(working_output,OUTPUT)
    with OUTPUT.with_suffix('.manifest.json').open('x') as f:json.dump(report,f,indent=2,default=str)
else:
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    with REPORT.open('x') as f:json.dump(report,f,indent=2,default=str)
print(json.dumps({'dataset':name,'rows':sum(x['rows'] for x in report['tables'].values()),'tables':len(tables),'database_bytes':report.get('database_bytes'),'database_sha256':report.get('database_sha256'),'duplicate_key_groups':{k:v['duplicate_key_groups'] for k,v in report['tables'].items() if v.get('duplicate_key_groups')},'file_before_pull_rows':{k:v['file_before_pull_rows'] for k,v in report['tables'].items() if v.get('file_before_pull_rows')},'free_after':report['physical_free_after']},indent=2))
