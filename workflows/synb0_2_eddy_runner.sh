#!/bin/bash

# A POSIX variable
OPTIND=1         # Reset in case getopts has been used previously in the shell.

# Initialize our own variables to empty strings
ROOT_PATH=""
SUB_ID=""
SES=""
DWI_IDENTIFIER=""
DWI_TEMPLATE=""
INDEX_PATH=""
ACQPARAMS_PATH=""

show_help() {
    echo "Usage:"
    echo "./synb0_2_eddy_runner.sh [options]"
    echo
    echo "Options:"
    echo "   -i, --id             Specify subject ID (required)"
    echo "   -r, --root           Specify root path"
    echo "                        Default: /data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/pnlpipe"
    echo "   -s, --session        Specify session. Default: 01"
    echo "   -d, --dwi-identifier Specify DWI identifier"
    echo "                        Default: acq-AP_dir-80_desc-XcUn_dwi"
    echo "   -t, --template       Specify DWI template for Luigi CNN masking step"
    echo "                        Default: sub-*/ses-*/dwi/*_\${dwi-itentifier}.nii.gz"
    echo "   -x, --index          Specify path to index.txt"
    echo "                        Default: /data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/index.txt"
    echo "   -a, --acqparams      Specify path to acqparams.txt"
    echo "                        Default: /data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/acqparams.txt"
    echo
    echo "For help or questions about this script please reach out to rzurrin@bwh.harvard.edu for further assistance."
}

while (( "$#" )); do
  case "$1" in
    -h|--help)
      show_help
      exit 0
      ;;
    -i|--id)
      SUB_ID=$2
      shift 2
      ;;
    -r|--root)
      ROOT_PATH=$2
      shift 2
      ;;
    -s|--session)
      SES=$2
      shift 2
      ;;
    -d|--dwi-identifier)
      DWI_IDENTIFIER=$2
      shift 2
      ;;
    -t|--template)
      DWI_TEMPLATE=$2
      shift 2
      ;;
    -x|--index)
      INDEX_PATH=$2
      shift 2
      ;;
    -a|--acqparams)
      ACQPARAMS_PATH=$2
      shift 2
      ;;
    --) # end argument parsing
      shift
      break
      ;;
    -*) # unsupported flags
      echo "Error: Unsupported flag $1" >&2
      show_help
      exit 1
      ;;
    *) # preserve positional arguments
      PARAMS="$PARAMS $1"
      shift
      ;;
  esac
done


# Check if SUB_ID is not empty, if it is, show help and exit
if [ -z "$SUB_ID" ]; then
    show_help
    exit 1
fi

##############################        ATTENTION USERS        ##################################
# Set default's for ROOT_PATH, SES, DWI_IDENTIFIER, DWI_TEMPLATE, INDEX_PATH, ACQPARAMS_PATH. #
#                                                                                             #
#  OPTIONAL VARIABLES ONLY NEED TO BE CHANGED HERE IF YOU DO NOT WANT TO PASS ARGUMENTS       #
#  THROUGH THE TERMINAL AND WISH FOR THEM TO BE DIFFERENT.                                    #
###############################################################################################
ROOT_PATH=${ROOT_PATH:-"/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/pnlpipe"}
SES=${SES:-"01"}
DWI_IDENTIFIER=${DWI_IDENTIFIER:-"acq-AP_dir-80_desc-XcUn_dwi"}
DWI_TEMPLATE=${DWI_TEMPLATE:-"sub-*/ses-*/dwi/*_${DWI_IDENTIFIER}.nii.gz"}
INDEX_PATH=${INDEX_PATH:-"/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/index.txt"}
ACQPARAMS_PATH=${ACQPARAMS_PATH:-"/data/pnl/Collaborators/CMA/mtsintou/Emotion/derivatives/acqparams.txt"}
###############################################################################################

# Remove trailing slash from ROOT_PATH if present
ROOT_PATH="${ROOT_PATH%/}"

# print the root path
echo "Root path: $ROOT_PATH"

# Construct the subject's session folder
SES_FOLDER="$ROOT_PATH/sub-$SUB_ID/ses-${SES}"

# print the session folder
echo "Session folder: $SES_FOLDER"

# Change the working directory to the session folder
cd "$SES_FOLDER" || { echo "Error: Unable to change directory."; exit 1; }

## Create INPUTS and OUTPUTS directories
mkdir -p INPUTS OUTPUTS || { echo "Error: Unable to create directories."; exit 1; }


# Check if bse.py is available
if ! command -v bse.py >/dev/null 2>&1; then
    # If not available, try to source the pnlpipe3 environment
    if [ -f "/rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu-cuda-10.2" ]; then
        echo "bse.py not found. Sourcing /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu-cuda-10.2..."
        source /rfanfs/pnl-zorro/software/pnlpipe3/bashrc3-gpu
        # Check again if bse.py is available
        command -v bse.py >/dev/null 2>&1 || \
        { echo >&2 "bse.py is still not available. Please check your environment."; exit 1; }
    else
        echo >&2 "bse.py is not available. Please source the environment containing bse.py."
        exit 1
    fi
fi

# Check for Qc mask file exists in the dwi directory
qc_mask_path="dwi/sub-${SUB_ID}_ses-${SES}_acq-AP_dir-80_desc-dwiXcUn_desc-XcUnCNNQc_mask.nii.gz"

# Check if non Qc mask file exists in the dwi directory
mask_path="dwi/sub-${SUB_ID}_ses-${SES}_acq-AP_dir-80_desc-dwiXcUn_desc-XcUnCNN_mask.nii.gz"

if [ -f $qc_mask_path ]; then
    mask_path=$qc_mask_path
    echo "Qc Mask found."
elif [ ! -f $mask_path ]; then
    echo "Mask not found. Running luigi pipeline to generate mask."

    # Update LUIGI_CONFIG_PATH to point to the correct config file
    export LUIGI_CONFIG_PATH=/data/pnl/soft/pnlpipe3/luigi-pnlpipe/params/cte/cnn_dwi_mask_params.cfg

    # Run the luigi task to generate the mask
    /data/pnl/soft/pnlpipe3/luigi-pnlpipe/exec/ExecuteTask --task CnnMask \
    --bids-data-dir $ROOT_PATH \
    --dwi-template "$DWI_TEMPLATE" \
    -c $SUB_ID -s $SES
else
    echo "Non Qc Mask found."
fi

# Run bse.py on the specific dwi file and save the output to INPUTS folder
bse.py -i "dwi/sub-${SUB_ID}_ses-${SES}_${DWI_IDENTIFIER}.nii.gz" -o INPUTS/b0.nii.gz \
|| { echo "Error: bse.py failed."; exit 1; }

# Copy acqparams.txt to INPUTS folder
# symlink won't work because target of symlink is not mounted in singularity container
cp -f ${ACQPARAMS_PATH} INPUTS/ || { echo "Error: Unable to copy acqparams.txt."; exit 1; }

# Copy T1 image to INPUTS folder and rename
cp -f "anat/sub-${SUB_ID}_ses-${SES}_desc-XcMaN4_T1w.nii.gz" INPUTS/T1.nii.gz \
|| { echo "Error: Unable to copy T1 image."; exit 1; }

# Run the singularity container (removed the -e flag)
singularity run -B INPUTS/:/INPUTS -B OUTPUTS/:/OUTPUTS \
-B /data/pnl/soft/pnlpipe3/fs7.1.0/license.txt:/extra/freesurfer/license.txt \
/data/pnl/soft/pnlpipe3/containers/synb0-disco_v3.0.sif --stripped \
|| { echo "Error: singularity run failed."; exit 1; }

# Create a symbolic link to index.txt in INPUTS folder for eddy_cuda
ln -s ${INDEX_PATH} INPUTS/ || { echo "Error: Unable to create a symbolic link to index.txt."; exit 1; }


echo "Running eddy_cuda10.2..."
export CUDA_VISIBLE_DEVICES=1
# Continue with the eddy_cuda processing
eddy_cuda10.2 \
  --imain="dwi/sub-${SUB_ID}_ses-${SES}_${DWI_IDENTIFIER}.nii.gz" \
  --bvecs="dwi/sub-${SUB_ID}_ses-${SES}_${DWI_IDENTIFIER}.bvec" \
  --bvals="dwi/sub-${SUB_ID}_ses-${SES}_${DWI_IDENTIFIER}.bval" \
  --mask=$mask_path \
  --topup="OUTPUTS/topup" \
  --acqp="INPUTS/acqparams.txt" \
  --index="INPUTS/index.txt" \
  --repol --data_is_shelled --verbose \
  --out="OUTPUTS/sub-${SUB_ID}_ses-${SES}_dir-80_desc-XcUnEdEp_dwi"


# organize outputs
cd dwi/ || { echo "Error: Unable to change to the dwi directory."; exit 1; }
mv ${SES_FOLDER}/OUTPUTS/sub-${SUB_ID}_ses-${SES}_dir-80_desc-XcUnEdEp_dwi.nii.gz .
mv ${SES_FOLDER}/OUTPUTS/sub-${SUB_ID}_ses-${SES}_dir-80_desc-XcUnEdEp_dwi.eddy_rotated_bvecs sub-${SUB_ID}_ses-${SES}_dir-80_desc-XcUnEdEp_dwi.bvec
ln -s sub-${SUB_ID}_ses-${SES}_${DWI_IDENTIFIER}.bval sub-${SUB_ID}_ses-${SES}_dir-80_desc-XcUnEdEp_dwi.bval
ln -s sub-${SUB_ID}_ses-${SES}_dir-80_desc-dwiXcUnEdEp_mask.nii.gz sub-${SUB_ID}_ses-${SES}_dir-80_desc-dwiXcUn_mask.nii.gz

echo "synb0 to eddy pipeline has finished running."