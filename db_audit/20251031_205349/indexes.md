## adm_emd
CREATE INDEX adm_emd_gix ON public.adm_emd USING gist (geom)
CREATE INDEX adm_emd_pt_gix ON public.adm_emd USING gist (rep_pt)
CREATE UNIQUE INDEX adm_emd_emd_cd_idx ON public.adm_emd USING btree (emd_cd)

## adm_emd_raw
CREATE INDEX adm_emd_raw_geom_geom_idx ON public.adm_emd_raw USING gist (geom)
CREATE UNIQUE INDEX adm_emd_raw_pkey ON public.adm_emd_raw USING btree (gid)

## adm_sgg
CREATE INDEX adm_sgg_gix ON public.adm_sgg USING gist (geom)
CREATE INDEX adm_sgg_pt_gix ON public.adm_sgg USING gist (rep_pt)
CREATE UNIQUE INDEX adm_sgg_sig_cd_idx ON public.adm_sgg USING btree (sig_cd)

## adm_sgg_raw
CREATE INDEX adm_sgg_raw_geom_geom_idx ON public.adm_sgg_raw USING gist (geom)
CREATE UNIQUE INDEX adm_sgg_raw_pkey ON public.adm_sgg_raw USING btree (gid)

## adm_sido
CREATE INDEX adm_sido_gix ON public.adm_sido USING gist (geom)
CREATE INDEX adm_sido_sidcd_ix ON public.adm_sido USING btree (sid_cd)
CREATE UNIQUE INDEX adm_sido_pkey ON public.adm_sido USING btree (gid)

## alembic_version
CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num)

## aptinfo
CREATE INDEX ix_aptinfo_apt_nm ON public.aptinfo USING btree (apt_nm)
CREATE INDEX ix_aptinfo_dong_key ON public.aptinfo USING btree (dong_key)
CREATE INDEX ix_aptinfo_gu_key ON public.aptinfo USING btree (gu_key)
CREATE INDEX ix_aptinfo_lot_key ON public.aptinfo USING btree (lot_key)
CREATE INDEX ix_aptinfo_name_key ON public.aptinfo USING btree (name_key)
CREATE UNIQUE INDEX aptinfo_pkey ON public.aptinfo USING btree (apt_cd)

## aptinfo_summary
CREATE INDEX aptinfo_ext_apt_nm_idx ON public.aptinfo_summary USING btree (apt_nm)
CREATE INDEX aptinfo_ext_dong_key_idx ON public.aptinfo_summary USING btree (dong_key)
CREATE INDEX aptinfo_ext_gu_key_idx ON public.aptinfo_summary USING btree (gu_key)
CREATE INDEX aptinfo_ext_lot_key_idx ON public.aptinfo_summary USING btree (lot_key)
CREATE INDEX aptinfo_ext_name_key_idx ON public.aptinfo_summary USING btree (name_key)
CREATE INDEX ix_aptinfo_ext_aptcd ON public.aptinfo_summary USING btree (apt_cd)
CREATE INDEX ix_aptinfo_ext_lotaddr_nospace ON public.aptinfo_summary USING btree (replace(lot_addr, ' '::text, ''::text))
CREATE INDEX ix_aptinfo_ext_lotaddr_null ON public.aptinfo_summary USING btree (((lot_addr IS NULL))) WHERE (lot_addr IS NULL)
CREATE UNIQUE INDEX aptinfo_ext_pkey ON public.aptinfo_summary USING btree (apt_cd)

## rent
CREATE INDEX ix_rent_cgg_nm ON public.rent USING btree (cgg_nm)
CREATE INDEX ix_rent_contract_date ON public.rent USING btree (contract_date)
CREATE INDEX ix_rent_lot_key ON public.rent USING btree (lot_key)
CREATE INDEX ix_rent_name_key ON public.rent USING btree (name_key)
CREATE INDEX ix_rent_stdg_nm ON public.rent USING btree (stdg_nm)
CREATE UNIQUE INDEX rent_pkey ON public.rent USING btree (id)

## sale
CREATE INDEX ix_sale_bldg_nm ON public.sale USING btree (bldg_nm)
CREATE INDEX ix_sale_cgg_nm ON public.sale USING btree (cgg_nm)
CREATE INDEX ix_sale_ctrt_day ON public.sale USING btree (ctrt_day)
CREATE INDEX ix_sale_dong_key ON public.sale USING btree (dong_key)
CREATE INDEX ix_sale_gu_key ON public.sale USING btree (gu_key)
CREATE INDEX ix_sale_lot_key ON public.sale USING btree (lot_key)
CREATE INDEX ix_sale_name_key ON public.sale USING btree (name_key)
CREATE INDEX ix_sale_stdg_nm ON public.sale USING btree (stdg_nm)
CREATE UNIQUE INDEX sale_pkey ON public.sale USING btree (id)

## spatial_ref_sys
CREATE UNIQUE INDEX spatial_ref_sys_pkey ON public.spatial_ref_sys USING btree (srid)

