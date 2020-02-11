![](./pnl-bwh-hms.png)

Developed by Tashrif Billah and Sylvain Bouix, and Yogesh Rathi, Brigham and Women's Hospital (Harvard Medical School).



> luigi-pnlpipe/scripts/ExecuteTask.py -h

```bash
usage: ExecuteTask.py [-h] --bids-data-dir BIDS_DATA_DIR -c C
                      [--dwi-template DWI_TEMPLATE]
                      [--t1-template T1_TEMPLATE] [--t2-template T2_TEMPLATE]
                      --task
                      {Freesurfer,PnlEddy,PnlEddyEpi,Ukf,Fs2Dwi,Wmql,Wmqlqc}
                      [--num-workers NUM_WORKERS]

pnlpipe glued together using Luigi, optional parameters can be set by
environment variable LUIGI_CONFIG_PATH, see luigi-
pnlpipe/scripts/struct_pipe_params.cfg as example

optional arguments:
  -h, --help            show this help message and exit
  --bids-data-dir BIDS_DATA_DIR
                        /path/to/bids/data/directory
  -c C                  a single caseid or a .txt file where each line is a
                        caseid
  --dwi-template DWI_TEMPLATE
                        glob bids-data-dir/t1-template to find input data
                        (default: sub-id/dwi/*_dwi.nii.gz)
  --t1-template T1_TEMPLATE
                        glob bids-data-dir/t2-template to find input data
                        (default: sub-id/anat/*_T1w.nii.gz)
  --t2-template T2_TEMPLATE
                        glob bids-data-dir/t2-template to find input data
                        (default: None)
  --task {Freesurfer,PnlEddy,PnlEddyEpi,Ukf,Fs2Dwi,Wmql,Wmqlqc}
                        number of Luigi workers (default: None)
  --num-workers NUM_WORKERS
                        number of Luigi workers (default: 1)


```


# Workstation

## Launch job

> luigi/scripts/ExecuteTask.py --task Freesurfer --bids-data-dir ~/INTRuST_BIDS -c ~/INTRuST_BIDS/caselist.txt

## Monitor progress
> firefox https://localhost:8082

# HPC cluster

## Launch job
Save the following as `run.lsf`

```bash
#!/bin/bash

# Copy this file to your project folder (usually called run.lsf), change
# NAME_OF_JOB and NUM_CORES below, edit the command to be run, and then start a
# cluster job by running: 
#     bsub < run.lsf

source /PHShome/tb571/luigi-pnlpipe/scripts/luigi_env

#BSUB -J luigi-pnlpipe
#BSUB -o %J.out
#BSUB -e %J.err
#BSUB -q big
#BSUB -n 4


luigid --logdir /PHShome/tb571/Downloads/luigi-pnlpipe/scripts/luigi-server.log --background

for id in $(cat ~/INTRuST_BIDS/caselist.txt)
do
    luigi/scripts/ExecuteTask.py --task Freesurfer --bids-data-dir ~/Downloads/INTRuST_BIDS/ --caselist $id
done
```

Then

> bsub < run.lsf


## Monitor progress
> bjobs

> firefox https://node.research.partners.org:8082