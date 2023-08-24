#!/bin/bash

# for time profiling
date

# User will edit only this block =========================================================
caselist=$1
s=01
dir=80
acq=AP

# New variables introduced
SUB_PREFIX="sub-"
SES_PREFIX="ses-"
DWI_PREFIX=""
T1W_PREFIX=""
[ -n "$acq" ] && ACQ_STR="acq-${acq}_" || ACQ_STR=""
[ -n "$dir" ] && DIR_STR="dir-${dir}_" || DIR_STR=""

BIDS_DATA_DIR=/data/pnl/Collaborators/CMA/mtsintou/Emotion/rawdata
DWI_TEMPLATE=${SUB_PREFIX}*/${SES_PREFIX}*/dwi/${SUB_PREFIX}*_${SES_PREFIX}*_${DWI_PREFIX}${ACQ_STR}${DIR_STR}dwi.nii.gz
INDEX=/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/index.txt
ACQPARAMS=/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/acqparams.txt
LUIGI_CONFIG_PATH=/data/pnl/soft/pnlpipe3/luigi-pnlpipe/params/cte/cnn_dwi_mask_params.cfg
# ========================================================================================

source /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu
NEW_SOFT_DIR=/rfanfs/pnl-zorro/software/pnlpipe3/

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
/rfanfs/pnl-zorro/software/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --task CnnMask \
--bids-data-dir $BIDS_DATA_DIR \
--dwi-template "$DWI_TEMPLATE" \
-c ${c} -s ${s}

DERIVATIVES=$(dirname $BIDS_DATA_DIR)/derivatives/pnlpipe/
SES_FOLDER=$DERIVATIVES/${SUB_PREFIX}${c}/${SES_PREFIX}${s}
pushd .
cd $SES_FOLDER
mkdir -p INPUTS OUTPUTS

if [ ! -z `ls $SES_FOLDER/dwi/*_desc-XcUnEdEp_dwi.nii.gz` ]
then
    echo $c was processed before
    exit
fi

echo "2. prepare b0 and T1 for synb0 container"
unring_prefix=dwi/${SUB_PREFIX}${c}_${SES_PREFIX}${s}_${DWI_PREFIX}${ACQ_STR}${DIR_STR}desc-XcUn_dwi
unring_mask=dwi/${SUB_PREFIX}${c}_${SES_PREFIX}${s}_${DWI_PREFIX}${ACQ_STR}${DIR_STR}desc-dwiXcUnCNN_mask.nii.gz

if [ ! -f INPUTS/b0.nii.gz ]
then
    fslmaths ${unring_prefix}.nii.gz -mul $unring_mask ${unring_prefix}.nii.gz && \
    bse.py -i ${unring_prefix}.nii.gz -o INPUTS/b0.nii.gz
fi

T1=anat/${SUB_PREFIX}${c}_${SES_PREFIX}${s}_${T1W_PREFIX}T1w.nii.gz
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
_caselist=$(mktemp --suffix=.txt)
realpath OUTPUTS/b0_all_topup.nii.gz > $_caselist
echo "0 0" > OUTPUTS/b0_all_topup.bval
dwi_masking.py -i $_caselist -f ${NEW_SOFT_DIR}/CNN-Diffusion-MRIBrain-Segmentation/model_folder
mask=`ls OUTPUTS/*-multi_BrainMask.nii.gz`
rm $_caselist

if [ -z $mask ]
then
    echo topup mask creation failed
    exit 1
fi

eddy_out=OUTPUTS/${SUB_PREFIX}${c}_${SES_PREFIX}${s}_${DIR_STR}desc-XcUnEdEp_dwi

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
fslmaths ${eddy_out}.nii.gz -mul $mask ${eddy_out}.nii.gz

bids_prefix=dwi/${SUB_PREFIX}${c}_${SES_PREFIX}${s}_${DIR_STR}desc-XcUnEdEp_dwi
mv ${eddy_out}.nii.gz ${bids_prefix}.nii.gz
mv ${eddy_out}.eddy_rotated_bvecs ${bids_prefix}.bvec
cp ${unring_prefix}.bval ${bids_prefix}.bval
mv $mask dwi/${SUB_PREFIX}${c}_${SES_PREFIX}${s}_${DIR_STR}desc-dwiXcUnEdEp_mask.nii.gz

echo "Luigi-SynB0-Eddy pipeline has completed"
echo "See outputs at $PWD/dwi/"

popd

# for time profiling
date
