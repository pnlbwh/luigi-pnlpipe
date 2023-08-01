#!/bin/bash


# User will edit only this block =========================================================
# caselist=/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/all_80_and_01_cases.txt
caselist=B15915
s=01
dir=80
acq=AP
BIDS_DATA_DIR=/data/pnl/Collaborators/CMA/mtsintou/Emotion/rawdata
DWI_TEMPLATE=sub-*/ses-*/dwi/sub-*_ses-*_acq-${acq}_dir-${dir}_dwi.nii.gz
INDEX=/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/index.txt
ACQPARAMS=/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/acqparams.txt
LUIGI_CONFIG_PATH=/data/pnl/soft/pnlpipe3/luigi-pnlpipe/params/cte/cnn_dwi_mask_params.cfg
# ========================================================================================



# for a caselist, this script must be run in a for loop
# https://github.com/pnlbwh/luigi-pnlpipe/wiki/Run-HCP-pipeline-on-PNL-GPU-machines-in-a-parallel-manner
if [ -f $caselist ]
then
    c=`head -${LSB_JOBINDEX} $caselist | tail -1`
    export CUDA_VISIBLE_DEVICES=$(( ${LSB_JOBINDEX}%2 ))
else
    c=$caselist
fi



source /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu-cuda-10.2



echo "1. run Luigi pipeline and prepare DWI for synb0 container"
export LUIGI_CONFIG_PATH
/data/pnl/soft/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --task GibbsUn \
--bids-data-dir $BIDS_DATA_DIR \
--dwi-template "$DWI_TEMPLATE" \
-c ${c} -s ${s}
# double quotes around $DWI_TEMPLATE are mandatory



DERIVATIVES=$(dirname $BIDS_DATA_DIR)/derivatives/pnlpipe/
SES_FOLDER=$DERIVATIVES/sub-${c}/ses-${s}
pushd .
cd $SES_FOLDER
mkdir -p INPUTS OUTPUTS



echo "2. prepare b0 and T1 for synb0 container"
unring_prefix=dwi/sub-${c}_ses-${s}_acq-${acq}_dir-${dir}_desc-XcUn_dwi
if [ ! -f INPUTS/b0.nii.gz ]
then
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
TMPDIR=$TMPDIR \
singularity run -B INPUTS/:/INPUTS -B OUTPUTS/:/OUTPUTS \
-B ${NEW_SOFT_DIR}/fs7.1.0/license.txt:/extra/freesurfer/license.txt \
${NEW_SOFT_DIR}/containers/synb0-disco_v3.0.sif --stripped



echo "4. create mask of topup (synb0) corrected b0"
# _caselist=$(mktemp --suffix=.txt)
# realpath OUTPUTS/b0_all_topup.nii.gz > $_caselist
# echo "0 0" > OUTPUTS/b0_all_topup.bval
# dwi_masking.py -i $_caselist -f ${NEW_SOFT_DIR}/CNN-Diffusion-MRIBrain-Segmentation/model_folder
# mask=`ls OUTPUTS/*-multi_BrainMask.nii.gz`
# rm $_caselist
# CNN brain masking program fails for the above b0_all_topup.nii.gz
# we believe because the CNN was not trained to predict on such low quality b0
# so falling back to bet
cd OUTPUTS/
fslroi b0_all_topup.nii.gz _b0.nii.gz 0 1
bet _b0.nii.gz b0_all_topup -m -n
mask=`realpath b0_all_topup_mask.nii.gz`
cd ..



eddy_out=OUTPUTS/sub-${c}_ses-${s}_dir-${dir}_desc-XcUnEdEp_dwi
echo "5. run eddy_cuda10.2"
eddy_cuda10.2 \
  --imain=${unring_prefix}.nii.gz \
  --bvecs=${unring_prefix}.bvec \
  --bvals=${unring_prefix}.bval \
  --mask=$mask \
  --topup=OUTPUTS/topup \
  --acqp=INPUTS/acqparams.txt \
  --index=INPUTS/index.txt \
  --repol --data_is_shelled --verbose \
  --out=$eddy_out



echo "6. organize outputs"
bids_prefix=dwi/sub-${c}_ses-${s}_dir-${dir}_desc-XcUnEdEp_dwi
mv ${eddy_out}.nii.gz ${bids_prefix}.nii.gz
mv ${eddy_out}.eddy_rotated_bvecs ${bids_prefix}.bvec
cp ${unring_prefix}.bval ${bids_prefix}.bval
mv $mask dwi/sub-${c}_ses-${s}_dir-${dir}_desc-dwiXcUnEdEp_mask.nii.gz



popd
echo "Luigi-SynB0-Eddy pipeline has completed"


