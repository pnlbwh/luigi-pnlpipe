## Guide for running tests

Table of Contents
=================

 * [Download Slicer](#download-slicer)
 * [Download test data](#download-test-data)
 * [Launch container](#launch-container)
 * [Run tests](#run-tests)



### Download Slicer

* Download a fresh Slicer-4.11.20200930-linux-amd64 locally
* Install SlicerDMRI extension module. It can be found at `~/.config/NA-MIC/Extensions-29402/SlicerDMRI`
* You can copy both the Slicer-4.11.20200930-linux-amd64 and SlicerDMRI into `/root` directory 
for ease of mounting.


### Download test data

This step is intended for eliminating sluggishness involved in downloading test data from Dropbox repeatedly. 
You can have both `luigi-pnlpipe-test-data` and `luigi-pnlpipe-g-truth` downloaded in your machine. 
This approach is particularly useful when you would have to rebuild the Docker container. If you download them 
inside the container, then they would be lost during rebuild. But if they are downloaded locally once, 
you can mount them into your container after a rebuild.

https://www.dropbox.com/s/pzloevkr8h3kyac/luigi-pnlpipe-test-data.tar.gz

https://www.dropbox.com/s/gi7kukud44bl6p2/luigi-pnlpipe-g-truth.tar.gz


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
