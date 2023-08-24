#!/bin/bash

# for time profiling
date

# User will edit only this block =========================================================
caselist=$1
s=01
dir=80
acq=AP
BIDS_DATA_DIR=/data/pnl/Collaborators/CMA/mtsintou/Emotion/rawdata
DWI_TEMPLATE=sub-*/ses-*/dwi/sub-*_ses-*_acq-${acq}_dir-${dir}_dwi.nii.gz
INDEX=/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/index.txt
ACQPARAMS=/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/acqparams.txt
LUIGI_CONFIG_PATH=/data/pnl/soft/pnlpipe3/luigi-pnlpipe/params/cte/cnn_dwi_mask_params.cfg
# ========================================================================================


source /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu
NEW_SOFT_DIR=/rfanfs/pnl-zorro/software/pnlpipe3/


# for a caselist, this script must be run in a for loop
# https://github.com/pnlbwh/luigi-pnlpipe/wiki/Run-HCP-pipeline-on-PNL-GPU-machines-in-a-parallel-manner
if [ -f $caselist ]
then
    c=`head -${LSB_JOBINDEX} $caselist | tail -1`

    NUM_GPUS=`nvidia-smi -L | wc -l`
    export CUDA_VISIBLE_DEVICES=$(( ${LSB_JOBINDEX}%${NUM_GPUS} ))
else
    c=$caselist
fi


echo "1. run Luigi pipeline and prepare DWI for synb0 container"
export LUIGI_CONFIG_PATH
# source /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu \
/rfanfs/pnl-zorro/software/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --task CnnMask \
--bids-data-dir $BIDS_DATA_DIR \
--dwi-template "$DWI_TEMPLATE" \
-c ${c} -s ${s}
# double quotes around $DWI_TEMPLATE are mandatory



DERIVATIVES=$(dirname $BIDS_DATA_DIR)/derivatives/pnlpipe/
SES_FOLDER=$DERIVATIVES/sub-${c}/ses-${s}
pushd .
cd $SES_FOLDER
mkdir -p INPUTS OUTPUTS


if [ ! -z `ls $SES_FOLDER/dwi/*_desc-XcUnEdEp_dwi.nii.gz` ]
then
    echo $c was processed before
    exit
fi


echo "2. prepare b0 and T1 for synb0 container"
_unring_prefix=`ls dwi/sub-${c}_ses-${s}_*desc-XcUn_dwi.nii.gz`
unring_prefix=${_unring_prefix//.nii.gz}
unring_mask=`ls dwi/sub-${c}_ses-${s}_*desc-dwiXcUnCNN_mask.nii.gz`
if [ ! -f INPUTS/b0.nii.gz ]
then
    # source /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu && \
    fslmaths ${unring_prefix}.nii.gz -mul $unring_mask ${unring_prefix}.nii.gz && \
    bse.py -i ${unring_prefix}.nii.gz -o INPUTS/b0.nii.gz
fi

T1=anat/sub-${c}_ses-${s}_desc-XcMaN4_T1w.nii.gz
if [ -f $T1 ]
then
    cp $T1 INPUTS/T1.nii.gz
else
    echo "Run structural pipeline first:"
    echo "https://github.com/pnlbwh/luigi-pnlpipe/blob/hcp/docs/Process_DIAGNOSE-CTE_data.md#structural-pipeline"
fi

cp $ACQPARAMS INPUTS/
cp $INDEX INPUTS/


echo "3. run synb0 container"
TMPDIR=$HOME/tmp/
mkdir -p $TMPDIR
if [ ! -f OUTPUTS/b0_all_topup.nii.gz ]
then
    TMPDIR=$TMPDIR \
    singularity run -B INPUTS/:/INPUTS -B OUTPUTS/:/OUTPUTS \
    -B ${NEW_SOFT_DIR}/fs7.1.0/license.txt:/extra/freesurfer/license.txt \
    ${NEW_SOFT_DIR}/containers/synb0-disco_v3.0.sif --stripped
fi

echo "4. create mask of topup (synb0) corrected b0"
# CNN method
_caselist=$(mktemp --suffix=.txt)
realpath OUTPUTS/b0_all_topup.nii.gz > $_caselist
echo "0 0" > OUTPUTS/b0_all_topup.bval
# source /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu && \
dwi_masking.py -i $_caselist -f ${NEW_SOFT_DIR}/CNN-Diffusion-MRIBrain-Segmentation/model_folder
mask=`ls OUTPUTS/*-multi_BrainMask.nii.gz`
rm $_caselist
# BET method
# cd OUTPUTS/
# fslroi b0_all_topup.nii.gz _b0.nii.gz 0 1
# bet _b0.nii.gz b0_all_topup -m -n
# mask=`realpath b0_all_topup_mask.nii.gz`
# cd ..

if [ -z $mask ]
then
    echo topup mask creation failed
    exit 1
fi


eddy_out=OUTPUTS/sub-${c}_ses-${s}_dir-${dir}_desc-XcUnEdEp_dwi
# initial guess was masking the --imain would improve quality of eddy corrected DWI
# however, the b0_all_topup_mask is underinclusive
# so it only crops off the frontal distortion
# so omit masking at this step
# fslmaths ${unring_prefix}.nii.gz -mul $mask ${unring_prefix}.nii.gz
echo "5. run eddy_cuda"
# source /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu-cuda-10.2 && \
eddy_cuda \
  --imain=${unring_prefix}.nii.gz \
  --bvecs=${unring_prefix}.bvec \
  --bvals=${unring_prefix}.bval \
  --mask=$mask \
  --topup=OUTPUTS/topup \
  --acqp=INPUTS/acqparams.txt \
  --index=INPUTS/index.txt \
  --repol --data_is_shelled --verbose \
  --out=$eddy_out || { exit 1; }



echo "6. organize outputs"
# provide masked eddy_out for clarity, quality, and convenience
fslmaths ${eddy_out}.nii.gz -mul $mask ${eddy_out}.nii.gz

bids_prefix=dwi/sub-${c}_ses-${s}_dir-${dir}_desc-XcUnEdEp_dwi
mv ${eddy_out}.nii.gz ${bids_prefix}.nii.gz
mv ${eddy_out}.eddy_rotated_bvecs ${bids_prefix}.bvec
cp ${unring_prefix}.bval ${bids_prefix}.bval
mv $mask dwi/sub-${c}_ses-${s}_dir-${dir}_desc-dwiXcUnEdEp_mask.nii.gz



echo "Luigi-SynB0-Eddy pipeline has completed"
echo "See outputs at $PWD/dwi/"

popd

# for time profiling
date

