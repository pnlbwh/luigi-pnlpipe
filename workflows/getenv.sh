#!/usr/bin/bash

cmd="git rev-parse --short=7 HEAD"

cd `dirname $0`/..

log_file=$1
[ -z $log_file ] && log_file=`pwd`/hashes.txt

# luigi-pnlpipe hash
echo luigi-pnlpipe,`$cmd` > $log_file

# pnlNipype hash
cd ../pnlNipype
echo pnlNipype,`$cmd` >> $log_file

# ANTs, UKFTractography, dcm2niix hashes
antsRegistration --version | head -n 1 | sed 's/ Version: /,/' >> $log_file
echo UKFTractography,$(cd $(dirname `which UKFTractography`) && git rev-parse --short=7 HEAD) >> $log_file
echo dcm2niix,`dcm2niix --version | tail -n 1` >> $log_file

# FSL version
echo FSL,`cat $FSLDIR/etc/fslversion` >> $log_file

# FreeSurfer version
echo FreeSurfer,`cat $FREESURFER_HOME/build-stamp.txt` >> $log_file

# Linux version
echo Computer,`cat /etc/system-release` `uname -nr` >> $log_file

# NVIDIA version
echo NVIDIA,`nvidia-smi | grep NVIDIA-SMI` >> $log_file

# GPUs
echo GPUs,`nvidia-smi -L` >> $log_file

