#!/usr/bin/env python

import argparse
from conversion import read_cases
from luigi import build
from _define_outputs import IO
from struct_pipe_t1_t2 import Freesurfer
from os.path import abspath

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='''pnlpipe glued together using Luigi, 
                                    optional parameters can be set by environment variable LUIGI_CONFIG_PATH, 
                                    see luigi-pnlpipe/scripts/struct_pipe_params.cfg as example''',
                                     formatter_class= argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--bids-data-dir', required= True, type=str, default= argparse.SUPPRESS,
                        help='/path/to/bids/data/directory')
    parser.add_argument('--caselist', required= True, type=str, default= argparse.SUPPRESS,
                        help='a txt file where each line is a caseid')
    parser.add_argument('--t1-template', type=str, default='sub-id/anat/*_T1w.nii.gz',
                        help='glob bids-data-dir/t1-template to find input data')
    parser.add_argument('--t2-template', type=str,
                        help='glob bids-data-dir/t2-template to find input data')
    parser.add_argument('--num-workers', type=int, default=1, help='number of Luigi workers')

    # parser.add_argument('--bids-derivatives', type= str, default='luigi-pnlpipe', help= 'name of bids derivatives directory')

    args = parser.parse_args()

    cases = read_cases(abspath(args.caselist))
    args.bids_data_dir= abspath(args.bids_data_dir)

    FsTasks = []
    for id in cases:
        inter = IO(id, args.bids_data_dir)

        # individual task with both t1 and t2
        FsTasks.append(Freesurfer(bids_data_dir=args.bids_data_dir,
                                  id=id,
                                  t1_template=args.t1_template,
                                  t2_template=args.t2_template,
                                  t1_align_prefix=inter['t1_align_prefix'],
                                  t1_mask_prefix=inter['t1_mabsmask_prefix'],
                                  t2_align_prefix=inter['t2_align_prefix'],
                                  t2_mask_prefix=inter['t2_mabsmask_prefix'],
                                  fs_dir=inter['fs_dir']))

    build(FsTasks, workers=args.num_workers)

