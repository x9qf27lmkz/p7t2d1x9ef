# DB Audit (20251028_215617)

- target : homuser@127.0.0.1:5432/homesweethome
- files
  - schema.sql             : public 스키마 DDL 전체
  - schema_core.sql        : 핵심 테이블 DDL (있을 때만)
  - columns.md/csv/json    : 컬럼 정의
  - indexes.md             : 인덱스 정의
  - constraints.csv        : 제약조건(PK/FK/UNIQUE/CHECK)
  - tables_size.md         : 테이블 크기/소유/추정행수
  - row_counts.txt         : 추정 행수(통계 기반)
