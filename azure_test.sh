#!/usr/bin/bash

cd /home/pnlbwh
git clone --single-branch --branch $BRANCH https://github.com/pnlbwh/luigi-pnlpipe.git


# download test data
wget https://www.dropbox.com/s/wqt4gdbuhuqbg6u/for_azure_test.tar.gz
tar -xzvf for_azure_test.tar.gz
mv for_azure_test rawdata/


# shorten T2w test data
git clone https://github.com/pnlbwh/trainingDataT2Masks.git
pushd .
cd trainingDataT2Masks
./mktrainingcsv.sh .
head -n 5 trainingDataT2Masks-hdr.csv > trainingDataT2Masks-curt.csv
popd


# hack recon-all
sed -i "356s+cmd+'mv $HOME/rawdata/freesurfer $HOME/derivatives/pnlpipe/sub-1004/ses-01/anat/'+g" struct_pipe.py


# provide *_pipe_params
pip install luigi sqlalchemy
cd luigi-pnlpipe
export LUIGI_CONFIG_PATH=`pwd`/params/struct_pipe_params.cfg


# define PATH and PYTHONPATH
export PATH=`pwd`/scripts/:$PATH
export PYTHONPATH=`pwd`:$PYTHONPATH


# run pipeline
workflows/ExecuteTask.py --task StructMask --bids-data-dir $HOME/rawdata -c 1004 -s 01 --t2-template sub-*/ses-01/anat/*_T2w.nii.gz

workflows/ExecuteTask.py --task Freesurfer --bids-data-dir $HOME/rawdata -c 1004 -s 01 --t1-template sub-*/ses-01/anat/*_T1w.nii.gz --t2-template sub-*/ses-01/anat/*_T2w.nii.gz


