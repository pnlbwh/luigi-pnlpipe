
![](hcp_pipeline.png)


* Organize data according to BIDS

> cd /data/pnl/U01_HCP_Psychosis/data_processing

```python
BIDS/
├── derivatives
└── rawdata

BIDS/
├── derivatives
└── rawdata
    ├── sub-1003
    └── sub-1004
    
BIDS/
├── derivatives
└── rawdata
    ├── sub-1003
    │   └── ses-1
    └── sub-1004
        └── ses-1
        
BIDS/
├── derivatives
└── rawdata
    ├── sub-1003
    │   └── ses-1
    │       ├── anat
    │       ├── dwi
    │       └── func
    └── sub-1004
        └── ses-1
            ├── anat
            ├── dwi
            └── func

```

<details><summary>BIDS/</summary>

```python
BIDS/
├── derivatives
└── rawdata
    ├── sub-1003
    │   └── ses-1
    │       ├── anat
    │       │   ├── sub-1003_ses-1_T1w.nii.gz
    │       │   └── sub-1003_ses-1_T2w.nii.gz
    │       ├── dwi
    │       │   ├── sub-1003_ses-1_acq-AP_dir-98_dwi.bval
    │       │   ├── sub-1003_ses-1_acq-AP_dir-98_dwi.bvec
    │       │   ├── sub-1003_ses-1_acq-AP_dir-98_dwi.nii.gz
    │       │   ├── sub-1003_ses-1_acq-PA_dir-98_dwi.bval
    │       │   ├── sub-1003_ses-1_acq-PA_dir-98_dwi.bvec
    │       │   └── sub-1003_ses-1_acq-PA_dir-98_dwi.nii.gz
    │       └── func
    │           ├── sub-1003_ses-1_task-rest_acq-AP_run-1_bold.json
    │           ├── sub-1003_ses-1_task-rest_acq-AP_run-1_bold.nii.gz
    │           ├── sub-1003_ses-1_task-rest_acq-AP_run-2_bold.json
    │           ├── sub-1003_ses-1_task-rest_acq-AP_run-2_bold.nii.gz
    │           ├── sub-1003_ses-1_task-rest_acq-PA_run-1_bold.json
    │           ├── sub-1003_ses-1_task-rest_acq-PA_run-1_bold.nii.gz
    │           ├── sub-1003_ses-1_task-rest_acq-PA_run-2_bold.json
    │           └── sub-1003_ses-1_task-rest_acq-PA_run-2_bold.nii.gz
    └── sub-1004
        └── ses-1
            ├── anat
            │   ├── sub-1004_ses-1_T1w.nii.gz
            │   └── sub-1004_ses-1_T2w.nii.gz
            ├── dwi
            │   ├── sub-1004_ses-1_acq-AP_dir-98_dwi.bval
            │   ├── sub-1004_ses-1_acq-AP_dir-98_dwi.bvec
            │   ├── sub-1004_ses-1_acq-AP_dir-98_dwi.nii.gz
            │   ├── sub-1004_ses-1_acq-AP_dir-99_dwi.bval
            │   ├── sub-1004_ses-1_acq-AP_dir-99_dwi.bvec
            │   ├── sub-1004_ses-1_acq-AP_dir-99_dwi.json
            │   ├── sub-1004_ses-1_acq-AP_dir-99_dwi.nii.gz
            │   ├── sub-1004_ses-1_acq-PA_dir-98_dwi.bval
            │   ├── sub-1004_ses-1_acq-PA_dir-98_dwi.bvec
            │   ├── sub-1004_ses-1_acq-PA_dir-98_dwi.nii.gz
            │   ├── sub-1004_ses-1_acq-PA_dir-99_dwi.bval
            │   ├── sub-1004_ses-1_acq-PA_dir-99_dwi.bvec
            │   ├── sub-1004_ses-1_acq-PA_dir-99_dwi.json
            │   └── sub-1004_ses-1_acq-PA_dir-99_dwi.nii.gz
            └── func
                ├── sub-1004_ses-1_task-rest_acq-AP_run-1_bold.json
                ├── sub-1004_ses-1_task-rest_acq-AP_run-1_bold.nii.gz
                ├── sub-1004_ses-1_task-rest_acq-AP_run-2_bold.json
                ├── sub-1004_ses-1_task-rest_acq-AP_run-2_bold.nii.gz
                ├── sub-1004_ses-1_task-rest_acq-PA_run-1_bold.json
                ├── sub-1004_ses-1_task-rest_acq-PA_run-1_bold.nii.gz
                ├── sub-1004_ses-1_task-rest_acq-PA_run-2_bold.json
                └── sub-1004_ses-1_task-rest_acq-PA_run-2_bold.nii.gz
```
  
</details>



* T2w masking

<img src="T2w_mask.png" width=300>

[HD-BET](https://github.com/MIC-DKFZ/HD-BET) is a deep learning based brain extraction tool.
It should be run on a GPU device i.e. `grx**` node or `bhosts gpu_hg` cluster.

* Set up environment

```bash
source /data/pnl/soft/pnlpipe3/HD-BET/env.sh
export LUIGI_CONFIG_PATH=/data/pnl/soft/pnlpipe3/luigi-pnlpipe/params/hcp/T2w_mask.cfg
```

> /data/pnl/soft/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --task StructMask \
--bids-data-dir /data/pnl/soft/pnlpipe3/luigi-pnlpipe/BIDS/rawdata \
-c 1003 -s 1 --t2-template "sub-*/ses-1/anat/*_T2w.nii.gz"

After submitting the job, go to https://pnlservers.bwh.harvard.edu/luigi/ and monitor its status.
Its username and password are shared privately. You should also monitor logs that are printed in your terminal.

The `-c` flag also accepts a `caselist.txt` argument where each line is a case ID:

```
1003
1004
...
```

Similarly, the `-s` flag also accepts a `sessions.txt` argument where each line is a session ID:

```
1
2
...
```

Some of you have access to `bhosts gpu_hg` cluster where HD-BET could be run. We shall teach you
how to optimize the number of parallel cases you can mask on the cluster at a later date.


Output after HD-BET masking completes:

```python
derivatives/
└── pnlpipe
    ├── sub-1003
    │   └── ses-1
    │       └── anat
    └── sub-1004
        └── ses-1
            └── anat

```

```python
derivatives/
└── pnlpipe
    ├── sub-1003
    │   └── ses-1
    │       └── anat
    │           ├── sub-1003_ses-1_desc-T2wXcMabs_mask.nii.gz
    │           └── sub-1003_ses-1_desc-Xc_T2w.nii.gz
    └── sub-1004
        └── ses-1
            └── anat
                ├── sub-1004_ses-1_desc-T2wXcMabs_mask.nii.gz
                └── sub-1004_ses-1_desc-Xc_T2w.nii.gz

```


* Quality checking T2w mask

Quality checked mask must be saved with Qc suffix in the desc field for its integration with later part of the structural pipeline. Example:

```
Automated mask  : sub-1003/ses-1/anat/sub-1003_ses-1_desc-T2wXcMabs_mask.nii.gz
Quality checked : sub-1003/ses-1/anat/sub-1003_ses-1_desc-T2wXcMabsQc_mask.nii.gz
```


```python
derivatives/
└── pnlpipe
    ├── sub-1003
    │   └── ses-1
    │       └── anat
    │           ├── sub-1003_ses-1_desc-T2wXcMabs_mask.nii.gz
    |           ├── sub-1003_ses-1_desc-T2wXcMabsQc_mask.nii.gz
    │           └── sub-1003_ses-1_desc-Xc_T2w.nii.gz
    └── sub-1004
        └── ses-1
            └── anat
                ├── sub-1004_ses-1_desc-T2wXcMabs_mask.nii.gz
                ├── sub-1004_ses-1_desc-T2wXcMabsQc_mask.nii.gz
                └── sub-1004_ses-1_desc-Xc_T2w.nii.gz

```


* Now run Freesurfer

<img src="T1w_Freesurfer.png" width=500>

For HCP-EP data, we have created HD-BET mask for T2w images. Then we have warped them to obtain mask for T1w images.
Hence there is a line from `QC (Human)` to `StructMask` node in the above diagram.
This approach minimizes the human effort required to quality check masks for all modalities.
Nevertheless, you can create HD-BET mask for all modalities and quality check them manually.
Both T1w and T2w images are necessary for performing FreeSurfer segmentation. For this `Freesurfer` task,
use the following environment and configuration:


```bash
source /data/pnl/soft/pnlpipe3/bashrc3
export LUIGI_CONFIG_PATH=/data/pnl/soft/pnlpipe3/luigi-pnlpipe/params/hcp/struct_pipe_params.cfg
```

> /data/pnl/soft/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --task StructMask \
--bids-data-dir /data/pnl/soft/pnlpipe3/luigi-pnlpipe/BIDS/rawdata \
-c 1003 -s 1 \
--t2-template "sub-*/ses-1/anat/*_T2w.nii.gz" \
--t1-template "sub-*/ses-1/anat/*_T2w.nii.gz"

A few parameters of the above configuration file demands explanation:

```
[StructMask]
reg_method: rigid

[Freesurfer]
t1_mask_method: registration
t1_ref_img: *_desc-Xc_T2w.nii.gz
t1_ref_mask: *_desc-T2wXcMabsQc_mask.nii.gz

t2_mask_method: HD-BET
```

Notice the difference of values between `t2_mask_method` and `t1_mask_method`. Also notice the values of `ref_img` and `ref_mask` beginning with asterisk (`*`). The asterisk (`*`) is important. These are the patterns with which output directory is searched to obtain T2w image and associated HD-BET mask. The T2w image is used to register to target space, in this case T1w space. Finally, the associated HD-BET mask is warped to target space. Another important parameter is `reg_method`. It takes a value of either `rigid` or `SyN` indicating the type of ANTs registration you would like to perform. `rigid` is quick and sufficient for this setting. `SyN` is time consuming and can be more accurate.

`NOTE` There is a modality mismatch between the parameter name `t1_ref_img` and its value `*_desc-Xc_T2w.nii.gz`. It came from the convention ANTs follows. It means--to create a T1w mask, use the T2w mask as the reference image.


After `Freesurfer` task completes, the will look like:

<details><summary>derivatives/</summary>

```python
derivatives/
└── pnlpipe
    ├── sub-1003
    │   └── ses-1
    │       └── anat
    │           ├── fs7.1.0
    │           │   ├── label
    │           │   ├── mri
    │           │   ├── scripts
    │           │   ├── stats
    │           │   ├── surf
    │           │   ├── tmp
    │           │   ├── touch
    │           │   ├── trash
    │           │   └── version.txt
    │           ├── sub-1003_ses-1_desc-T2wXcMabsQc_mask.nii.gz
    │           ├── sub-1003_ses-1_desc-T2wXcMabsQcToT1wXc_mask.nii.gz
    │           ├── sub-1003_ses-1_desc-XcMaN4_T1w.nii.gz
    │           ├── sub-1003_ses-1_desc-XcMaN4_T2w.nii.gz
    │           ├── sub-1003_ses-1_desc-XcMa_T1w.nii.gz
    │           ├── sub-1003_ses-1_desc-XcMa_T2w.nii.gz
    │           ├── sub-1003_ses-1_desc-Xc_T1w.nii.gz
    │           └── sub-1003_ses-1_desc-Xc_T2w.nii.gz
    └── sub-1004
        └── ses-1
            └── anat
                ├── fs7.1.0
                │   ├── label
                │   ├── mri
                │   ├── scripts
                │   ├── stats
                │   ├── surf
                │   ├── tmp
                │   ├── touch
                │   ├── trash
                │   └── version.txt
                ├── sub-1004_ses-1_desc-T2wXcMabsQc_mask.nii.gz
                ├── sub-1004_ses-1_desc-T2wXcMabsQcToT1wXc_mask.nii.gz
                ├── sub-1004_ses-1_desc-XcMaN4_T1w.nii.gz
                ├── sub-1004_ses-1_desc-XcMaN4_T2w.nii.gz
                ├── sub-1004_ses-1_desc-XcMa_T1w.nii.gz
                ├── sub-1004_ses-1_desc-XcMa_T2w.nii.gz
                ├── sub-1004_ses-1_desc-Xc_T1w.nii.gz
                └── sub-1004_ses-1_desc-Xc_T2w.nii.gz

```

</details>

