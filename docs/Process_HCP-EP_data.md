
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
-c 1003 -s 1 --t2-template sub-*/ses-1/anat/*_T2w.nii.gz

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
