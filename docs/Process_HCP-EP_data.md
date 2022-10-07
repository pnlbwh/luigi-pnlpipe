
![](hcp_pipeline.png)


* Organize data according to BIDS

```python
BIDS_example/
├── derivatives
└── rawdata

BIDS_example/
├── derivatives
└── rawdata
    ├── sub-1003
    └── sub-1004
    
BIDS_example/
├── derivatives
└── rawdata
    ├── sub-1003
    │   └── ses-1
    └── sub-1004
        └── ses-1
        
BIDS_example/
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

<details><summary>BIDS_example</summary>

```python
BIDS_example/
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
