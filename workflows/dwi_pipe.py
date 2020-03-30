#!/usr/bin/env python

from luigi import Task, ExternalTask, Parameter, BoolParameter, IntParameter, FloatParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isfile, basename, dirname

from plumbum import local
from subprocess import Popen
from time import sleep
import re

from struct_pipe import StructMask

from scripts.util import N_PROC, B0_THRESHOLD, BET_THRESHOLD, QC_POLL, _mask_name

class SelectDwiFiles(ExternalTask):
    id = Parameter()
    bids_data_dir = Parameter()
    dwi_template = Parameter(default='')

    def output(self):
        dwi= glob(pjoin(abspath(self.bids_data_dir), self.dwi_template.replace('$', self.id)))[0]
        bval= dwi.split('.nii')[0]+'.bval'
        bvec= dwi.split('.nii')[0]+'.bvec'

        return dict(dwi=local.path(dwi), bval=local.path(bval), bvec=local.path(bvec))


@requires(SelectDwiFiles)
class DwiAlign(Task):
    
    derivatives_dir= Parameter()
    
    def run(self):
        self.output()['dwi'].dirname.mkdir()

        cmd = (' ').join(['align.py',
                          '-i', self.input()['dwi'],
                          '--bvals', self.input()['bval'],
                          '--bvecs', self.input()['bvec'],
                          '-o', self.output()['dwi'].rsplit('.nii.gz')[0]])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        
        subject_dir= dirname(self.input()['dwi'].replace('rawdata', self.derivatives_dir))
        prefix= self.input()['dwi'].basename
        
        dwi = local.path(pjoin(subject_dir, prefix.split('_dwi.nii')[0]+ '_desc-Xc_dwi.nii.gz'))
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)

        return dict(dwi=dwi, bval=bval, bvec=bvec)


class BseExtract(Task):
    dwi= Parameter(default='')
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
        bse_prefix= self.dwi.basename
        desc= re.search('_desc-(.+?)_dwi.nii.gz', bse_prefix).group(1)
        desc= 'dwi'+ desc
        
        bse= local.path(pjoin(self.dwi.dirname, bse_prefix.split('_desc-')[0])+ '_desc-'+ desc+ '_bse.nii.gz')
        
        return bse



@requires(BseExtract)
class BseBetMask(Task):
    bet_threshold = FloatParameter(default=float(BET_THRESHOLD))
    slicer_exec = Parameter(default='')
    mask_qc= BoolParameter(default=False)

    def run(self):
        
        auto_mask = self.output()['mask'].replace('Qc','')

        if not isfile(auto_mask):
            cmd = (' ').join(['bet_mask.py',
                              '-i', self.input(),
                              '-o', self.output()['mask'].rsplit('_mask.nii.gz')[0],
                              f'-f {self.bet_threshold}' if self.bet_threshold else ''])
            p = Popen(cmd, shell=True)
            p.wait()

            if p.returncode:
                return


        # mask the baseline image
        cmd = (' ').join(['ImageMath', '3', self.output()['bse'], 'm', self.output()['bse'], auto_mask])
        p = Popen(cmd, shell=True)
        p.wait()


        if self.slicer_exec or self.mask_qc:
            print('\n\n** Check quality of created mask {} . Once you are done, save the (edited) mask as {} **\n\n'
                  .format(auto_mask,self.output()['mask']))


        if self.slicer_exec:
            cmd = (' ').join([self.slicer_exec, '--python-code',
                              '\"slicer.util.loadVolume(\'{}\'); '
                              'slicer.util.loadLabelVolume(\'{}\')\"'
                             .format(self.input(), auto_mask)])

            p = Popen(cmd, shell=True)
            p.wait()


        elif self.mask_qc:
            while 1:
                sleep(QC_POLL)
                if isfile(self.output()['mask']):
                    break


    def output(self):
    
        bse_betmask_prefix= local.path(self.input().rsplit('_bse.nii.gz')[0]+ 'BseBet')
        mask= _mask_name(bse_betmask_prefix, self.slicer_exec, self.mask_qc)
        
        return dict(bse= self.input(), mask=mask)



@requires(DwiAlign)
@inherits(BseBetMask)
class PnlEddy(Task):
    
    debug = BoolParameter(default=False)
    eddy_nproc = IntParameter(default=int(N_PROC))

    def run(self):
    
        for name in ['dwi', 'bval', 'bvec']:
            if not self.output()[name].exists():
                cmd = (' ').join(['pnl_eddy.py',
                                  '-i', self.input()['dwi'],
                                  '--bvals', self.input()['bval'],
                                  '--bvecs', self.input()['bvec'],
                                  '-o', self.output()['dwi'].rsplit('.nii.gz')[0],
                                  '-d' if self.debug else '',
                                  f'-n {self.eddy_nproc}' if self.eddy_nproc else ''])
                p = Popen(cmd, shell=True)
                p.wait()
                
                break

        self.dwi= self.output()['dwi']
        yield self.clone(BseBetMask)


    def output(self):
    
        eddy_prefix= self.input()['dwi'].rsplit('_dwi.nii.gz')[0]+ 'Ed'
                
        dwi = local.path(eddy_prefix+ '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth= 2)
        bvec = dwi.with_suffix('.bvec', depth= 2)
        
        bse_prefix= dwi.basename
        desc= re.search('_desc-(.+?)_dwi.nii.gz', bse_prefix).group(1)
        desc= 'dwi'+ desc
        
        bse= local.path(pjoin(dwi.dirname, bse_prefix.split('_desc-')[0])+ '_desc-'+ desc+ '_bse.nii.gz')
        eddy_bse_betmask_prefix= local.path(bse.rsplit('_bse.nii.gz')[0]+ 'BseBet')
        mask = _mask_name(eddy_bse_betmask_prefix, self.slicer_exec, self.mask_qc)
        
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
    
        for name in ['dwi', 'bval', 'bvec']:
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
        
        mask = _mask_name(self.eddy_epi_bse_betmask_prefix, self.slicer_exec, self.mask_qc)

        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)



@inherits(PnlEddy,PnlEddyEpi)
class Ukf(Task):

    tract_prefix = Parameter()
    ukf_params = Parameter(default='')

    def requires(self):
        self.tract_prefix.dirname.mkdir()

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

