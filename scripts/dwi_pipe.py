#!/usr/bin/env python

from luigi import Task, build, ExternalTask, Parameter, BoolParameter, ListParameter, IntParameter, FloatParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isdir

from plumbum import local
from shutil import rmtree

from _define_outputs import define_outputs_wf, create_dirs
from struct_pipe_t1_t2 import StructMask

from util import N_PROC, B0_THRESHOLD, BET_THRESHOLD

from subprocess import Popen


class SelectDwiFiles(ExternalTask):
    id = Parameter()
    bids_data_dir = Parameter()
    dwi_template = Parameter()

    def output(self):
        dwi= glob(pjoin(abspath(self.bids_data_dir), self.dwi_template.replace('id', self.id)))[0]
        bval= dwi.split('.nii')[0]+'.bval'
        bvec= dwi.split('.nii')[0]+'.bvec'

        return dict(dwi=local.path(dwi), bval=local.path(bval), bvec=local.path(bvec))


@requires(SelectDwiFiles)
class DwiAlign(Task):
    dwi_align_prefix = Parameter()

    def run(self):
        cmd = (' ').join(['align.py',
                          '-i', self.input()['dwi'],
                          '--bvals', self.input()['bval'],
                          '--bvecs', self.input()['bvec'],
                          '-o', self.dwi_align_prefix])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        dwi = self.dwi_align_prefix.with_suffix('.nii.gz')
        bval = self.dwi_align_prefix.with_suffix('.bval')
        bvec = self.dwi_align_prefix.with_suffix('.bvec')

        return dict(dwi=dwi, bval=bval, bvec=bvec)


class BseExtract(Task):
    dwi= Parameter(default='')
    bse_prefix = Parameter(default='')
    b0_threshold= FloatParameter(default=float(B0_THRESHOLD))
    which_bse= Parameter(default='')

    def run(self):

        cmd = (' ').join(['bse.py',
                          '-i', self.dwi,
                          '--bvals', self.dwi.with_suffix('.bval', depth=2),
                          '-o', self.output(),
                          f'-t {self.b0_threshold}' if self.b0_threshold else '',
                          self.which_bse if self.which_bse else ''])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.bse_prefix.with_suffix('.nii.gz')



@requires(BseExtract)
class BseBetMask(Task):
    bse_betmask_prefix = Parameter(default='')
    bet_threshold = FloatParameter(default=float(BET_THRESHOLD))
    slicer_exec = Parameter(default='')

    def run(self):
        cmd = (' ').join(['bet_mask.py',
                          '-i', self.input(),
                          '-o', self.bse_betmask_prefix,
                          f'-f {self.bet_threshold}' if self.bet_threshold else ''])
        p = Popen(cmd, shell=True)
        p.wait()

        # mask the baseline image
        cmd = (' ').join(['ImageMath', '3', self.output()['bse'], 'm', self.output()['bse'], self.output()['mask']])
        p = Popen(cmd, shell=True)
        p.wait()

        if self.slicer_exec:
            cmd = (' ').join([self.slicer_exec, '--python-code',
                              '\"slicer.util.loadVolume(\'{}\'); '
                              'slicer.util.loadLabelVolume(\'{}\')\"'
                             .format(self.input(), self.output())])

            p = Popen(cmd, shell=True)
            p.wait()

    def output(self):
        return dict(bse=self.input(), mask=local.path(self.bse_betmask_prefix+ '_mask.nii.gz'))



@requires(DwiAlign)
@inherits(BseBetMask)
class PnlEddy(Task):
    eddy_prefix = Parameter(default='')
    eddy_bse_masked_prefix = Parameter(default='')
    eddy_bse_betmask_prefix = Parameter(default='')
    debug = BoolParameter(default=False)
    eddy_nproc = IntParameter(default=int(N_PROC))

    def requires(self):
        return self.clone(DwiAlign)

    def run(self):
    
        for name in self.output().keys():
            if not self.output()[name].exists():        
                cmd = (' ').join(['pnl_eddy.py',
                                  '-i', self.input()['dwi'],
                                  '--bvals', self.input()['bval'],
                                  '--bvecs', self.input()['bvec'],
                                  '-o', self.eddy_prefix,
                                  '-d' if self.debug else '',
                                  f'-n {self.eddy_nproc}' if self.eddy_nproc else ''])
                p = Popen(cmd, shell=True)
                p.wait()
                
            break

        self.dwi= self.output()['dwi']
        self.bse_prefix= self.eddy_bse_masked_prefix
        self.bse_betmask_prefix= self.eddy_bse_betmask_prefix
        yield self.clone(BseBetMask)


    def output(self):
        dwi = self.eddy_prefix.with_suffix('.nii.gz')
        bval = self.eddy_prefix.with_suffix('.bval')
        bvec = self.eddy_prefix.with_suffix('.bvec')
        bse = self.eddy_bse_masked_prefix.with_suffix('.nii.gz')
        mask= local.path(self.eddy_bse_betmask_prefix+'_mask.nii.gz')

        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)



@inherits(PnlEddy,BseBetMask,StructMask)
class PnlEddyEpi(Task):
    eddy_epi_prefix = Parameter(default='')
    eddy_epi_bse_masked_prefix = Parameter(default='')
    eddy_epi_bse_betmask_prefix = Parameter(default='')
    debug= BoolParameter(default=False)
    epi_nproc= IntParameter(default=N_PROC)


    def requires(self):
        return dict(eddy= self.clone(PnlEddy), t2= self.clone(StructMask))

    def run(self):
    
        for name in self.output().keys():
            if not self.output()[name].exists():        
                cmd = (' ').join(['pnl_epi.py',
                                  '--dwi', self.input()['eddy']['dwi'],
                                  '--bvals', self.input()['eddy']['bval'],
                                  '--bvecs', self.input()['eddy']['bvec'],
                                  '--dwimask', self.input()['eddy']['mask'],
                                  '--bse', self.input()['eddy']['bse'],
                                  '--t2', self.input()['t2']['aligned'],
                                  '--t2mask', self.input()['t2']['mask'],
                                  '-o', self.eddy_epi_prefix,
                                  '-d' if self.debug else '',
                                  f'-n {self.epi_nproc}' if self.epi_nproc else ''])
                p = Popen(cmd, shell=True)
                p.wait()
            
            break

        self.dwi= self.output()['dwi']
        self.bse_prefix= self.eddy_epi_bse_masked_prefix
        self.bse_betmask_prefix= self.eddy_epi_bse_betmask_prefix
        yield self.clone(BseBetMask)

    def output(self):
        dwi = self.eddy_epi_prefix.with_suffix('.nii.gz')
        bval = self.eddy_epi_prefix.with_suffix('.bval')
        bvec = self.eddy_epi_prefix.with_suffix('.bvec')
        bse = self.eddy_epi_bse_masked_prefix.with_suffix('.nii.gz')
        mask= local.path(self.eddy_epi_bse_betmask_prefix+'_mask.nii.gz')

        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)



@inherits(PnlEddy,PnlEddyEpi)
class Ukf(Task):

    tract_prefix = Parameter(default='')
    ukf_params = Parameter()

    def requires(self):
        if self.struct_template:
            return self.clone(PnlEddyEpi)
        else:
            return self.clone(PnlEddy)

        #TODO can be extended to include FslEddy task

    def run(self):            
        cmd = (' ').join(['ukf.py',
                          '-i', self.input()['dwi'],
                          '--bvals', self.input()['dwi'].with_suffix('.bval', depth=2),
                          '--bvecs', self.input()['dwi'].with_suffix('.bvec', depth=2),
                          '-m', self.input()['mask'],
                          '-o', self.output(),
                          '--params', self.ukf_params])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.tract_prefix.with_suffix('.vtk')



if __name__ == '__main__':

    bids_data_dir = '/home/tb571/Downloads/INTRuST_BIDS/'
    bids_derivatives = pjoin(abspath(bids_data_dir), 'derivatives', 'luigi-pnlpipe')

    # cases= ['003GNX007']
    cases= ['003GNX012', '003GNX021']
    # cases = ['003GNX007', '003GNX012', '003GNX021']

    overwrite = False
    if overwrite:
        try:
            for id in cases:
                p= Popen(f'rm -rf {bids_derivatives}/sub-{id}/dwi', shell= True)
                p.wait()
        except:
            pass


    create_dirs(cases, bids_derivatives)

    dwi_template = 'sub-id/dwi/*_dwi.nii.gz'
    t2_template = 'sub-id/anat/*_T2w.nii.gz'

    # bse.py
    which_bse= '' # '', '--min', '--avg', or '--all'
    b0_threshold= float(B0_THRESHOLD)

    # bet_mask.py
    bet_threshold= float(BET_THRESHOLD)

    # for qc'ing the created mask
    slicer_exec = ''  # '/home/tb571/Downloads/Slicer-4.10.2-linux-amd64/Slicer'

    debug= False

    # pnl_eddy.py
    eddy_nproc= int(N_PROC)

    # pnl_epi.py
    epi_nproc= int(N_PROC)

    # fsl_eddy.py
    acqp_file= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/acqp.txt'
    index_file= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/index.txt'
    eddy_config= '/home/tb571/luigi-pnlpipe/scripts/eddy_config.txt'

    # ukf.py
    ukf_params= '--seedingThreshold,0.4,--seedsPerVoxel,1'

    # fs2dwi.py
    mode= 'direct' # 'direct', or 'witht2'

    # atlas.py
    mabs_mask_nproc= int(N_PROC)
    fusion= '' # 'avg', 'wavg', or 'antsJointFusion'
    t2_csvFile= ''#'/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT2Masks-12a14d9/trainingDataT2Masks-hdr.csv'

    # makeRigidMask.py
    t2_model_img= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T2w.nii.gz'
    t2_model_mask= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T2wXcMabs_mask.nii.gz'

    inter= define_outputs_wf(cases[0], bids_derivatives)


    # individual task
    build([PnlEddy(bids_data_dir = bids_data_dir,
                   id=cases[0],
                   dwi_template = dwi_template,
                   dwi_align_prefix=inter['dwi_align_prefix'],
                   eddy_prefix=inter['eddy_prefix'],
                   eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                   eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                   which_bse= which_bse,
                   b0_threshold= b0_threshold,
                   bet_threshold= bet_threshold,
                   slicer_exec= slicer_exec,
                   debug= debug,
                   eddy_nproc= eddy_nproc)])


    # individual task
    build([PnlEddyEpi(bids_data_dir = bids_data_dir,
                      id=cases[0],
                      dwi_template = dwi_template,
                      dwi_align_prefix=inter['dwi_align_prefix'],
                      eddy_prefix=inter['eddy_prefix'],
                      eddy_epi_prefix=inter['eddy_epi_prefix'],
                      eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
                      eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                      eddy_epi_bse_masked_prefix=inter['eddy_epi_bse_masked_prefix'],
                      eddy_epi_bse_betmask_prefix=inter['eddy_epi_bse_betmask_prefix'],
                      which_bse= which_bse,
                      b0_threshold= b0_threshold,
                      bet_threshold= bet_threshold,
                      slicer_exec= slicer_exec,
                      debug= debug,
                      eddy_nproc= eddy_nproc,
                      epi_nproc= epi_nproc,
                      struct_template= t2_template,
                      struct_align_prefix=inter['t2_align_prefix'],
                      mabs_mask_prefix=inter['t2_mabsmask_prefix'],
                      csvFile=t2_csvFile,
                      fusion=fusion,
                      mabs_mask_nproc=mabs_mask_nproc,
                      model_img=t2_model_img,
                      model_mask=t2_model_mask)])
    

    
    # individual task, based on PnlEddy
    build([Ukf(bids_data_dir = bids_data_dir,
               id = cases[0],
               dwi_template = dwi_template,
               dwi_align_prefix=inter['dwi_align_prefix'],
               eddy_prefix=inter['eddy_prefix'],
               eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
               eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
               which_bse= which_bse,
               b0_threshold= b0_threshold,
               bet_threshold= bet_threshold,
               slicer_exec= slicer_exec,
               debug= debug,
               eddy_nproc= eddy_nproc,
               ukf_params = ukf_params,
               tract_prefix= inter['eddy_tract_prefix'])])
    

    # individual task, based on PnlEddyEpi
    build([Ukf(bids_data_dir = bids_data_dir,
               id=cases[0],
               dwi_template = dwi_template,
               dwi_align_prefix=inter['dwi_align_prefix'],
               eddy_prefix=inter['eddy_prefix'],
               eddy_epi_prefix=inter['eddy_epi_prefix'],
               eddy_bse_masked_prefix=inter['eddy_bse_masked_prefix'],
               eddy_bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
               eddy_epi_bse_masked_prefix=inter['eddy_epi_bse_masked_prefix'],
               eddy_epi_bse_betmask_prefix=inter['eddy_epi_bse_betmask_prefix'],
               which_bse= which_bse,
               b0_threshold= b0_threshold,
               bet_threshold= bet_threshold,
               slicer_exec= slicer_exec,
               debug= debug,
               eddy_nproc= eddy_nproc,
               epi_nproc= epi_nproc,
               struct_template= t2_template,
               struct_align_prefix=inter['t2_align_prefix'],
               mabs_mask_prefix=inter['t2_mabsmask_prefix'],
               csvFile=t2_csvFile,
               fusion=fusion,
               mabs_mask_nproc=mabs_mask_nproc,
               t1_model_img=t2_model_img,
               t1_model_mask=t2_model_mask,
               ukf_params=ukf_params,
               tract_prefix= inter['eddy_epi_tract_prefix'])])

