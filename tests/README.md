## Guide for running tests

### Download a Slicer

### Launch container


    docker run --rm -ti \
    # mount SlicerDMRI
    -v `pwd`/Slicer-4.11.20200930-linux-amd64:/Slicer-4.11 \
    -v `pwd`/SlicerDMRI:/SlicerDMRI \
    # mount ground truth
    -v /home/tb571/tmp/Reference/:/home/pnlbwh/luigi-pnlpipe/Reference \
    # mount FreeSurfer license
    -v /home/tb571/freesurfer/license.txt:/home/pnlbwh/freesurfer-7.1.0/license.txt \
    tbillah/pnlpipe:latest


### Run tests

    luigi-pnlpipe/pipeline_test.sh -h
