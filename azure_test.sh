#!/usr/bin/bash

cd /home/pnlbwh
git clone --single-branch --branch azure https://github.com/pnlbwh/luigi-pnlpipe.git


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
mkdir bin
export PATH=$HOME/bin:$PATH
echo "mv $HOME/rawdata/freesurfer $HOME/derivatives/pnlpipe/sub-1004/ses-01/anat/" > ~/bin/recon-all
chmod +x bin/recon-all


# provide *_pipe_params
pip install luigi sqlalchemy
cd luigi-pnlpipe
export LUIGI_CONFIG_PATH=`pwd`/params/struct_pipe_params.cfg


# define PATH and PYTHONPATH
export PATH=`pwd`/scripts/:$PATH
export PYTHONPATH=`pwd`:$PYTHONPATH


# run pipeline
workflows/ExecuteTask.py --task StructMask --bids-data-dir $HOME/rawdata -c 1004 -s 01 --t1-template sub-*/ses-01/anat/*_T1w.nii.gz


