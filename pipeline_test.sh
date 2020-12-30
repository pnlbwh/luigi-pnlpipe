#!/usr/bin/bash

set -eo pipefail

cd /home/pnlbwh

# pushd .
# cd luigi-pnlpipe
# git reset --hard
# git checkout $BRANCH
# git pull origin $BRANCH
# popd


# download test data
test_data=luigi-pnlpipe-test-data.tar.gz
if [ ! -f $test_data ]
then
    wget https://www.dropbox.com/s/pzloevkr8h3kyac/$test_data

    tar -xzvf $test_data


    # download and shorten T2w test data
    if [ ! -d trainingDataT2Masks ]
    then
        git clone https://github.com/pnlbwh/trainingDataT2Masks.git
        pushd .
        cd trainingDataT2Masks
        ./mktrainingcsv.sh .

        head -n 5 trainingDataT2Masks-hdr.csv > trainingDataT2Masks-curt.csv
        popd
    fi
fi


# hack recon-all
sed -i "361s+cmd+'mv $HOME/CTE/rawdata/freesurfer $HOME/CTE/derivatives/pnlpipe/sub-1004/ses-01/anat/'+g" luigi-pnlpipe/workflows/struct_pipe.py


cd luigi-pnlpipe

### CTE ###


## structural pipeline ##
export LUIGI_CONFIG_PATH=`pwd`/test_params/struct_pipe_params.cfg

# test of StructMask
workflows/ExecuteTask.py --task StructMask --bids-data-dir $HOME/CTE/rawdata -c 1004 -s 01 \
--t2-template sub-*/ses-01/anat/*_T2w.nii.gz


# test of Freesurfer
workflows/ExecuteTask.py --task Freesurfer --bids-data-dir $HOME/CTE/rawdata -c 1004 -s 01 \
--t1-template sub-*/ses-01/anat/*_T1w.nii.gz --t2-template sub-*/ses-01/anat/*_T2w.nii.gz



## dwi pipeline ##
export LUIGI_CONFIG_PATH=`pwd`/test_params/dwi_pipe_params.cfg

# test of EddyEpi (FslEddy+PnlEpi) and Ukf
workflows/ExecuteTask.py --task Ukf --bids-data-dir $HOME/CTE/rawdata -c 1004 -s 01 \
--dwi-template sub-*/ses-01/dwi/*_dwi.nii.gz --t2-template sub-*/ses-01/anat/*_AXT2.nii.gz


# test of EddyEpi (PnlEddy)
# replace eddy_task in dwi_pipe_params
sed -i "s/eddy_task:\ FslEddy/eddy_task:\ PnlEddy/g" test_params/dwi_pipe_params.cfg
# delete *Ed_dwi.nii.gz
rm $HOME/CTE/derivatives/pnlpipe/sub-*/ses-*/dwi/*Ed_dwi.nii.gz

workflows/ExecuteTask.py --task EddyEpi --bids-data-dir $HOME/CTE/rawdata -c 1004 -s 01 \
--dwi-template sub-*/ses-01/dwi/*_dwi.nii.gz --t2-template sub-*/ses-01/anat/*_AXT2.nii.gz



## fs2dwi pipeline ##
export LUIGI_CONFIG_PATH=`pwd`/test_params/fs2dwi_pipe_params.cfg

# test of Wmql
# delete *_T2w*nii.gz
rm $HOME/CTE/derivatives/pnlpipe/sub-*/ses-*/anat/*_T2w*
workflows/ExecuteTask.py --task Wmql --bids-data-dir $HOME/CTE/rawdata -c 1004 -s 01 \
--dwi-template sub-*/ses-*/dwi/*EdEp_dwi.nii.gz --t2-template sub-*/ses-*/anat/*_T2w.nii.gz



### HCP ###

## dwi pipeline ##
export LUIGI_CONFIG_PATH=`pwd`/test_params/dwi_pipe_params.cfg

# test of EddyEpi (TopupEddy) and Ukf
# replace eddy_epi_task, acqp, index in dwi_pipe_params
sed -i "s/eddy_epi_task:\ PnlEddy/eddy_task:\ topupeddy/g" test_params/dwi_pipe_params.cfg
sed -i "s/acqp.txt/acqp_ap_pa.txt/g" test_params/dwi_pipe_params.cfg
sed -i "s/index.txt//g" test_params/dwi_pipe_params.cfg

workflows/ExecuteTask.py --task Ukf --bids-data-dir $HOME/HCP/rawdata -c 1042 -s 1 \
--dwi-template sub-*/ses-*/dwi/*acq-PA_dwi.nii.gz,sub-*/ses-*/dwi/*acq-AP_dwi.nii.gz

