
![](cte_pipeline.png)

### Structural pipeline

Its description is the same as that of HCP-EP [structural pipeline](https://github.com/pnlbwh/luigi-pnlpipe/blob/hcp/docs/Process_HCP-EP_data.md#structural-pipeline).
Instead of HD-BET, we used our good old MABS (Multi Atlas Brain Segmentation) algorithm to create T2w masks.

It is run in two steps: T2w mask creation and FreeSurfer segmentation.

* T2w mask creation

```bash
source /data/pnl/soft/pnlpipe3/bashrc3
export LUIGI_CONFIG_PATH=/data/pnl/soft/pnlpipe3/luigi-pnlpipe/params/cte/T2w_mask_params.cfg
/data/pnl/soft/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --task StructMask \
--bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata \
--t2-template "sub-*/ses-01/anat/*_T2w.nii.gz" \
-c 1004 -s 01
```

* FreesSurfer segmentation

```bash
source /data/pnl/soft/pnlpipe3/bashrc3
export LUIGI_CONFIG_PATH=/data/pnl/soft/pnlpipe3/luigi-pnlpipe/params/cte/struct_pipe_params.cfg
/data/pnl/soft/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --task Freesurfer \
--bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata \
--t1-template "sub-*/ses-01/anat/*_T1w.nii.gz" \
--t2-template "sub-*/ses-01/anat/*_T2w.nii.gz" \
-c 1004 -s 01
```



/data/pnl/soft/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata --dwi-template "sub-*/ses-01/dwi/*_dwi.nii.gz" --t2-template "sub-*/ses-01/anat/*_AXT2.nii.gz" -c 1004 -s 01 --task StructMask
```

### Diffusion pipeline

StructMask needs to be completed first

Then complete CNN dwi mask

Finally run FslEddy

bashrc3
~/Downloads/luigi-pnlpipe/exec/ExecuteTask --bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata --dwi-template "sub-*/ses-01/dwi/*_dwi.nii.gz" --t2-template "sub-*/ses-01/anat/*_AXT2.nii.gz" -c 1004 -s 01 --task EddyEpi

