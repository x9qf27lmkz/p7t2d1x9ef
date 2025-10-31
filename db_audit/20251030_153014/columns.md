## adm_emd
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|emd_cd|text|YES|||
|2|name|text|YES|||
|3|geom|USER-DEFINED|YES|||
|4|rep_pt|USER-DEFINED|YES|||

## adm_emd_raw
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|gid|integer(32,0)|NO|nextval('adm_emd_raw_gid_seq'::regclass)||
|2|emd_cd|character varying|YES|||
|3|name|character varying|YES|||
|4|geom|USER-DEFINED|YES|||

## adm_sgg
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|sig_cd|text|YES|||
|2|name|text|YES|||
|3|geom|USER-DEFINED|YES|||
|4|rep_pt|USER-DEFINED|YES|||

## adm_sgg_raw
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|gid|integer(32,0)|NO|nextval('adm_sgg_raw_gid_seq'::regclass)||
|2|sig_cd|character varying|YES|||
|3|name|character varying|YES|||
|4|geom|USER-DEFINED|YES|||

## adm_sido
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|gid|integer(32,0)|NO|nextval('adm_sido_gid_seq'::regclass)||
|2|sid_cd|text|YES|||
|3|sid_nm|text|YES|||
|4|geom|USER-DEFINED|YES|||
|5|centroid|USER-DEFINED|YES|||

## alembic_version
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|version_num|character varying(32)|NO|||

## aptinfo
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|apt_cd|text|NO|||
|2|sn|integer(32,0)|YES|||
|3|apt_nm|text|YES|||
|4|cmpx_clsf|text|YES|||
|5|apt_stdg_addr|text|YES|||
|6|apt_rdn_addr|text|YES|||
|7|ctpv_addr|text|YES|||
|8|sgg_addr|text|YES|||
|9|emd_addr|text|YES|||
|10|daddr|text|YES|||
|11|rdn_addr|text|YES|||
|12|road_daddr|text|YES|||
|13|telno|text|YES|||
|14|fxno|text|YES|||
|15|apt_cmpx|text|YES|||
|16|apt_atch_file|text|YES|||
|17|hh_type|text|YES|||
|18|mng_mthd|text|YES|||
|19|road_type|text|YES|||
|20|mn_mthd|text|YES|||
|21|whol_dong_cnt|integer(32,0)|YES|||
|22|tnohsh|integer(32,0)|YES|||
|23|bldr|text|YES|||
|24|dvlr|text|YES|||
|25|use_aprv_ymd|date|YES|||
|26|gfa|numeric(14,2)|YES|||
|27|rsdt_xuar|numeric(14,2)|YES|||
|28|mnco_levy_area|numeric(14,2)|YES|||
|29|xuar_hh_stts60|numeric(14,2)|YES|||
|30|xuar_hh_stts85|numeric(14,2)|YES|||
|31|xuar_hh_stts135|numeric(14,2)|YES|||
|32|xuar_hh_stts136|numeric(14,2)|YES|||
|33|hmpg|text|YES|||
|34|reg_ymd|date|YES|||
|35|mdfcn_ymd|date|YES|||
|36|epis_mng_no|text|YES|||
|37|eps_mng_form|text|YES|||
|38|hh_elct_ctrt_mthd|text|YES|||
|39|clng_mng_form|text|YES|||
|40|bdar|numeric(14,2)|YES|||
|41|prk_cntom|integer(32,0)|YES|||
|42|se_cd|text|YES|||
|43|cmpx_aprv_day|date|YES|||
|44|use_yn|text|YES|||
|45|mnco_uld_yn|text|YES|||
|46|lng|numeric(10,7)|YES|||
|47|lat|numeric(10,7)|YES|||
|48|cmpx_apld_day|date|YES|||
|49|gu_key|text|YES|||
|50|dong_key|text|YES|||
|51|name_key|text|YES|||
|52|lot_key|text|YES|||
|53|raw|jsonb|NO|||
|54|created_at|timestamp with time zone|NO|now()||
|55|updated_at|timestamp with time zone|NO|now()||

## aptinfo_ext_v
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|apt_cd|text|YES|||
|2|apt_nm|text|YES|||
|3|lot_addr_nospace|text|YES|||

## aptinfo_summary
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|apt_cd|text|NO|||
|2|sn|integer(32,0)|YES|||
|3|apt_nm|text|YES|||
|4|cmpx_clsf|text|YES|||
|5|apt_stdg_addr|text|YES|||
|6|apt_rdn_addr|text|YES|||
|7|ctpv_addr|text|YES|||
|8|sgg_addr|text|YES|||
|9|emd_addr|text|YES|||
|10|daddr|text|YES|||
|11|rdn_addr|text|YES|||
|12|road_daddr|text|YES|||
|13|telno|text|YES|||
|14|fxno|text|YES|||
|15|apt_cmpx|text|YES|||
|16|apt_atch_file|text|YES|||
|17|hh_type|text|YES|||
|18|mng_mthd|text|YES|||
|19|road_type|text|YES|||
|20|mn_mthd|text|YES|||
|21|whol_dong_cnt|integer(32,0)|YES|||
|22|tnohsh|integer(32,0)|YES|||
|23|bldr|text|YES|||
|24|dvlr|text|YES|||
|25|use_aprv_ymd|date|YES|||
|26|gfa|numeric(14,2)|YES|||
|27|rsdt_xuar|numeric(14,2)|YES|||
|28|mnco_levy_area|numeric(14,2)|YES|||
|29|xuar_hh_stts60|numeric(14,2)|YES|||
|30|xuar_hh_stts85|numeric(14,2)|YES|||
|31|xuar_hh_stts135|numeric(14,2)|YES|||
|32|xuar_hh_stts136|numeric(14,2)|YES|||
|33|hmpg|text|YES|||
|34|reg_ymd|date|YES|||
|35|mdfcn_ymd|date|YES|||
|36|epis_mng_no|text|YES|||
|37|eps_mng_form|text|YES|||
|38|hh_elct_ctrt_mthd|text|YES|||
|39|clng_mng_form|text|YES|||
|40|bdar|numeric(14,2)|YES|||
|41|prk_cntom|integer(32,0)|YES|||
|42|se_cd|text|YES|||
|43|cmpx_aprv_day|date|YES|||
|44|use_yn|text|YES|||
|45|mnco_uld_yn|text|YES|||
|46|lng|numeric(10,7)|YES|||
|47|lat|numeric(10,7)|YES|||
|48|cmpx_apld_day|date|YES|||
|49|gu_key|text|YES|||
|50|dong_key|text|YES|||
|51|name_key|text|YES|||
|52|lot_key|text|YES|||
|53|raw|jsonb|NO|||
|54|created_at|timestamp with time zone|NO|now()||
|55|updated_at|timestamp with time zone|NO|now()||
|56|lot_addr|text|YES|||
|57|lot_main|integer(32,0)|YES|||
|58|lot_sub|integer(32,0)|YES|||
|59|lot_union|text|YES|||
|60|sale84_med_3m|numeric|YES|||
|61|sale84_med_6m|numeric|YES|||
|62|sale84_med_12m|numeric|YES|||
|63|rent84_med_3m|numeric|YES|||
|64|rent84_med_6m|numeric|YES|||
|65|rent84_med_12m|numeric|YES|||
|66|sale84_med_1w|numeric|YES|||
|67|sale84_med_1m|numeric|YES|||
|68|sale84_med_24m|numeric|YES|||
|69|sale84_med_36m|numeric|YES|||
|70|rent84_med_1w|numeric|YES|||
|71|rent84_med_1m|numeric|YES|||
|72|rent84_med_24m|numeric|YES|||
|73|rent84_med_36m|numeric|YES|||
|74|sale_tx_cnt_1w|integer(32,0)|YES|||
|75|sale_tx_cnt_1m|integer(32,0)|YES|||
|76|sale_tx_cnt_3m|integer(32,0)|YES|||
|77|sale_tx_cnt_6m|integer(32,0)|YES|||
|78|sale_tx_cnt_12m|integer(32,0)|YES|||
|79|sale_tx_cnt_24m|integer(32,0)|YES|||
|80|sale_tx_cnt_36m|integer(32,0)|YES|||
|81|rent_tx_cnt_1w|integer(32,0)|YES|||
|82|rent_tx_cnt_1m|integer(32,0)|YES|||
|83|rent_tx_cnt_3m|integer(32,0)|YES|||
|84|rent_tx_cnt_6m|integer(32,0)|YES|||
|85|rent_tx_cnt_12m|integer(32,0)|YES|||
|86|rent_tx_cnt_24m|integer(32,0)|YES|||
|87|rent_tx_cnt_36m|integer(32,0)|YES|||
|88|geom|USER-DEFINED|YES|||

## geography_columns
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|f_table_catalog|name|YES|||
|2|f_table_schema|name|YES|||
|3|f_table_name|name|YES|||
|4|f_geography_column|name|YES|||
|5|coord_dimension|integer(32,0)|YES|||
|6|srid|integer(32,0)|YES|||
|7|type|text|YES|||

## geometry_columns
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|f_table_catalog|character varying(256)|YES|||
|2|f_table_schema|name|YES|||
|3|f_table_name|name|YES|||
|4|f_geometry_column|name|YES|||
|5|coord_dimension|integer(32,0)|YES|||
|6|srid|integer(32,0)|YES|||
|7|type|character varying(30)|YES|||

## rent
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|id|bigint(64,0)|NO|nextval('rent_id_seq'::regclass)||
|2|rcpt_yr|integer(32,0)|YES|||
|3|cgg_cd|text|YES|||
|4|cgg_nm|text|YES|||
|5|stdg_cd|text|YES|||
|6|stdg_nm|text|YES|||
|7|lotno_se|text|YES|||
|8|lotno_se_nm|text|YES|||
|9|mno|text|YES|||
|10|sno|text|YES|||
|11|flr|integer(32,0)|YES|||
|12|ctrt_day|text|YES|||
|13|rent_se|text|YES|||
|14|rent_area|numeric(10,2)|YES|||
|15|grfe_mwon|bigint(64,0)|YES|||
|16|rtfe_mwon|bigint(64,0)|YES|||
|17|bldg_nm|text|YES|||
|18|arch_yr|integer(32,0)|YES|||
|19|bldg_usg|text|YES|||
|20|ctrt_prd|text|YES|||
|21|new_updt_yn|text|YES|||
|22|ctrt_updt_use_yn|text|YES|||
|23|bfr_grfe_mwon|bigint(64,0)|YES|||
|24|bfr_rtfe_mwon|bigint(64,0)|YES|||
|25|contract_date|date|YES|||
|26|area_m2|numeric(10,2)|YES|||
|27|deposit_krw|bigint(64,0)|YES|||
|28|rent_krw|bigint(64,0)|YES|||
|29|lot_key|text|YES|||
|30|gu_key|text|YES|||
|31|dong_key|text|YES|||
|32|name_key|text|YES|||
|33|lat|numeric(10,7)|YES|||
|34|lng|numeric(10,7)|YES|||
|35|raw|jsonb|NO|||
|36|created_at|timestamp with time zone|NO|now()||
|37|updated_at|timestamp with time zone|NO|now()||

## sale
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|id|bigint(64,0)|NO|nextval('sale_id_seq'::regclass)||
|2|raw|jsonb|NO|||
|3|rcpt_yr|integer(32,0)|YES||접수연도|
|4|cgg_cd|integer(32,0)|YES||자치구코드|
|5|cgg_nm|text|YES||자치구명|
|6|stdg_cd|integer(32,0)|YES||법정동코드|
|7|stdg_nm|text|YES||법정동명|
|8|lotno_se|integer(32,0)|YES||지번구분|
|9|lotno_se_nm|text|YES||지번구분명|
|10|mno|text|YES||본번|
|11|sno|text|YES||부번|
|12|bldg_nm|text|YES||건물명|
|13|ctrt_day|date|YES||계약일|
|14|thing_amt|bigint(64,0)|YES||물건금액(만원)|
|15|arch_area|numeric(14,3)|YES||건물면적(㎡)|
|16|land_area|numeric(14,3)|YES||토지면적(㎡)|
|17|flr|text|YES||층|
|18|rght_se|text|YES||권리구분|
|19|rtrcn_day|text|YES||취소일|
|20|arch_yr|integer(32,0)|YES||건축년도|
|21|bldg_usg|text|YES||건물용도|
|22|dclr_se|text|YES||신고구분|
|23|opbiz_restagnt_sgg_nm|text|YES||신고한 개업공인중개사 시군구명|
|24|lat|numeric(10,7)|YES|||
|25|lng|numeric(10,7)|YES|||
|26|created_at|timestamp with time zone|NO|CURRENT_TIMESTAMP||
|27|updated_at|timestamp with time zone|NO|CURRENT_TIMESTAMP||
|28|gu_key|text|YES|||
|29|dong_key|text|YES|||
|30|name_key|text|YES|||
|31|lot_key|text|YES|||

## spatial_ref_sys
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|srid|integer(32,0)|NO|||
|2|auth_name|character varying(256)|YES|||
|3|auth_srid|integer(32,0)|YES|||
|4|srtext|character varying(2048)|YES|||
|5|proj4text|character varying(2048)|YES|||

## v_apt_markers
| # | column | type | null | default | comment |
|---|--------|------|------|---------|---------|
|1|id|text|YES|||
|2|name|text|YES|||
|3|lat|double precision(53)|YES|||
|4|lng|double precision(53)|YES|||
|5|gu|text|YES|||
|6|dong|text|YES|||
|7|addr_road|text|YES|||
|8|addr_jibun|text|YES|||

