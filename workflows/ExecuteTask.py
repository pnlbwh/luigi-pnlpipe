#!/usr/bin/env python

import argparse
from conversion import read_cases
from luigi import build, configuration
from _define_outputs import IO
from struct_pipe import StructMask, Freesurfer
# TODO remove FslEddyEpi
from dwi_pipe import CnnMask, PnlEddy, FslEddy, FslEddyEpi, \
    TopupEddy, EddyEpi, Ukf
from fs2dwi_pipe import Fs2Dwi, Wmql, Wmqlqc
from scripts.util import abspath, isfile, pjoin, LIBDIR
from os import getenv, stat

if __name__ == '__main__':
    
    config = configuration.get_config()
    config.read(pjoin(LIBDIR, 'luigi.cfg'))

    parser = argparse.ArgumentParser(description='''pnlpipe glued together using Luigi, 
                                    optional parameters can be set by environment variable LUIGI_CONFIG_PATH, 
                                    see luigi-pnlpipe/scripts/params/*.cfg as examples''',
                                     formatter_class= argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--bids-data-dir', required= True, type=str, default= argparse.SUPPRESS,
                        help='/path/to/bids/data/directory')

    parser.add_argument('-c', required= True, type=str, default= argparse.SUPPRESS,
                        help='a single case ID or a .txt file where each line is a case ID')

    parser.add_argument('-s', required= True, type=str, default= argparse.SUPPRESS,
                        help='a single session ID or a .txt file where each line is a session ID')
    
    parser.add_argument('--dwi-template', type=str, default='sub-*/dwi/*_dwi.nii.gz',
                        help='dwi pipeline: glob bids-data-dir/dwi-template to find input data e.g. sub-*/ses-*/dwi/*_dwi.nii.gz, '
                             'fs2dwi pipeline: glob bids-data-dir/derivatives/derivatives-name/dwi-template to find input data')

    parser.add_argument('--t1-template', type=str, default='sub-*/anat/*_T1w.nii.gz',
                        help='glob bids-data-dir/t1-template to find input data e.g. sub-*/ses-*/anat/*_T1w.nii.gz')

    parser.add_argument('--t2-template', type=str,
                        help='glob bids-data-dir/t2-template to find input data')

    parser.add_argument('--task', type=str, required=True, help='number of Luigi workers',
                        choices=['StructMask', 'Freesurfer',
                                 'CnnMask',
                                 'PnlEddy', 'FslEddy', 'TopupEddy',
                                 'FslEddyEpi', 'EddyEpi',
                                 'Ukf',
                                 'Fs2Dwi', 'Wmql', 'Wmqlqc'])

    parser.add_argument('--num-workers', type=int, default=1, help='number of Luigi workers')

    parser.add_argument('--derivatives-name', type= str, default='pnlpipe',
                        help='''relative name of bids derivatives directory, 
                            translates to bids-data-dir/derivatives/derivatives-name''')


    args = parser.parse_args()


    try:
        cfg=getenv('LUIGI_CONFIG_PATH')
        stat(cfg)
    except (TypeError,FileNotFoundError):
        print('\nERROR')
        print('Define a valid configuration file: export LUIGI_CONFIG_PATH=/path/to/your_params.cfg\n')
        exit(1)

    
    cases = read_cases(abspath(args.c)) if isfile(abspath(args.c)) else [args.c]
    sessions = read_cases(abspath(args.s)) if isfile(abspath(args.s)) else [args.s]
    
    args.bids_data_dir= abspath(args.bids_data_dir)
    derivatives_dir= pjoin('derivatives', args.derivatives_name)
    
    jobs = []
    for ses in sessions:
        for id in cases:

            if args.t2_template:

                if args.task=='StructMask':
                    jobs.append(StructMask(bids_data_dir=args.bids_data_dir,
                                           derivatives_dir=derivatives_dir,
                                           id=id,
                                           ses=ses,
                                           struct_template=args.t2_template))

                elif args.task=='Freesurfer':
                    jobs.append(Freesurfer(bids_data_dir=args.bids_data_dir,
                                           derivatives_dir=derivatives_dir, 
                                           id=id,
                                           ses=ses,
                                           t1_template=args.t1_template,
                                           t2_template=args.t2_template))

                # TODO keep EddyEpi only
                elif args.task=='PnlEddyEpi' or args.task=='FslEddyEpi' or args.task=='EddyEpi':
                    jobs.append(eval(args.task)(bids_data_dir=args.bids_data_dir,
                                                derivatives_dir=derivatives_dir,
                                                id=id,
                                                ses=ses,
                                                dwi_template=args.dwi_template,
                                                struct_template=args.t2_template))



                # the following three tasks do not have pa_ap_template because
                # when axt2 is available, pa_ap acquisition should be unavailable
                # in other words, PnlEpi and TopupEddy are mutually exclusive
                elif args.task=='Ukf':
                    jobs.append(Ukf(bids_data_dir=args.bids_data_dir,
                                    derivatives_dir=derivatives_dir,
                                    id=id,
                                    ses=ses,
                                    dwi_template=args.dwi_template,
                                    struct_template=args.t2_template))


                # clash b/w Freesurfer and PnlEpi
                # either Freesurfer have to be run separately before with t1+t2 or
                # as part of Fs2Dwi with just t1
                elif args.task=='Fs2Dwi':
                    jobs.append(Fs2Dwi(bids_data_dir=args.bids_data_dir,
                                       derivatives_dir=derivatives_dir,
                                       id=id,
                                       ses=ses,
                                       dwi_template=args.dwi_template,
                                       struct_template=args.t2_template))

                elif args.task=='Wmql':
                    jobs.append(Wmql(bids_data_dir=args.bids_data_dir,
                                       derivatives_dir=derivatives_dir,
                                       id=id,
                                       ses=ses,
                                       dwi_template=args.dwi_template,
                                       struct_template=args.t2_template))


                # clash b/w Freesurfer and PnlEpi
                # either Freesurfer have to be run separately before with t1+t2 or
                # as part of Fs2Dwi with just t1
                elif args.task=='Wmqlqc':
                    jobs.append(Wmqlqc(bids_data_dir=args.bids_data_dir,
                                       derivatives_dir=derivatives_dir,
                                       id=id,
                                       ses=ses,
                                       dwi_template=args.dwi_template,
                                       struct_template=args.t2_template))


            # just t1_template
            else:
                if args.task=='StructMask':
                    jobs.append(StructMask(bids_data_dir=args.bids_data_dir,
                                           derivatives_dir=derivatives_dir,
                                           id=id,
                                           ses=ses,
                                           struct_template=args.t1_template))

                elif args.task=='Freesurfer':
                    jobs.append(Freesurfer(bids_data_dir=args.bids_data_dir,
                                           derivatives_dir=derivatives_dir,
                                           id=id,
                                           ses=ses,
                                           t1_template=args.t1_template))

                elif args.task=='CnnMask':
                    jobs.append(CnnMask(bids_data_dir=args.bids_data_dir,
                                        derivatives_dir=derivatives_dir,
                                        id=id,
                                        ses=ses,
                                        dwi_template=args.dwi_template))

                # TODO keep EddyEpi only
                elif args.task=='PnlEddy' or args.task=='FslEddy' or args.task=='EddyEpi':
                    jobs.append(eval(args.task)(bids_data_dir=args.bids_data_dir,
                                                derivatives_dir=derivatives_dir,
                                                id=id,
                                                ses=ses,
                                                dwi_template=args.dwi_template))


                elif args.task=='TopupEddy':
                    jobs.append(TopupEddy(bids_data_dir=args.bids_data_dir,
                                          derivatives_dir=derivatives_dir,
                                          id=id,
                                          ses=ses,
                                          pa_ap_template=args.dwi_template))


                # the following three tasks have both dwi_template and pa_ap_template
                # because a user may want to run {PnlEddy,FslEddy} or TopupEddy
                elif args.task=='Ukf':
                    jobs.append(Ukf(bids_data_dir=args.bids_data_dir,
                                    derivatives_dir=derivatives_dir,
                                    id=id,
                                    ses=ses,
                                    dwi_template=args.dwi_template,
                                    pa_ap_template=args.dwi_template))


                elif args.task=='Fs2Dwi':
                    jobs.append(Fs2Dwi(bids_data_dir=args.bids_data_dir,
                                       derivatives_dir=derivatives_dir,
                                       id=id,
                                       ses=ses,
                                       dwi_template=args.dwi_template))


                elif args.task == 'Wmql':
                    jobs.append(Wmql(bids_data_dir=args.bids_data_dir,
                                       derivatives_dir=derivatives_dir,
                                       id=id,
                                       ses=ses,
                                       dwi_template=args.dwi_template))


                elif args.task=='Wmqlqc':
                    jobs.append(Wmqlqc(bids_data_dir=args.bids_data_dir,
                                       derivatives_dir=derivatives_dir,
                                       id=id,
                                       ses=ses,
                                       dwi_template=args.dwi_template))


    build(jobs, workers=args.num_workers)

