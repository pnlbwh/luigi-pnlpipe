#!/usr/bin/env python

from luigi import Task, build, Parameter, BoolParameter, IntParameter
from luigi.util import inherits, requires

from os.path import join as pjoin, abspath, isdir

from dwi_pipe import PnlEddy, PnlEddyEpi, Ukf
from struct_pipe_t1_t2 import Freesurfer, StructMask

from subprocess import Popen
from plumbum import local

from _define_outputs import create_dirs

from util import N_PROC, B0_THRESHOLD, BET_THRESHOLD, FILEDIR

from _define_outputs import define_outputs_wf


@inherits(Freesurfer,PnlEddy,PnlEddyEpi,StructMask)
class Fs2Dwi(Task):

    fs_in_dwi= Parameter()
    debug= BoolParameter(default=False)
    mode= Parameter(default='direct')
    
    def requires(self):
        if self.mode=='direct':
            return dict(fs_dir= self.clone(Freesurfer), corrected= self.clone(PnlEddy))
            
        elif self.mode=='witht2':
            fs_dir= self.clone(Freesurfer)

            self.struct_template = self.t2_template
            self.struct_align_prefix = self.t2_align_prefix
            self.mabs_mask_prefix = self.t2_mask_prefix
            self.csvFile = self.t2_csvFile
            self.model_img = self.t2_model_img
            self.model_mask = self.t2_model_mask

            corrected= self.clone(PnlEddyEpi)
            t2_attr= self.clone(StructMask)

            return dict(fs_dir= fs_dir, corrected= corrected, t2_attr= t2_attr)
   
            
    def run(self):
        cmd = (' ').join(['fs2dwi.py',
                          '-f', self.input()['fs_dir'],
                          '--bse', self.input()['corrected']['bse'],
                          '--dwimask', self.input()['corrected']['mask'],
                          '-o', self.fs_in_dwi.dirname,
                          '-d' if self.debug else '',
                          self.mode,
                          '--t2 {} --t2mask {}'.format(self.input()['t2_attr']['aligned'],self.input()['t2_attr']['mask'])
                                                if self.mode=='witht2' else ''])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.fs_in_dwi



@inherits(Fs2Dwi,Ukf)
class Wmql(Task):

    wmql_out= Parameter()
    query= Parameter(default='')
    wmql_nproc= IntParameter(default= int(N_PROC))

    def requires(self):

        fs_in_dwi= self.clone(Fs2Dwi)

        if self.t2_template:
            self.struct_template = self.t2_template
            self.struct_align_prefix = self.t2_align_prefix
            self.mabs_mask_prefix = self.t2_mask_prefix
            self.csvFile = self.t2_csvFile
            self.model_img = self.t2_model_img
            self.model_mask = self.t2_model_mask

        tract= self.clone(Ukf)

        return (fs_in_dwi,tract)

    def run(self):
        cmd = (' ').join(['wmql.py',
                          '-f', self.input()[0],
                          '-i', self.input()[1],
                          '-o', self.wmql_out,
                          f'-q {self.query}' if self.query else '',
                          f'-n {self.wmql_nproc}' if self.wmql_nproc else ''])
        p = Popen(cmd, shell=True)
        p.wait()


    def output(self):
        return self.wmql_out


@requires(Wmql)
class Wmqlqc(Task):
    id= Parameter()
    wmqlqc_out= Parameter()

    def run(self):
        cmd = (' ').join(['wmqlqc.py',
                          '-i', self.input(),
                          '-s', self.id,
                          '-o', self.wmqlqc_out])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.wmqlqc_out





if __name__=='__main__':

    bids_data_dir = '/home/tb571/Downloads/INTRuST_BIDS/'
    bids_derivatives = pjoin(abspath(bids_data_dir), 'derivatives', 'luigi-pnlpipe')

    # cases= ['003GNX007']
    cases = ['003GNX012']
    # cases= ['003GNX012', '003GNX021']
    # cases = ['003GNX007', '003GNX012', '003GNX021']

    overwrite = False
    if overwrite:
        try:
            for id in cases:
                p= Popen(f'rm -rf {bids_derivatives}/sub-{id}/fs2dwi {bids_derivatives}/sub-{id}/tracts', shell= True)
                p.wait()
        except:
            pass


    create_dirs(cases, bids_derivatives)

    t1_template = 'sub-id/anat/*_T1w.nii.gz'
    t2_template = 'sub-id/anat/*_T2w.nii.gz'
    dwi_template = 'sub-id/dwi/*_dwi.nii.gz'

    # atlas.py
    mabs_mask_nproc= int(N_PROC)
    fusion= '' # 'avg', 'wavg', or 'antsJointFusion'
    debug = False
    t1_csvFile = ''  # '/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT1AHCC-8141805/trainingDataT1Masks-hdr.csv'
    t2_csvFile = ''  # '/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT2Masks-12a14d9/trainingDataT2Masks-hdr.csv'

    # makeRigidMask.py
    t1_model_img = '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T1w.nii.gz'
    t1_model_mask = '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T1wXcMabs_mask.nii.gz'
    t2_model_img = '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T2w.nii.gz'
    t2_model_mask = '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T2wXcMabs_mask.nii.gz'

    # fs.py
    freesurfer_nproc= 1
    expert_file= ''
    no_hires= False
    no_skullstrip= True

    slicer_exec= ''#'/home/tb571/Downloads/Slicer-4.10.2-linux-amd64/Slicer'

    # bse.py
    which_bse = ''  # '', '--min', '--avg', or '--all'
    b0_threshold = float(B0_THRESHOLD)

    # bet_mask.py
    bet_threshold = float(BET_THRESHOLD)

    # pnl_eddy.py
    eddy_nproc = int(N_PROC)

    # pnl_epi.py
    epi_nproc = int(N_PROC)

    # fsl_eddy.py
    acqp_file = '/home/tb571/Downloads/INTRuST_BIDS/derivatives/acqp.txt'
    index_file = '/home/tb571/Downloads/INTRuST_BIDS/derivatives/index.txt'
    eddy_config = '/home/tb571/luigi-pnlpipe/scripts/eddy_config.txt'

    # ukf.py
    ukf_params = '--seedingThreshold,0.4,--seedsPerVoxel,1'

    # fs2dwi.py
    mode='witht2'

    # wmql.py
    wmql_nproc= int(N_PROC)
    query= pjoin(FILEDIR, 'wmql-2.0.qry')



    # Freesurfer and Fs2Dwi with only T1
    tasks= []
    for id in cases:

        inter= define_outputs_wf(id, bids_derivatives)

        tasks.append(Fs2Dwi(id=id,
                            bids_data_dir=bids_data_dir,
                            dwi_template=dwi_template,
                            dwi_align_prefix=inter['dwi_align_prefix'],
                            eddy_prefix=inter['eddy_prefix'],
                            eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                            eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                            which_bse=which_bse,
                            b0_threshold=b0_threshold,
                            bet_threshold=bet_threshold,
                            slicer_exec=slicer_exec,
                            debug=debug,
                            t1_template=t1_template,
                            t1_align_prefix=inter['t1_align_prefix'],
                            t1_mask_prefix=inter['t1_mabsmask_prefix'],
                            t1_csvFile=t1_csvFile,
                            fusion=fusion,
                            mabs_mask_nproc=mabs_mask_nproc,
                            t1_model_img= t1_model_img,
                            t1_model_mask=t1_model_mask,
                            freesurfer_nproc=freesurfer_nproc,
                            expert_file=expert_file,
                            no_hires=no_hires,
                            no_skullstrip=no_skullstrip,
                            fs_dir= inter['fs_dir'],
                            fs_in_dwi= inter['fs_in_eddy'],
                            mode= mode))

    build(tasks)
    
    
    # Freesurfer and Fs2Dwi with both T1 and T2
    tasks= []
    for id in cases:

        inter= define_outputs_wf(id, bids_derivatives)
        
        tasks.append(Fs2Dwi(id=id,
                            bids_data_dir=bids_data_dir,
                            bids_derivatives=bids_derivatives,
                            dwi_template=dwi_template,
                            dwi_align_prefix=inter['dwi_align_prefix'],
                            eddy_prefix=inter['eddy_prefix'],
                            eddy_epi_prefix=inter['eddy_epi_prefix'],
                            eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                            eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                            eddy_epi_bse_masked_prefix=inter['eddy_epi_bse_masked_prefix'],
                            eddy_epi_bse_betmask_prefix=inter['eddy_epi_bse_betmask_prefix'],
                            which_bse=which_bse,
                            b0_threshold=b0_threshold,
                            bet_threshold=bet_threshold,
                            slicer_exec=slicer_exec,
                            debug=debug,
                            struct_template=t1_template,
                            struct_align_prefix=inter['t1_align_prefix'],
                            mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                            t1_csvFile=t1_csvFile,
                            t2_csvFile=t2_csvFile,
                            fusion=fusion,
                            mabs_mask_nproc=mabs_mask_nproc,
                            t1_model_img= t1_model_img,
                            t1_model_mask=t1_model_mask,
                            t2_model_img= t2_model_img,
                            t2_model_mask=t2_model_mask,
                            freesurfer_nproc=freesurfer_nproc,
                            expert_file=expert_file,
                            no_hires=no_hires,
                            no_skullstrip=no_skullstrip,
                            fs_dir= inter['fs_dir'],
                            fs_in_dwi= inter['fs_in_epi'],
                            mode= mode))
        
    build(tasks)

    
    # Wmqlqc with PnlEddyEpi
    tasks = []
    for id in cases:
        inter = define_outputs_wf(id, bids_derivatives)

        tasks.append(Wmqlqc(id=id,
                            bids_data_dir=bids_data_dir,
                            dwi_template=dwi_template,
                            dwi_align_prefix=inter['dwi_align_prefix'],
                            eddy_prefix=inter['eddy_prefix'],
                            eddy_epi_prefix=inter['eddy_epi_prefix'],
                            eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                            eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                            eddy_epi_bse_masked_prefix=inter['eddy_epi_bse_masked_prefix'],
                            eddy_epi_bse_betmask_prefix=inter['eddy_epi_bse_betmask_prefix'],
                            eddy_nproc=eddy_nproc,
                            epi_nproc=epi_nproc,
                            which_bse=which_bse,
                            b0_threshold=b0_threshold,
                            bet_threshold=bet_threshold,
                            slicer_exec=slicer_exec,
                            debug=debug,
                            t1_template=t1_template,
                            t1_align_prefix=inter['t1_align_prefix'],
                            t1_mask_prefix=inter['t1_mabsmask_prefix'],
                            t2_template=t2_template,
                            t2_align_prefix=inter['t2_align_prefix'],
                            t2_mask_prefix=inter['t2_mabsmask_prefix'],
                            t1_csvFile=t1_csvFile,
                            t2_csvFile=t2_csvFile,
                            fusion=fusion,
                            mabs_mask_nproc=mabs_mask_nproc,
                            t1_model_img=t1_model_img,
                            t1_model_mask=t1_model_mask,
                            t2_model_img=t2_model_img,
                            t2_model_mask=t2_model_mask,
                            freesurfer_nproc=freesurfer_nproc,
                            expert_file=expert_file,
                            no_hires=no_hires,
                            no_skullstrip=no_skullstrip,
                            fs_dir=inter['fs_dir'],
                            mode=mode,
                            fs_in_dwi=inter['fs_in_epi'],
                            ukf_params=ukf_params,
                            tract_prefix=inter['eddy_epi_tract_prefix'],
                            wmql_out=inter['epi_wmql_dir'],
                            query= query,
                            wmql_nproc= wmql_nproc,
                            wmqlqc_out= inter['epi_wmqlqc_dir']))

    build(tasks)
    


    # Wmqlqc with PnlEddy
    tasks = []
    for id in cases:
        inter = define_outputs_wf(id, bids_derivatives)

        tasks.append(Wmqlqc(id=id,
                            bids_data_dir=bids_data_dir,
                            dwi_template=dwi_template,
                            dwi_align_prefix=inter['dwi_align_prefix'],
                            eddy_prefix=inter['eddy_prefix'],
                            eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                            eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                            eddy_nproc=eddy_nproc,
                            which_bse=which_bse,
                            b0_threshold=b0_threshold,
                            bet_threshold=bet_threshold,
                            slicer_exec=slicer_exec,
                            debug=debug,
                            t1_template=t1_template,
                            t1_align_prefix=inter['t1_align_prefix'],
                            t1_mask_prefix=inter['t1_mabsmask_prefix'],
                            t1_csvFile=t1_csvFile,
                            fusion=fusion,
                            mabs_mask_nproc=mabs_mask_nproc,
                            t1_model_img=t1_model_img,
                            t1_model_mask=t1_model_mask,
                            freesurfer_nproc=freesurfer_nproc,
                            expert_file=expert_file,
                            no_hires=no_hires,
                            no_skullstrip=no_skullstrip,
                            fs_dir=inter['fs_dir'],
                            fs_in_dwi=inter['fs_in_eddy'],
                            mode=mode,
                            ukf_params=ukf_params,
                            tract_prefix=inter['eddy_tract_prefix'],
                            wmql_out=inter['eddy_wmql_dir'],
                            query= query,
                            wmql_nproc= wmql_nproc,
                            wmqlqc_out= inter['eddy_wmqlqc_dir']))

    build(tasks)


