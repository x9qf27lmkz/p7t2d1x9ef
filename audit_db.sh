#!/usr/bin/env bash
set -euo pipefail

# ===== 연결 정보 (환경변수가 있으면 그 값을, 없으면 기본값을 사용) =====
: "${PGHOST:=127.0.0.1}"
: "${PGPORT:=5432}"
: "${PGDATABASE:=homesweethome}"
: "${PGUSER:=homuser}"          # <- 기존 homuser 오타 수정
: "${PGPASSWORD:=pass123}"

export PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="db_audit/${STAMP}"
mkdir -p "${OUT_DIR}"

echo "== DB Audit Start =="
echo "   target: ${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE}"
echo "   outdir: ${OUT_DIR}"
echo

# 공통 옵션 (pg_dump/psql 모두 명시적으로 host/port/user 지정)
PDUMP_OPTS=(-h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}")
PSQL_OPTS=(-h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -X -v ON_ERROR_STOP=1)

# [1/6] DDL 덤프
echo "[1/6] Dump DDL"
pg_dump "${PDUMP_OPTS[@]}" -s -n public            > "${OUT_DIR}/schema.sql"
# 코어 테이블만 별도
pg_dump "${PDUMP_OPTS[@]}" -s \
  -t public.aptinfo \
  -t public.rent   -t public.sale \
  -t public.aptinfo_ext \
  -t public.rent_ext -t public.sale_ext \
  > "${OUT_DIR}/schema_core.sql" 2>/dev/null || true

# [2/6] Columns (Markdown/CSV/JSON)
echo "[2/6] Columns (Markdown/CSV/JSON)"
psql "${PSQL_OPTS[@]}" -q <<'SQL' > __columns.md
\pset format unaligned
\pset tuples_only on
WITH cols AS (
  SELECT
    c.table_name,
    c.ordinal_position,
    c.column_name,
    c.data_type ||
      COALESCE('('||c.character_maximum_length||')','') ||
      CASE WHEN c.numeric_precision IS NOT NULL
           THEN '('||c.numeric_precision||COALESCE(','||c.numeric_scale,'')||')'
           ELSE '' END AS type,
    c.is_nullable,
    COALESCE(c.column_default,'') AS column_default,
    pgd.description AS comment
  FROM information_schema.columns c
  LEFT JOIN pg_catalog.pg_class     pc ON pc.relname = c.table_name
  LEFT JOIN pg_catalog.pg_namespace pn ON pn.nspname = c.table_schema AND pn.oid = pc.relnamespace
  LEFT JOIN pg_catalog.pg_attribute pa ON pa.attrelid = pc.oid AND pa.attname = c.column_name
  LEFT JOIN pg_catalog.pg_description pgd ON pgd.objoid = pc.oid AND pgd.objsubid = pa.attnum
  WHERE c.table_schema='public'
)
SELECT
'## '||table_name||E'\n'||
'| # | column | type | null | default | comment |'||E'\n'||
'|---|--------|------|------|---------|---------|'||E'\n'||
string_agg(
  '|'||ordinal_position||'|'||column_name||'|'||type||'|'||is_nullable||'|'||
  replace(column_default,'\n',' ')||'|'||COALESCE(replace(comment,'\n',' '),'')||'|'
, E'\n' ORDER BY ordinal_position)
||E'\n'
FROM cols
GROUP BY table_name
ORDER BY table_name;
SQL
mv __columns.md "${OUT_DIR}/columns.md"

psql "${PSQL_OPTS[@]}" -A -F, -P footer=off -c "
SELECT table_name, ordinal_position, column_name,
       data_type, character_maximum_length, numeric_precision, numeric_scale,
       is_nullable, column_default
FROM information_schema.columns
WHERE table_schema='public'
ORDER BY table_name, ordinal_position
" > "${OUT_DIR}/columns.csv"

psql "${PSQL_OPTS[@]}" -q <<'SQL' > "${OUT_DIR}/columns.json"
WITH cols AS (
  SELECT
    c.table_name, c.column_name, c.ordinal_position,
    c.data_type, c.character_maximum_length, c.numeric_precision, c.numeric_scale,
    c.is_nullable, c.column_default
  FROM information_schema.columns c
  WHERE c.table_schema='public'
),
j AS (
  SELECT table_name,
         jsonb_agg(jsonb_build_object(
           'position', ordinal_position,
           'name', column_name,
           'data_type', data_type,
           'char_len', character_maximum_length,
           'num_precision', numeric_precision,
           'num_scale', numeric_scale,
           'nullable', is_nullable,
           'default', column_default
         ) ORDER BY ordinal_position) AS columns
  FROM cols
  GROUP BY table_name
)
SELECT jsonb_pretty(jsonb_object_agg(table_name, columns ORDER BY table_name))
FROM j;
SQL

# [3/6] Indexes / Constraints
echo "[3/6] Indexes"
psql "${PSQL_OPTS[@]}" -q <<'SQL' > "${OUT_DIR}/indexes.md"
\pset format unaligned
\pset tuples_only on
SELECT
  '## '||relname||E'\n'||
  string_agg(idxdef, E'\n' ORDER BY idxdef)||E'\n'
FROM (
  SELECT c.relname, pg_get_indexdef(i.indexrelid) AS idxdef
  FROM   pg_class c
  JOIN   pg_namespace n ON n.oid = c.relnamespace AND n.nspname='public'
  JOIN   pg_index i     ON i.indrelid = c.oid
  WHERE  c.relkind='r'
) t
GROUP BY relname
ORDER BY relname;
SQL

echo "[3b/6] Constraints (PK/FK/UNIQUE/CHECK)"
psql "${PSQL_OPTS[@]}" -c "\copy (
  SELECT
    n.nspname   AS schema,
    c.relname   AS table,
    con.conname AS constraint,
    CASE con.contype
      WHEN 'p' THEN 'PRIMARY KEY'
      WHEN 'f' THEN 'FOREIGN KEY'
      WHEN 'u' THEN 'UNIQUE'
      WHEN 'c' THEN 'CHECK'
      ELSE con.contype::text
    END AS type,
    pg_get_constraintdef(con.oid) AS definition
  FROM pg_constraint con
  JOIN pg_class c ON c.oid = con.conrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname='public'
  ORDER BY c.relname, con.contype DESC, con.conname
) TO STDOUT WITH CSV HEADER" > "${OUT_DIR}/constraints.csv"

# [4/6] Table sizes
echo "[4/6] Table sizes"
psql "${PSQL_OPTS[@]}" -A -F ' | ' -P footer=off -c "
SELECT n.nspname AS schema, c.relname AS table,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
       COALESCE(to_char(reltuples, 'FM999999999999'), '0') AS row_estimate,
       pg_get_userbyid(c.relowner) AS owner
FROM pg_class c
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='r'
ORDER BY pg_total_relation_size(c.oid) DESC;
" > "${OUT_DIR}/tables_size.md"

# [5/6] Estimated row counts (quick view)
echo "[5/6] Estimated row counts"
psql "${PSQL_OPTS[@]}" -qAt -c "
SELECT relname, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
" > "${OUT_DIR}/row_counts.txt"

# [6/6] 요약 README
cat > "${OUT_DIR}/README.md" <<EOF
# DB Audit (${STAMP})

- target : ${PGUSER}@${PGHOST}:${PGPORT}/${PGDATABASE}
- files
  - schema.sql             : public 스키마 DDL 전체
  - schema_core.sql        : 핵심 테이블 DDL (있을 때만)
  - columns.md/csv/json    : 컬럼 정의
  - indexes.md             : 인덱스 정의
  - constraints.csv        : 제약조건(PK/FK/UNIQUE/CHECK)
  - tables_size.md         : 테이블 크기/소유/추정행수
  - row_counts.txt         : 추정 행수(통계 기반)
EOF

echo
echo "✅ Done. See ${OUT_DIR}"
