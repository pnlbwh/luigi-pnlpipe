PNL pipeline has a few branches for processing structural and diffusion MRI data.
The primary branches are **HCP** and **SynB0**. If neither works, we follow the legacy **CTE** branch.
These are described in order below.

Table of Contents
-----------------

  * [New bashrc](#new-bashrc)
  * [Workstations to use](#workstations-to-use)
  * [HCP](#hcp)
     * [Structural pipeline](#structural-pipeline)
     * [Run FreeSurfer segmentation](#run-freesurfer-segmentation)
     * [Diffusion pipeline](#diffusion-pipeline)
  * [SynB0](#synb0)
  * [CTE](#cte)
     * [Generate T2w mask using MABS (alternative to HD-BET)](#generate-t2w-mask-using-mabs-alternative-to-hd-bet)
     * [FSL Eddy + PNL EPI (alternative to SynB0)](#fsl-eddy--pnl-epi-alternative-to-synb0)



---

### New bashrc

`source /software/rocky9/bashrc9`


### Workstations to use

You can run this tutorial on any Red Hat 9 computer that has >=4 GB GPU on it. Examples include but are not limited to:

```
,,pnl-oracle,
,,pnl-predict,
,,pnl-maxwell,
,,pnl-axon,
,,pnl-thinkserv-1,
,,pnl-thinkserv-2,
,,pnl-x80-4,
,,pnl-x90-10,
```

---

### HCP

This is the primary way of processing new MRIs. HCP-like data consists of:

* T1w and T2w
* Two opposing AP and PA DWI

Reference: https://github.com/pnlbwh/luigi-pnlpipe/blob/hcp/docs/Process_HCP-EP_data.md

#### Structural pipeline

* Generate T2w mask using HD-BET

```
export LUIGI_CONFIG_PATH=/software/rocky9/luigi-pnlpipe/params/hcp/T2w_mask_params.cfg
/software/rocky9/luigi-pnlpipe/workflows/ExecuteTask.py -s 2 -c 4003 --t2-template sub-*/ses-*/anat/*_T2w.nii.gz --task StructMask --derivatives-name $USER-pnlpipe --bids-data-dir /software/rocky9/luigi-tutorial/hcp/rawdata
```

#### Run FreeSurfer segmentation

```
export LUIGI_CONFIG_PATH=/software/rocky9/luigi-pnlpipe/params/hcp/struct_pipe_params.cfg
/software/rocky9/luigi-pnlpipe/workflows/ExecuteTask.py -s 2 -c 4003 --t1-template sub-*/ses-*/anat/*_T1w.nii.gz --t2-template sub-*/ses-*/anat/*_T2w.nii.gz --task Freesurfer --derivatives-name $USER-pnlpipe --bids-data-dir /software/rocky9/luigi-tutorial/hcp/rawdata
```

#### Diffusion pipeline

It is one grand pipeline chaining PNL pre-processing, WashU HCP pipeline, UKFTractography, and white matter analysis.

> /software/rocky9/luigi-tutorial/hcp/hcp_pnl_topup.lsf

(All parameters are entered into this script)


---


### SynB0

This is another way of processing diffusion data when there is only one direction acquisition available.
It could be either AP or PA. We use a tool called *Synthesized b0 for diffusion distortion correction*.
For this way, you need:

* single DWI
* T1w

Reference: https://github.com/pnlbwh/luigi-pnlpipe/blob/hcp/docs/TUTORIAL.md#synb0

```
export LUIGI_CONFIG_PATH=/software/rocky9/luigi-pnlpipe/params/synb0/dwi_pipe_params.cfg
/software/rocky9/luigi-pnlpipe/workflows/ExecuteTask.py -s 001 -c ne00300 --dwi-template sub-*/ses-*/dwi/*_dwi.nii.gz --t1-template sub-*/ses-*/anat/*_T1w.nii.gz --task SynB0 --derivatives-name $USER-pnlpipe --bids-data-dir /software/rocky9/luigi-tutorial/edcrp/rawdata
```

---



### CTE

This branch is basically the alternative or fallback method. If none of the above works, you can use this branch.
The data that you need are:

* T1w and T2w
* single DWI
* Axial T2

Reference: https://github.com/pnlbwh/luigi-pnlpipe/blob/hcp/docs/Process_DIAGNOSE-CTE_data.md

#### Generate T2w mask using MABS (alternative to HD-BET)

MABS stands for *Multi Atlas Brain Segmentation*. It originated at PNL. You have to give a set of model
T2w images and human quality checked masks for MABS to work.

```
export LUIGI_CONFIG_PATH=/software/rocky9/luigi-pnlpipe/params/cte/T2w_mask_params.cfg
/software/rocky9/luigi-pnlpipe/workflows/ExecuteTask.py -s 01 -c 1003 --t2-template sub-*/ses-*/anat/*_T2w.nii.gz --task StructMask --derivatives-name $USER-pnlpipe --bids-data-dir /software/rocky9/luigi-tutorial/cte/rawdata
```

Afterward, you can run FreeSurfer segmentation as shown in **HCP** branch.

**Note:** If the above fails, make sure to mount `/data/pnl/` using `cifscreds add -u $USER -d PARTNERS` and retry.


#### FSL Eddy + PNL EPI (alternative to SynB0)

In this method, for processing diffusion image, you need an axial-T2 image, acquired in the same plane of T2w image.
That axial-T2 image is used in EPI correction while FSL does the eddy correction.

* Generate DWI mask
```
export LUIGI_CONFIG_PATH=/software/rocky9/luigi-pnlpipe/params/cte/dwi_pipe_params.cfg
/software/rocky9/luigi-pnlpipe/workflows/ExecuteTask.py -s 01 -c 1003 --dwi-template sub-*/ses-*/dwi/*_dwi.nii.gz --task CnnMask --derivatives-name $USER-pnlpipe --bids-data-dir /software/rocky9/luigi-tutorial/cte/rawdata
```

* Run FSL Eddy + PNL EPI

```
export LUIGI_CONFIG_PATH=/software/rocky9/luigi-pnlpipe/params/cte/dwi_pipe_params.cfg
/software/rocky9/luigi-pnlpipe/workflows/ExecuteTask.py -s 01 -c 1003 --dwi-template sub-*/ses-*/dwi/*_dwi.nii.gz --t2-template sub-*/ses-*/anat/*_AXT2.nii.gz --task EddyEpi --derivatives-name $USER-pnlpipe --bids-data-dir /software/rocky9/luigi-tutorial/cte/rawdata
```
