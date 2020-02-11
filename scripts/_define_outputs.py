def IO(id, bids_data_dir):
    from os.path import join as pjoin, abspath
    from plumbum import local

    # bids_derivatives
    dir= pjoin(abspath(bids_data_dir), 'derivatives', 'luigi-pnlpipe')
    local.path(dir).mkdir()

    inter= {}

    inter['t1_align_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'anat', f'sub-{id}_desc-Xc_T1w'))
    inter['t2_align_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'anat', f'sub-{id}_desc-Xc_T2w'))
    inter['dwi_align_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-Xc_dwi'))

    inter['t1_mabsmask_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'anat', f'sub-{id}_desc-T1wXcMabs'))
    inter['t2_mabsmask_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'anat', f'sub-{id}_desc-T2wXcMabs'))
    
    inter['fs_dir'] = local.path(pjoin(dir, f'sub-{id}', 'anat', 'freesurfer'))

    inter['aligned_bse_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-dwiXc_bse'))
    inter['eddy_bse_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-dwiXcEd_bse'))
    inter['eddy_epi_bse_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-dwiXcEdEp_bse'))

    inter['aligned_bse_betmask_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-XcBseBet'))
    inter['eddy_bse_betmask_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-XcEdBseBet'))
    inter['eddy_epi_bse_betmask_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-XcEdEpBseBet'))

    inter['aligned_bse_masked_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-dwiXcMa_bse'))
    inter['eddy_bse_masked_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-dwiXcEdMa_bse'))
    inter['eddy_epi_bse_masked_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-dwiXcEdEpMa_bse'))

    inter['eddy_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-XcEd_dwi'))
    inter['eddy_epi_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'dwi', f'sub-{id}_desc-XcEdEp_dwi'))
    
    inter['eddy_fs2dwi_dir'] = local.path(pjoin(dir, f'sub-{id}', 'fs2dwi', 'eddy_fs2dwi'))
    inter['fs_in_eddy'] = local.path(pjoin(dir, f'sub-{id}', 'fs2dwi', 'eddy_fs2dwi', 'wmparcInDwi.nii.gz'))
    inter['epi_fs2dwi_dir'] = local.path(pjoin(dir, f'sub-{id}', 'fs2dwi', 'epi_fs2dwi'))
    inter['fs_in_epi'] = local.path(pjoin(dir, f'sub-{id}', 'fs2dwi', 'epi_fs2dwi', 'wmparcInDwi.nii.gz'))

    inter['eddy_tract_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'tracts', f'sub-{id}_desc-XcEd'))
    inter['eddy_epi_tract_prefix'] = local.path(pjoin(dir, f'sub-{id}', 'tracts', f'sub-{id}_desc-XcEdEp'))

    inter['eddy_wmql_dir'] = local.path(pjoin(dir, f'sub-{id}', 'tracts', 'wmql', 'eddy'))
    inter['eddy_wmqlqc_dir'] = local.path(pjoin(dir, f'sub-{id}', 'tracts', 'wmqlqc', 'eddy'))
    inter['epi_wmql_dir'] = local.path(pjoin(dir, f'sub-{id}', 'tracts', 'wmql', 'epi'))
    inter['epi_wmqlqc_dir'] = local.path(pjoin(dir, f'sub-{id}', 'tracts', 'wmqlqc', 'epi'))
    

    return inter


