
![](cte_pipeline.png)

### Structural pipeline

Its description is the same as that of HCP-EP [structural pipeline](https://github.com/pnlbwh/luigi-pnlpipe/blob/hcp/docs/Process_HCP-EP_data.md#structural-pipeline).
Instead of HD-BET, we used our good old MABS (Multi Atlas Brain Segmentation) algorithm to create T2w masks.


* StructMask

Use workflows/run_gpu_mask.lsf

source /data/pnl/soft/pnlpipe3/HD-BET/env.sh
~/Downloads/luigi-pnlpipe/exec/ExecuteTask --bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata --dwi-template "sub-*/ses-01/dwi/*_dwi.nii.gz" --t2-template "sub-*/ses-01/anat/*_AXT2.nii.gz" -c 1004 -s 01 --task StructMask


* Freesurfer

Repeat the above for Freesurfer


### Diffusion pipeline

StructMask needs to be completed first

Then complete CNN dwi mask

Finally run FslEddy

bashrc3
~/Downloads/luigi-pnlpipe/exec/ExecuteTask --bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata --dwi-template "sub-*/ses-01/dwi/*_dwi.nii.gz" --t2-template "sub-*/ses-01/anat/*_AXT2.nii.gz" -c 1004 -s 01 --task EddyEpi

