#!/usr/bin/env python

import argparse
from conversion import read_cases
from luigi import build
from _define_outputs import IO
from fs2dwi_pipe import Wmqlqc
from os.path import abspath, isfile

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='''pnlpipe glued together using Luigi, 
                                    optional parameters can be set by environment variable LUIGI_CONFIG_PATH, 
                                    see luigi-pnlpipe/scripts/struct_pipe_params.cfg as example''',
                                     formatter_class= argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--bids-data-dir', required= True, type=str, default= argparse.SUPPRESS,
                        help='/path/to/bids/data/directory')
    parser.add_argument('-c', required= True, type=str, default= argparse.SUPPRESS,
                        help='a single caseid or a .txt file where each line is a caseid')
    parser.add_argument('--dwi-template', type=str, default='sub-id/dwi/*_dwi.nii.gz',
                        help='glob bids-data-dir/t1-template to find input data')
    parser.add_argument('--t1-template', type=str, default='sub-id/anat/*_T1w.nii.gz',
                        help='glob bids-data-dir/t2-template to find input data')
    parser.add_argument('--t2-template', type=str,
                        help='glob bids-data-dir/t2-template to find input data')
    parser.add_argument('--num-workers', type=int, default=1, help='number of Luigi workers')

    # parser.add_argument('--bids-derivatives', type= str, default='luigi-pnlpipe', help= 'name of bids derivatives directory')

    args = parser.parse_args()
    
    cases = read_cases(abspath(args.c)) if isfile(abspath(args.c)) else [args.c]
    args.bids_data_dir= abspath(args.bids_data_dir)

    WmqlqcTasks = []
    for id in cases:
        inter = IO(id, args.bids_data_dir)

        if args.t2_template:
            WmqlqcTasks.append(Wmqlqc(bids_data_dir=args.bids_data_dir,
                                      id=id,
                                      dwi_template=args.dwi_template,
                                      dwi_align_prefix=inter['dwi_align_prefix'],
                                      eddy_prefix=inter['eddy_prefix'],
                                      eddy_epi_prefix=inter['eddy_epi_prefix'],
                                      eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                                      eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                                      eddy_epi_bse_masked_prefix=inter['eddy_epi_bse_masked_prefix'],
                                      eddy_epi_bse_betmask_prefix=inter['eddy_epi_bse_betmask_prefix'],
                                      t1_template=args.t1_template,
                                      t1_align_prefix=inter['t1_align_prefix'],
                                      t1_mask_prefix=inter['t1_mabsmask_prefix'],
                                      t2_template=args.t2_template,
                                      t2_align_prefix=inter['t2_align_prefix'],
                                      t2_mask_prefix=inter['t2_mabsmask_prefix'],
                                      fs_dir=inter['fs_dir'],
                                      mode='witht2',
                                      fs_in_dwi=inter['fs_in_epi'],
                                      tract_prefix=inter['eddy_epi_tract_prefix'],
                                      wmql_out=inter['epi_wmql_dir'],
                                      wmqlqc_out= inter['epi_wmqlqc_dir']))

        else:
            WmqlqcTasks.append(Wmqlqc(bids_data_dir=args.bids_data_dir,
                                      id=id,
                                      dwi_template=args.dwi_template,
                                      dwi_align_prefix=inter['dwi_align_prefix'],
                                      eddy_prefix=inter['eddy_prefix'],
                                      eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                                      eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                                      t1_template=args.t1_template,
                                      t1_align_prefix=inter['t1_align_prefix'],
                                      t1_mask_prefix=inter['t1_mabsmask_prefix'],
                                      t2_template=args.t2_template,
                                      t2_align_prefix=inter['t2_align_prefix'],
                                      t2_mask_prefix=inter['t2_mabsmask_prefix'],
                                      fs_dir=inter['fs_dir'],
                                      mode='direct',
                                      fs_in_dwi=inter['fs_in_eddy'],
                                      tract_prefix=inter['eddy_tract_prefix'],
                                      wmql_out=inter['eddy_wmql_dir'],
                                      wmqlqc_out= inter['eddy_wmqlqc_dir']))


    build(WmqlqcTasks, workers=args.num_workers)

