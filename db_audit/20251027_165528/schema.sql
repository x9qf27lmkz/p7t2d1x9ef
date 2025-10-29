--
-- PostgreSQL database dump
--

\restrict BO2LMOViZvohigMvElZlUaQVZYjswBTKnTimWqq3A8I4CpK6T2kg6rvRfnHVlp2

-- Dumped from database version 16.10 (Ubuntu 16.10-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.10 (Ubuntu 16.10-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- Name: classify_aptinfo_use(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.classify_aptinfo_use(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE
           WHEN txt IN ('아파트','도시형 생활주택(아파트)','주상복합') THEN 'APT_FAMILY'
           WHEN txt IN ('연립주택') THEN 'MULTI_FAMILY'
           WHEN txt IN ('도시형 생활주택(주상복합)') THEN 'MIXED'
           ELSE NULL
         END;
$$;


ALTER FUNCTION public.classify_aptinfo_use(txt text) OWNER TO homuser;

--
-- Name: clean_lot(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.clean_lot(p text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
  SELECT NULLIF(regexp_replace(p, '[^0-9\-]', '', 'g'), '');
$$;


ALTER FUNCTION public.clean_lot(p text) OWNER TO homuser;

--
-- Name: ltrim_zeros(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.ltrim_zeros(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE
           WHEN txt IS NULL THEN NULL
           ELSE NULLIF(regexp_replace(txt, '^0+', ''),'')
         END;
$$;


ALTER FUNCTION public.ltrim_zeros(txt text) OWNER TO homuser;

--
-- Name: mk_join3(text, text, text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.mk_join3(gu text, dong text, lot text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE
           WHEN safe_key(lot) IS NULL THEN NULL
           ELSE lower(coalesce(gu,'')) || '|' || lower(coalesce(dong,'')) || '|' || lower(safe_key(lot))
         END
$$;


ALTER FUNCTION public.mk_join3(gu text, dong text, lot text) OWNER TO homuser;

--
-- Name: norm_dong_safe(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.norm_dong_safe(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE
           WHEN txt IS NULL THEN NULL
           ELSE lower(regexp_replace(txt, '\s+', '', 'g'))
         END;
$$;


ALTER FUNCTION public.norm_dong_safe(txt text) OWNER TO homuser;

--
-- Name: norm_lot(text, text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.norm_lot(mno text, sno text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE
           WHEN coalesce(mno,'') = '' THEN NULL
           WHEN coalesce(sno,'') = '' THEN regexp_replace(mno, '^0+', '')
           ELSE regexp_replace(mno, '^0+', '') || '-' || regexp_replace(sno, '^0+', '')
         END;
$$;


ALTER FUNCTION public.norm_lot(mno text, sno text) OWNER TO homuser;

--
-- Name: norm_lot_key(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.norm_lot_key(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
  SELECT CASE
           WHEN txt IS NULL OR btrim(txt) = '' THEN NULL
           WHEN txt ~ '^[0-9]+-[0-9]+$'
             THEN regexp_replace(split_part(txt,'-',1), '^0+', '') || '-' ||
                  regexp_replace(split_part(txt,'-',2), '^0+', '')
           WHEN txt ~ '^[0-9]+$'
             THEN regexp_replace(txt, '^0+', '')
           ELSE txt
         END;
$_$;


ALTER FUNCTION public.norm_lot_key(txt text) OWNER TO homuser;

--
-- Name: norm_name_safe(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.norm_name_safe(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
  SELECT CASE
           WHEN txt IS NULL THEN NULL
           ELSE lower(
                  regexp_replace(
                    regexp_replace(
                      regexp_replace(txt, '\(.*?\)', '', 'g'),
                      '(아파트|단지)$', '', 'g'
                    ),
                    '\s+', '', 'g'
                  )
                )
         END;
$_$;


ALTER FUNCTION public.norm_name_safe(txt text) OWNER TO homuser;

--
-- Name: norm_text(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.norm_text(p text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT
    AS $$
  SELECT lower(regexp_replace(trim(p), '\s+', '', 'g'));
$$;


ALTER FUNCTION public.norm_text(p text) OWNER TO homuser;

--
-- Name: norm_txt(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.norm_txt(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE WHEN txt IS NULL THEN NULL
              ELSE lower(regexp_replace(txt, '\s+', '', 'g'))
         END;
$$;


ALTER FUNCTION public.norm_txt(txt text) OWNER TO homuser;

--
-- Name: normalize_lot_text(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.normalize_lot_text(lot text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE
    WHEN safe_key(lot) IS NULL THEN NULL
    ELSE
      COALESCE(ltrim_zeros(split_part(lot,'-',1)),'')
      || CASE WHEN ltrim_zeros(NULLIF(split_part(lot,'-',2),'')) IS NULL
              THEN '' ELSE '-'||ltrim_zeros(split_part(lot,'-',2)) END
  END;
$$;


ALTER FUNCTION public.normalize_lot_text(lot text) OWNER TO homuser;

--
-- Name: safe_key(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.safe_key(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE
           WHEN txt IS NULL THEN NULL
           WHEN btrim(txt) = '' THEN NULL
           WHEN lower(btrim(txt)) IN ('null') THEN NULL
           ELSE btrim(txt)
         END;
$$;


ALTER FUNCTION public.safe_key(txt text) OWNER TO homuser;

--
-- Name: sanitize_name_key(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.sanitize_name_key(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $_$
  SELECT CASE
           WHEN txt IS NULL THEN NULL
           WHEN txt ~ '^[()0-9\-]+$' THEN NULL
           ELSE txt
         END;
$_$;


ALTER FUNCTION public.sanitize_name_key(txt text) OWNER TO homuser;

--
-- Name: strip_brackets(text); Type: FUNCTION; Schema: public; Owner: homuser
--

CREATE FUNCTION public.strip_brackets(txt text) RETURNS text
    LANGUAGE sql IMMUTABLE
    AS $$
  SELECT CASE WHEN txt IS NULL THEN NULL
              ELSE replace(replace(txt,'[',''),']','') END;
$$;


ALTER FUNCTION public.strip_brackets(txt text) OWNER TO homuser;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: homuser
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO homuser;

--
-- Name: aptinfo; Type: TABLE; Schema: public; Owner: homuser
--

CREATE TABLE public.aptinfo (
    apt_cd text NOT NULL,
    sn integer,
    apt_nm text,
    cmpx_clsf text,
    apt_stdg_addr text,
    apt_rdn_addr text,
    ctpv_addr text,
    sgg_addr text,
    emd_addr text,
    daddr text,
    rdn_addr text,
    road_daddr text,
    telno text,
    fxno text,
    apt_cmpx text,
    apt_atch_file text,
    hh_type text,
    mng_mthd text,
    road_type text,
    mn_mthd text,
    whol_dong_cnt integer,
    tnohsh integer,
    bldr text,
    dvlr text,
    use_aprv_ymd date,
    gfa numeric(14,2),
    rsdt_xuar numeric(14,2),
    mnco_levy_area numeric(14,2),
    xuar_hh_stts60 numeric(14,2),
    xuar_hh_stts85 numeric(14,2),
    xuar_hh_stts135 numeric(14,2),
    xuar_hh_stts136 numeric(14,2),
    hmpg text,
    reg_ymd date,
    mdfcn_ymd date,
    epis_mng_no text,
    eps_mng_form text,
    hh_elct_ctrt_mthd text,
    clng_mng_form text,
    bdar numeric(14,2),
    prk_cntom integer,
    se_cd text,
    cmpx_aprv_day date,
    use_yn text,
    mnco_uld_yn text,
    lng numeric(10,7),
    lat numeric(10,7),
    cmpx_apld_day date,
    gu_key text,
    dong_key text,
    name_key text,
    lot_key text,
    raw jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.aptinfo OWNER TO homuser;

--
-- Name: aptinfo_ext; Type: TABLE; Schema: public; Owner: homuser
--

CREATE TABLE public.aptinfo_ext (
    apt_cd text NOT NULL,
    sn integer,
    apt_nm text,
    cmpx_clsf text,
    apt_stdg_addr text,
    apt_rdn_addr text,
    ctpv_addr text,
    sgg_addr text,
    emd_addr text,
    daddr text,
    rdn_addr text,
    road_daddr text,
    telno text,
    fxno text,
    apt_cmpx text,
    apt_atch_file text,
    hh_type text,
    mng_mthd text,
    road_type text,
    mn_mthd text,
    whol_dong_cnt integer,
    tnohsh integer,
    bldr text,
    dvlr text,
    use_aprv_ymd date,
    gfa numeric(14,2),
    rsdt_xuar numeric(14,2),
    mnco_levy_area numeric(14,2),
    xuar_hh_stts60 numeric(14,2),
    xuar_hh_stts85 numeric(14,2),
    xuar_hh_stts135 numeric(14,2),
    xuar_hh_stts136 numeric(14,2),
    hmpg text,
    reg_ymd date,
    mdfcn_ymd date,
    epis_mng_no text,
    eps_mng_form text,
    hh_elct_ctrt_mthd text,
    clng_mng_form text,
    bdar numeric(14,2),
    prk_cntom integer,
    se_cd text,
    cmpx_aprv_day date,
    use_yn text,
    mnco_uld_yn text,
    lng numeric(10,7),
    lat numeric(10,7),
    cmpx_apld_day date,
    gu_key text,
    dong_key text,
    name_key text,
    lot_key text,
    raw jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    lot_addr text,
    lot_main integer,
    lot_sub integer,
    lot_union text,
    sale84_med_3m numeric,
    sale84_med_6m numeric,
    sale84_med_12m numeric,
    rent84_med_3m numeric,
    rent84_med_6m numeric,
    rent84_med_12m numeric,
    sale84_med_1w numeric,
    sale84_med_1m numeric,
    sale84_med_24m numeric,
    sale84_med_36m numeric,
    rent84_med_1w numeric,
    rent84_med_1m numeric,
    rent84_med_24m numeric,
    rent84_med_36m numeric,
    sale_tx_cnt_1w integer,
    sale_tx_cnt_1m integer,
    sale_tx_cnt_3m integer,
    sale_tx_cnt_6m integer,
    sale_tx_cnt_12m integer,
    sale_tx_cnt_24m integer,
    sale_tx_cnt_36m integer,
    rent_tx_cnt_1w integer,
    rent_tx_cnt_1m integer,
    rent_tx_cnt_3m integer,
    rent_tx_cnt_6m integer,
    rent_tx_cnt_12m integer,
    rent_tx_cnt_24m integer,
    rent_tx_cnt_36m integer
);


ALTER TABLE public.aptinfo_ext OWNER TO homuser;

--
-- Name: aptinfo_ext_v; Type: VIEW; Schema: public; Owner: homuser
--

CREATE VIEW public.aptinfo_ext_v AS
 SELECT apt_cd,
    apt_nm,
    replace(lot_addr, ' '::text, ''::text) AS lot_addr_nospace
   FROM public.aptinfo_ext a
  WHERE (lot_addr IS NOT NULL);


ALTER VIEW public.aptinfo_ext_v OWNER TO homuser;

--
-- Name: rent; Type: TABLE; Schema: public; Owner: homuser
--

CREATE TABLE public.rent (
    id bigint NOT NULL,
    rcpt_yr integer,
    cgg_cd text,
    cgg_nm text,
    stdg_cd text,
    stdg_nm text,
    lotno_se text,
    lotno_se_nm text,
    mno text,
    sno text,
    flr integer,
    ctrt_day text,
    rent_se text,
    rent_area numeric(10,2),
    grfe_mwon bigint,
    rtfe_mwon bigint,
    bldg_nm text,
    arch_yr integer,
    bldg_usg text,
    ctrt_prd text,
    new_updt_yn text,
    ctrt_updt_use_yn text,
    bfr_grfe_mwon bigint,
    bfr_rtfe_mwon bigint,
    contract_date date,
    area_m2 numeric(10,2),
    deposit_krw bigint,
    rent_krw bigint,
    lot_key text,
    gu_key text,
    dong_key text,
    name_key text,
    lat numeric(10,7),
    lng numeric(10,7),
    raw jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.rent OWNER TO homuser;

--
-- Name: rent_id_seq; Type: SEQUENCE; Schema: public; Owner: homuser
--

CREATE SEQUENCE public.rent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.rent_id_seq OWNER TO homuser;

--
-- Name: rent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: homuser
--

ALTER SEQUENCE public.rent_id_seq OWNED BY public.rent.id;


--
-- Name: rent_mv; Type: MATERIALIZED VIEW; Schema: public; Owner: homuser
--

CREATE MATERIALIZED VIEW public.rent_mv AS
 WITH base AS (
         SELECT r.id,
            r.rcpt_yr,
            r.cgg_cd,
            r.cgg_nm,
            r.stdg_cd,
            r.stdg_nm,
            r.lotno_se,
            r.lotno_se_nm,
            r.mno,
            r.sno,
            r.flr,
            r.ctrt_day,
            r.rent_se,
            r.rent_area,
            r.grfe_mwon,
            r.rtfe_mwon,
            r.bldg_nm,
            r.arch_yr,
            r.bldg_usg,
            r.ctrt_prd,
            r.new_updt_yn,
            r.ctrt_updt_use_yn,
            r.bfr_grfe_mwon,
            r.bfr_rtfe_mwon,
            r.contract_date,
            r.area_m2,
            r.deposit_krw,
            r.rent_krw,
            r.lot_key,
            r.gu_key,
            r.dong_key,
            r.name_key,
            r.lat,
            r.lng,
            r.raw,
            r.created_at,
            r.updated_at,
            (NULLIF(regexp_replace(r.mno, '\D'::text, ''::text, 'g'::text), ''::text))::integer AS lot_main_i,
            (NULLIF(regexp_replace(r.sno, '\D'::text, ''::text, 'g'::text), ''::text))::integer AS lot_sub_i
           FROM public.rent r
        ), addr AS (
         SELECT b.id,
            b.rcpt_yr,
            b.cgg_cd,
            b.cgg_nm,
            b.stdg_cd,
            b.stdg_nm,
            b.lotno_se,
            b.lotno_se_nm,
            b.mno,
            b.sno,
            b.flr,
            b.ctrt_day,
            b.rent_se,
            b.rent_area,
            b.grfe_mwon,
            b.rtfe_mwon,
            b.bldg_nm,
            b.arch_yr,
            b.bldg_usg,
            b.ctrt_prd,
            b.new_updt_yn,
            b.ctrt_updt_use_yn,
            b.bfr_grfe_mwon,
            b.bfr_rtfe_mwon,
            b.contract_date,
            b.area_m2,
            b.deposit_krw,
            b.rent_krw,
            b.lot_key,
            b.gu_key,
            b.dong_key,
            b.name_key,
            b.lat,
            b.lng,
            b.raw,
            b.created_at,
            b.updated_at,
            b.lot_main_i,
            b.lot_sub_i,
                CASE
                    WHEN ((b.lot_sub_i IS NULL) OR (b.lot_sub_i = 0)) THEN (b.lot_main_i)::text
                    ELSE (((b.lot_main_i)::text || '-'::text) || (b.lot_sub_i)::text)
                END AS lot_pair,
            replace(((b.dong_key || ' '::text) ||
                CASE
                    WHEN ((b.lot_sub_i IS NULL) OR (b.lot_sub_i = 0)) THEN (b.lot_main_i)::text
                    ELSE (((b.lot_main_i)::text || '-'::text) || (b.lot_sub_i)::text)
                END), ' '::text, ''::text) AS lot_addr_nospace
           FROM base b
        )
 SELECT a.id,
    a.rcpt_yr,
    a.cgg_cd,
    a.cgg_nm,
    a.stdg_cd,
    a.stdg_nm,
    a.lotno_se,
    a.lotno_se_nm,
    a.mno,
    a.sno,
    a.flr,
    a.ctrt_day,
    a.rent_se,
    a.rent_area,
    a.grfe_mwon,
    a.rtfe_mwon,
    a.bldg_nm,
    a.arch_yr,
    a.bldg_usg,
    a.ctrt_prd,
    a.new_updt_yn,
    a.ctrt_updt_use_yn,
    a.bfr_grfe_mwon,
    a.bfr_rtfe_mwon,
    a.contract_date,
    a.area_m2,
    a.deposit_krw,
    a.rent_krw,
    a.lot_key,
    a.gu_key,
    a.dong_key,
    a.name_key,
    a.lat,
    a.lng,
    a.raw,
    a.created_at,
    a.updated_at,
    a.lot_main_i,
    a.lot_sub_i,
    a.lot_pair,
    a.lot_addr_nospace,
    v.apt_cd,
    v.apt_nm,
        CASE
            WHEN (v.apt_cd IS NULL) THEN 'NONE'::text
            ELSE 'MATCH'::text
        END AS match_status
   FROM (addr a
     LEFT JOIN public.aptinfo_ext_v v ON ((a.lot_addr_nospace = v.lot_addr_nospace)))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.rent_mv OWNER TO homuser;

--
-- Name: sale; Type: TABLE; Schema: public; Owner: homuser
--

CREATE TABLE public.sale (
    id bigint NOT NULL,
    raw jsonb NOT NULL,
    rcpt_yr integer,
    cgg_cd integer,
    cgg_nm text,
    stdg_cd integer,
    stdg_nm text,
    lotno_se integer,
    lotno_se_nm text,
    mno text,
    sno text,
    bldg_nm text,
    ctrt_day date,
    thing_amt bigint,
    arch_area numeric(14,3),
    land_area numeric(14,3),
    flr text,
    rght_se text,
    rtrcn_day text,
    arch_yr integer,
    bldg_usg text,
    dclr_se text,
    opbiz_restagnt_sgg_nm text,
    lat numeric(10,7),
    lng numeric(10,7),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    gu_key text,
    dong_key text,
    name_key text,
    lot_key text
);


ALTER TABLE public.sale OWNER TO homuser;

--
-- Name: COLUMN sale.rcpt_yr; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.rcpt_yr IS '접수연도';


--
-- Name: COLUMN sale.cgg_cd; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.cgg_cd IS '자치구코드';


--
-- Name: COLUMN sale.cgg_nm; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.cgg_nm IS '자치구명';


--
-- Name: COLUMN sale.stdg_cd; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.stdg_cd IS '법정동코드';


--
-- Name: COLUMN sale.stdg_nm; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.stdg_nm IS '법정동명';


--
-- Name: COLUMN sale.lotno_se; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.lotno_se IS '지번구분';


--
-- Name: COLUMN sale.lotno_se_nm; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.lotno_se_nm IS '지번구분명';


--
-- Name: COLUMN sale.mno; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.mno IS '본번';


--
-- Name: COLUMN sale.sno; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.sno IS '부번';


--
-- Name: COLUMN sale.bldg_nm; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.bldg_nm IS '건물명';


--
-- Name: COLUMN sale.ctrt_day; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.ctrt_day IS '계약일';


--
-- Name: COLUMN sale.thing_amt; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.thing_amt IS '물건금액(만원)';


--
-- Name: COLUMN sale.arch_area; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.arch_area IS '건물면적(㎡)';


--
-- Name: COLUMN sale.land_area; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.land_area IS '토지면적(㎡)';


--
-- Name: COLUMN sale.flr; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.flr IS '층';


--
-- Name: COLUMN sale.rght_se; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.rght_se IS '권리구분';


--
-- Name: COLUMN sale.rtrcn_day; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.rtrcn_day IS '취소일';


--
-- Name: COLUMN sale.arch_yr; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.arch_yr IS '건축년도';


--
-- Name: COLUMN sale.bldg_usg; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.bldg_usg IS '건물용도';


--
-- Name: COLUMN sale.dclr_se; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.dclr_se IS '신고구분';


--
-- Name: COLUMN sale.opbiz_restagnt_sgg_nm; Type: COMMENT; Schema: public; Owner: homuser
--

COMMENT ON COLUMN public.sale.opbiz_restagnt_sgg_nm IS '신고한 개업공인중개사 시군구명';


--
-- Name: sale_id_seq; Type: SEQUENCE; Schema: public; Owner: homuser
--

CREATE SEQUENCE public.sale_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sale_id_seq OWNER TO homuser;

--
-- Name: sale_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: homuser
--

ALTER SEQUENCE public.sale_id_seq OWNED BY public.sale.id;


--
-- Name: sale_mv; Type: MATERIALIZED VIEW; Schema: public; Owner: homuser
--

CREATE MATERIALIZED VIEW public.sale_mv AS
 WITH base AS (
         SELECT s.id,
            s.raw,
            s.rcpt_yr,
            s.cgg_cd,
            s.cgg_nm,
            s.stdg_cd,
            s.stdg_nm,
            s.lotno_se,
            s.lotno_se_nm,
            s.mno,
            s.sno,
            s.bldg_nm,
            s.ctrt_day,
            s.thing_amt,
            s.arch_area,
            s.land_area,
            s.flr,
            s.rght_se,
            s.rtrcn_day,
            s.arch_yr,
            s.bldg_usg,
            s.dclr_se,
            s.opbiz_restagnt_sgg_nm,
            s.lat,
            s.lng,
            s.created_at,
            s.updated_at,
            s.gu_key,
            s.dong_key,
            s.name_key,
            s.lot_key,
            (NULLIF(regexp_replace(s.mno, '\D'::text, ''::text, 'g'::text), ''::text))::integer AS lot_main_i,
            (NULLIF(regexp_replace(s.sno, '\D'::text, ''::text, 'g'::text), ''::text))::integer AS lot_sub_i
           FROM public.sale s
        ), addr AS (
         SELECT b.id,
            b.raw,
            b.rcpt_yr,
            b.cgg_cd,
            b.cgg_nm,
            b.stdg_cd,
            b.stdg_nm,
            b.lotno_se,
            b.lotno_se_nm,
            b.mno,
            b.sno,
            b.bldg_nm,
            b.ctrt_day,
            b.thing_amt,
            b.arch_area,
            b.land_area,
            b.flr,
            b.rght_se,
            b.rtrcn_day,
            b.arch_yr,
            b.bldg_usg,
            b.dclr_se,
            b.opbiz_restagnt_sgg_nm,
            b.lat,
            b.lng,
            b.created_at,
            b.updated_at,
            b.gu_key,
            b.dong_key,
            b.name_key,
            b.lot_key,
            b.lot_main_i,
            b.lot_sub_i,
                CASE
                    WHEN ((b.lot_sub_i IS NULL) OR (b.lot_sub_i = 0)) THEN (b.lot_main_i)::text
                    ELSE (((b.lot_main_i)::text || '-'::text) || (b.lot_sub_i)::text)
                END AS lot_pair,
            replace(((b.dong_key || ' '::text) ||
                CASE
                    WHEN ((b.lot_sub_i IS NULL) OR (b.lot_sub_i = 0)) THEN (b.lot_main_i)::text
                    ELSE (((b.lot_main_i)::text || '-'::text) || (b.lot_sub_i)::text)
                END), ' '::text, ''::text) AS lot_addr_nospace
           FROM base b
        )
 SELECT a.id,
    a.raw,
    a.rcpt_yr,
    a.cgg_cd,
    a.cgg_nm,
    a.stdg_cd,
    a.stdg_nm,
    a.lotno_se,
    a.lotno_se_nm,
    a.mno,
    a.sno,
    a.bldg_nm,
    a.ctrt_day,
    a.thing_amt,
    a.arch_area,
    a.land_area,
    a.flr,
    a.rght_se,
    a.rtrcn_day,
    a.arch_yr,
    a.bldg_usg,
    a.dclr_se,
    a.opbiz_restagnt_sgg_nm,
    a.lat,
    a.lng,
    a.created_at,
    a.updated_at,
    a.gu_key,
    a.dong_key,
    a.name_key,
    a.lot_key,
    a.lot_main_i,
    a.lot_sub_i,
    a.lot_pair,
    a.lot_addr_nospace,
    v.apt_cd,
    v.apt_nm,
        CASE
            WHEN (v.apt_cd IS NULL) THEN 'NONE'::text
            ELSE 'MATCH'::text
        END AS match_status
   FROM (addr a
     LEFT JOIN public.aptinfo_ext_v v ON ((a.lot_addr_nospace = v.lot_addr_nospace)))
  WITH NO DATA;


ALTER MATERIALIZED VIEW public.sale_mv OWNER TO homuser;

--
-- Name: v_apt_markers; Type: VIEW; Schema: public; Owner: homuser
--

CREATE VIEW public.v_apt_markers AS
 SELECT apt_cd AS id,
    COALESCE(apt_nm, name_key) AS name,
    (lat)::double precision AS lat,
    (lng)::double precision AS lng,
    sgg_addr AS gu,
    emd_addr AS dong,
    apt_rdn_addr AS addr_road,
    apt_stdg_addr AS addr_jibun
   FROM public.aptinfo
  WHERE ((use_yn = 'Y'::text) AND (lat IS NOT NULL) AND (lng IS NOT NULL) AND (COALESCE(apt_nm, name_key, ''::text) <> ''::text));


ALTER VIEW public.v_apt_markers OWNER TO homuser;

--
-- Name: rent id; Type: DEFAULT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.rent ALTER COLUMN id SET DEFAULT nextval('public.rent_id_seq'::regclass);


--
-- Name: sale id; Type: DEFAULT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.sale ALTER COLUMN id SET DEFAULT nextval('public.sale_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: aptinfo_ext aptinfo_ext_pkey; Type: CONSTRAINT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.aptinfo_ext
    ADD CONSTRAINT aptinfo_ext_pkey PRIMARY KEY (apt_cd);


--
-- Name: aptinfo aptinfo_pkey; Type: CONSTRAINT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.aptinfo
    ADD CONSTRAINT aptinfo_pkey PRIMARY KEY (apt_cd);


--
-- Name: rent rent_pkey; Type: CONSTRAINT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.rent
    ADD CONSTRAINT rent_pkey PRIMARY KEY (id);


--
-- Name: sale sale_pkey; Type: CONSTRAINT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.sale
    ADD CONSTRAINT sale_pkey PRIMARY KEY (id);


--
-- Name: aptinfo_ext_apt_nm_idx; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX aptinfo_ext_apt_nm_idx ON public.aptinfo_ext USING btree (apt_nm);


--
-- Name: aptinfo_ext_dong_key_idx; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX aptinfo_ext_dong_key_idx ON public.aptinfo_ext USING btree (dong_key);


--
-- Name: aptinfo_ext_gu_key_idx; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX aptinfo_ext_gu_key_idx ON public.aptinfo_ext USING btree (gu_key);


--
-- Name: aptinfo_ext_lot_key_idx; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX aptinfo_ext_lot_key_idx ON public.aptinfo_ext USING btree (lot_key);


--
-- Name: aptinfo_ext_name_key_idx; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX aptinfo_ext_name_key_idx ON public.aptinfo_ext USING btree (name_key);


--
-- Name: ix_aptinfo_apt_nm; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_apt_nm ON public.aptinfo USING btree (apt_nm);


--
-- Name: ix_aptinfo_dong_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_dong_key ON public.aptinfo USING btree (dong_key);


--
-- Name: ix_aptinfo_ext_aptcd; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_ext_aptcd ON public.aptinfo_ext USING btree (apt_cd);


--
-- Name: ix_aptinfo_ext_lotaddr_nospace; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_ext_lotaddr_nospace ON public.aptinfo_ext USING btree (replace(lot_addr, ' '::text, ''::text));


--
-- Name: ix_aptinfo_ext_lotaddr_null; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_ext_lotaddr_null ON public.aptinfo_ext USING btree (((lot_addr IS NULL))) WHERE (lot_addr IS NULL);


--
-- Name: ix_aptinfo_gu_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_gu_key ON public.aptinfo USING btree (gu_key);


--
-- Name: ix_aptinfo_lot_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_lot_key ON public.aptinfo USING btree (lot_key);


--
-- Name: ix_aptinfo_name_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_name_key ON public.aptinfo USING btree (name_key);


--
-- Name: ix_rent_cgg_nm; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_rent_cgg_nm ON public.rent USING btree (cgg_nm);


--
-- Name: ix_rent_contract_date; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_rent_contract_date ON public.rent USING btree (contract_date);


--
-- Name: ix_rent_lot_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_rent_lot_key ON public.rent USING btree (lot_key);


--
-- Name: ix_rent_mv_addr; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_rent_mv_addr ON public.rent_mv USING btree (lot_addr_nospace);


--
-- Name: ix_rent_mv_aptcd; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_rent_mv_aptcd ON public.rent_mv USING btree (apt_cd);


--
-- Name: ix_rent_name_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_rent_name_key ON public.rent USING btree (name_key);


--
-- Name: ix_rent_stdg_nm; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_rent_stdg_nm ON public.rent USING btree (stdg_nm);


--
-- Name: ix_sale_bldg_nm; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_bldg_nm ON public.sale USING btree (bldg_nm);


--
-- Name: ix_sale_cgg_nm; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_cgg_nm ON public.sale USING btree (cgg_nm);


--
-- Name: ix_sale_ctrt_day; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_ctrt_day ON public.sale USING btree (ctrt_day);


--
-- Name: ix_sale_dong_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_dong_key ON public.sale USING btree (dong_key);


--
-- Name: ix_sale_gu_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_gu_key ON public.sale USING btree (gu_key);


--
-- Name: ix_sale_lot_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_lot_key ON public.sale USING btree (lot_key);


--
-- Name: ix_sale_mv_addr; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_mv_addr ON public.sale_mv USING btree (lot_addr_nospace);


--
-- Name: ix_sale_mv_aptcd; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_mv_aptcd ON public.sale_mv USING btree (apt_cd);


--
-- Name: ix_sale_name_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_name_key ON public.sale USING btree (name_key);


--
-- Name: ix_sale_stdg_nm; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_stdg_nm ON public.sale USING btree (stdg_nm);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO homuser;


--
-- PostgreSQL database dump complete
--

\unrestrict BO2LMOViZvohigMvElZlUaQVZYjswBTKnTimWqq3A8I4CpK6T2kg6rvRfnHVlp2

