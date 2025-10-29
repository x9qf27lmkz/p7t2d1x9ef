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

## aptinfo_ext
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

