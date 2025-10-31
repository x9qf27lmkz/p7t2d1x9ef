--
-- PostgreSQL database dump
--

\restrict 22VhkbJurIG39PWd8rGHG2JcIqV5WRFBNASgdmQWDrKDZXmycCJCdf0s3cfBQfd

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

SET default_tablespace = '';

SET default_table_access_method = heap;

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
-- Name: rent id; Type: DEFAULT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.rent ALTER COLUMN id SET DEFAULT nextval('public.rent_id_seq'::regclass);


--
-- Name: sale id; Type: DEFAULT; Schema: public; Owner: homuser
--

ALTER TABLE ONLY public.sale ALTER COLUMN id SET DEFAULT nextval('public.sale_id_seq'::regclass);


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
-- Name: ix_aptinfo_apt_nm; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_apt_nm ON public.aptinfo USING btree (apt_nm);


--
-- Name: ix_aptinfo_dong_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_aptinfo_dong_key ON public.aptinfo USING btree (dong_key);


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
-- Name: ix_sale_name_key; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_name_key ON public.sale USING btree (name_key);


--
-- Name: ix_sale_stdg_nm; Type: INDEX; Schema: public; Owner: homuser
--

CREATE INDEX ix_sale_stdg_nm ON public.sale USING btree (stdg_nm);


--
-- PostgreSQL database dump complete
--

\unrestrict 22VhkbJurIG39PWd8rGHG2JcIqV5WRFBNASgdmQWDrKDZXmycCJCdf0s3cfBQfd

