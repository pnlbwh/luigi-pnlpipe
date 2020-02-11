#!/usr/bin/env python

from luigi import Task, build, ExternalTask, Parameter, BoolParameter, ListParameter, IntParameter, FloatParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isdir

from plumbum import local
from shutil import rmtree

from struct_pipe_t1_t2 import StructMask

from util import N_PROC, B0_THRESHOLD, BET_THRESHOLD

from subprocess import Popen


class SelectDwiFiles(ExternalTask):
    id = Parameter()
    bids_data_dir = Parameter()
    dwi_template = Parameter(default= 'sub-id/dwi/*_dwi.nii.gz')

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
    eddy_prefix = Parameter()
    eddy_bse_masked_prefix = Parameter()
    eddy_bse_betmask_prefix = Parameter()
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

    tract_prefix = Parameter()
    ukf_params = Parameter(default='')

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

