#!/bin/bash

# for time profiling
date

unring_prefix=${1//.nii.gz/}
b0=$2
T1=$3
eddy_prefix=${4//.nii.gz/}
eddy_mask=$5
eddy_bse=$6
ACQPARAMS=$7
INDEX=$8


pushd .
SES_FOLDER=$(dirname $(dirname $unring_prefix))
cd $SES_FOLDER
mkdir -p INPUTS OUTPUTS

cp $b0 INPUTS/b0.nii.gz
cp $T1 INPUTS/T1.nii.gz

cp $ACQPARAMS INPUTS/
cp $INDEX INPUTS/


echo "3. run synb0 container"
TMPDIR=$HOME/tmp/
mkdir -p $TMPDIR
if [ ! -f OUTPUTS/b0_all_topup.nii.gz ]
then
    TMPDIR=$TMPDIR \
    singularity run -e -B INPUTS/:/INPUTS -B OUTPUTS/:/OUTPUTS \
    -B ${FREESURFER_HOME}/license.txt:/extra/freesurfer/license.txt \
    ${NEW_SOFT_DIR}/containers/synb0-disco_v3.0.sif --stripped
fi

echo "4. create mask of topup (synb0) corrected b0"
# CNN method
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


_eddy_out=OUTPUTS/$(basename $eddy_prefix)
echo "5. run eddy_cuda"
eddy_cuda \
  --imain=${unring_prefix}.nii.gz \
  --bvecs=${unring_prefix}.bvec \
  --bvals=${unring_prefix}.bval \
  --mask=$mask \
  --topup=OUTPUTS/topup \
  --acqp=INPUTS/acqparams.txt \
  --index=INPUTS/index.txt \
  --repol --data_is_shelled --verbose \
  --out=${_eddy_out} || { exit 1; }



echo "6. organize outputs"
# provide masked eddy_out for clarity, quality, and convenience
fslmaths ${_eddy_out}.nii.gz -mul $mask ${_eddy_out}.nii.gz

mv ${_eddy_out}.nii.gz ${eddy_prefix}.nii.gz
mv ${_eddy_out}.eddy_rotated_bvecs ${eddy_prefix}.bvec
cp ${unring_prefix}.bval ${eddy_prefix}.bval

mv $mask $eddy_mask
mv OUTPUTS/b0_all_topup_bse.nii.gz $eddy_bse



echo "Luigi-SynB0-Eddy pipeline has completed"
echo "See outputs at $PWD/dwi/"

popd

# for time profiling
date

