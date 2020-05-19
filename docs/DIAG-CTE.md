The [Luigi workflows](../workflows/) accept input in two ways-- through the command line and through a config file. 
The motivation for that compartmentalization is to differentiate between high-level (former) and low-level (latter) inputs.
High-level inputs facilitate launching workflows while low-level inputs specify parameters pertinent to the workflow, 
some of which are optional. Workflow specific parameters are provided in a configuration file defined via 
environment variable `LUIGI_CONFIG_PATH`.

```bash
usage: ExecuteTask.py [-h] --bids-data-dir BIDS_DATA_DIR -c C
                      [--dwi-template DWI_TEMPLATE]
                      [--t1-template T1_TEMPLATE] [--t2-template T2_TEMPLATE]
                      --task
                      {StructMask,Freesurfer,PnlEddy,PnlEddyEpi,FslEddy,FslEddyEpi,Ukf,Fs2Dwi,Wmql,Wmqlqc}
                      [--num-workers NUM_WORKERS]
                      [--derivatives-name DERIVATIVES_NAME]

pnlpipe glued together using Luigi, optional parameters can be set by
environment variable LUIGI_CONFIG_PATH, see luigi-pnlpipe/scripts/params/*.cfg
as example

optional arguments:
  -h, --help            show this help message and exit
  --bids-data-dir BIDS_DATA_DIR
                        /path/to/bids/data/directory
  -c C                  a single caseid or a .txt file where each line is a
                        caseid
  --dwi-template DWI_TEMPLATE
                        glob bids-data-dir/t1-template to find input data
                        (default: sub-$/dwi/*_dwi.nii.gz)
  --t1-template T1_TEMPLATE
                        glob bids-data-dir/t2-template to find input data
                        (default: sub-$/anat/*_T1w.nii.gz)
  --t2-template T2_TEMPLATE
                        glob bids-data-dir/t2-template to find input data
                        (default: None)
  --task {StructMask,Freesurfer,PnlEddy,PnlEddyEpi,FslEddy,FslEddyEpi,Ukf,Fs2Dwi,Wmql,Wmqlqc}
                        number of Luigi workers (default: None)
  --num-workers NUM_WORKERS
                        number of Luigi workers (default: 1)
  --derivatives-name DERIVATIVES_NAME
                        relative name of bids derivatives directory,
                        translates to bids-data-dir/derivatives/derivatives-
                        name (default: pnlpipe)
```

In the following, we shall provide both mandatory and optional settings for each workflow. Before running any workflow, 
you should set up your terminal so that various prerequisite software i.e. FSL, FreeSurfer, ANTs etc. are found. 
In addition, define `PYTHONPATH`:

    cd ~/luigi-pnlpipe
    export PYTHONPATH=`pwd`/scripts:`pwd`/workflows:$PYTHONPATH


# Structural pipeline

The goal of structural pipeline is to perform FreeSurfer segmentation. To be able to do that, we need mask for 
structural images-- T1w and maybe T2w.

## Create masks

MABS (Multi Atlas Brain Segmentation) remains as the acceptable technique to create mask for structural images. 
We shall create a MABS mask for one modality only and then quality check it manually. We shall warp that 
quality checked mask to obtain mask for other modalities. This approach minimizes the human effort required to quality 
check masks for all modalities. Nevertheless, you can create MABS mask for all modalities and quality check them manually.  


### MABS mask

MABS requires training data which are specified through `csvFile` below. `StructMask` task is capable of waiting until 
quality checking of automated mask is complete, an option which can be invoked by setting `mask_qc: True`. 
However, you can set `mask_qc: False`, obtain all masks, and then quality check at a later time.
So the content of `LUIGI_CONFIG_PATH` is following:

```cfg
[DEFAULT]
mabs_mask_nproc: 8
fusion:
debug: False
reg_method:
slicer_exec:
mask_qc: False


[StructMask]
csvFile: /path/to/trainingDataT1Masks.csv
ref_img:
ref_mask:
```

Finally, save the above configuration in `mabs_mask_params.cfg` and run `StructMask` task as follows:

```bash
export LUIGI_CONFIG_PATH=/path/to/mabs_mask_params.cfg

# individual
# MABS masking of T2w image for case 1001
exec/ExecuteTask --task StructMask \
--bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata -c 1001 --t2-template sub-$/ses-01/anat/*_T2w.nii.gz

# group
# MABS masking of T2w image for all cases
exec/ExecuteTask --task StructMask \
--bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata -c /path/to/caselist.txt --t2-template sub-id/anat/*_T2w.nii.gz \
--num-workers 8
```

Quality checked mask must be saved with `Qc` suffix in the `desc` field for its integration with later part of 
the structural pipeline. Example: 

        Mabs mask   : sub-1001/ses-01/anat/sub-1001_ses-01_desc-T2wXcMabs_mask.nii.gz
    Quality checked : sub-1001/ses-01/anat/sub-1001_ses-01_desc-T2wXcMabsQc_mask.nii.gz


A couple of points to note regarding the above examples:
* For executing task through LSF, you should be using the individual example
* When using group example, depending on the number of cases and CPUs in your machine, you should provide 
a suitable `--num-workers` so optimal number of cases are processed parallelly allowing room for other users 
in a shared cluster environment.
* Although we provided both individual and group examples in the above, we shall be providing only individual examples 
in the rest of the tutorial. You can follow the above group example as a model for the rest. 

Tips:
* `lscpu` command will show you the number of processors available. 
As a rule of thumb, you can choose `--num-workers` to be half the number of available processors on a shared environment. 
* `vmstat -s -S M` will show you the RAM available

### Warped mask

For DIAG-CTE data, we have created MABS mask for T2w images. Then we have warped them to obtain mask for T1w and AXT2 
images. Alternatively, you can create masks for T1w images first and then use them to create masks 
for T2w and AXT2 images. Once again, we need a configuration to be provided via `LUIGI_CONFIG_PATH`:

```cfg
[DEFAULT]
mabs_mask_nproc: 8
fusion:
debug: False
reg_method: SyN
slicer_exec:
mask_qc: False


[StructMask]
csvFile:
ref_img: *_desc-Xc_T2w.nii.gz
ref_mask: *_desc-T2wXcMabsQc_mask.nii.gz
```

Notice the values of `ref_img` and `ref_mask` beginning with asterisk (`*`). The asterisk (`*`) is important. 
These are the patterns with which output directory is searched to obtain structural image and associated MABS mask. 
The structural image is used to register to target space, in this case T1w or AXT2 space. Finally, the associated MABS 
mask is warped to target space.

Other important parameters are `reg_method` and `mask_qc`. `reg_method` takes a value of either `rigid` or `SyN` 
indicating the type of `antsRegistration` you would like to perform. On the other hand, since MABS mask was already 
quality checked, `mask_qc` is set to False. Notice the `csvFile` field that must be kept empty otherwise MABS masking 
procedure will be triggered.

Putting them all together:

```bash
export LUIGI_CONFIG_PATH=/path/to/mask_warping_params.cfg

exec/ExecuteTask --task StructMask \
--bids-data-dir /data/pnl/DIAGNOSE_CTE_U01/rawdata -c 1001 --t1-template sub-$/ses-01/anat/*_T1w.nii.gz
```


## Run FreeSurfer

TODO: explain why `mask_qc: False`



### With T1w only

```cfg
[Freesurfer]
t1_csvFile:
t1_ref_img: *_desc-Xc_T2w.nii.gz
t1_ref_mask: *_desc-T2wXcMabsQc_mask.nii.gz
t1_mask_qc: False

freesurfer_nproc: 4
expert_file:
no_hires: True
no_skullstrip: True
subfields: True
fs_dirname: freesurfer
```

Notice the introduction of `t1_` prefix preceding parameters we have for `StructMask` task itself. 
The role of this introduction would be clear in the following section.

```bash


```

### With both T1w and T2w

```bash


```



# Run dwi pipeline

## Create masks

```cfg
[DEFAULT]
## SelectDwiFiles
dwi_template:


## StructMask, PnlEddy, PnlEddyEpi
debug: False


## StructMask, BseBetmask, CnnMask
slicer_exec:


## BseMask, CnnMask
dwi_mask_qc: True


## CnnMask
model_folder: /data/pnl/soft/pnlpipe3/CNN-Diffusion-MRIBrain-Segmentation/model_folder


## BseExtract
which_bse:
b0_threshold: 50


## BseMask
bet_threshold: 0.25
mask_method: Bet


[SelectDwiFiles]

[BseExtract]

[BseMask]

[CnnMask]

```


## Run FSL eddy

```cfg
[DEFAULT]
## SelectDwiFiles
dwi_template:


## StructMask
csvFile:
mabs_mask_nproc: 8
fusion:
mask_qc: False
ref_img: *_desc-Xc_T2w.nii.gz
ref_mask: *_desc-T2wXcMabsQc_mask.nii.gz
reg_method: SyN


## StructMask, PnlEddy, PnlEddyEpi
debug: False


## StructMask, BseBetmask, CnnMask
slicer_exec:


## BseMask, CnnMask
dwi_mask_qc: True


## CnnMask
model_folder: /data/pnl/soft/pnlpipe3/CNN-Diffusion-MRIBrain-Segmentation/model_folder


## BseExtract
which_bse:
b0_threshold: 50


## BseMask
bet_threshold: 0.25
mask_method: Bet


## PnlEddy
eddy_nproc: 8


# FslEddy, FslEddyEpi
acqp: /data/pnl/DIAGNOSE_CTE_U01/acqp.txt
index: /data/pnl/DIAGNOSE_CTE_U01/index.txt
config: /data/pnl/DIAGNOSE_CTE_U01/eddy_config.txt


## PnlEddyEpi, FslEddyEpi
epi_nproc: 8


## Ukf
ukf_params: --seedingThreshold,0.4,--seedsPerVoxel,1


[SelectDwiFiles]

[StructMask]

[BseExtract]

[BseMask]

[CnnMask]

[PnlEddy]

[PnlEddyEpi]

[FslEddy]

[FslEddyEpi]

[Ukf]

```
