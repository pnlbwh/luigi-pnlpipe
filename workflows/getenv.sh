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

# pnlpipe hash
cd ../pnlpipe
echo pnlpipe,`$cmd` >> $log_file

# ANTs, UKFTractography, dcm2niix, tract_querier hashes
cd pnlpipe_software
for s in ANTs UKFTractography dcm2niix tract_querier
do
    hash_line=`grep "DEFAULT_HASH = " $s.py`
    IFS=" = ", read -ra tmp <<< $hash_line
    hash=`echo ${tmp[1]} | sed "s/'//g"`
    echo $s,$hash >> $log_file
done


# FSL version
hash_line=`eddy_openmp --help 2>&1 | grep "Part of FSL"`
IFS=:, read -ra tmp <<< $hash_line
hash=`echo ${tmp[1]} | sed "s/)//"`
echo FSL,$hash >> $log_file

# FreeSurfer version
echo FreeSurfer,`cat $FREESURFER_HOME/build-stamp.txt` >> $log_file

