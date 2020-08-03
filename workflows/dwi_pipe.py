#!/usr/bin/env python

from luigi import Task, ExternalTask, Parameter, BoolParameter, IntParameter, FloatParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isfile, basename, dirname
from os import symlink
from shutil import move

from plumbum import local
from subprocess import Popen, check_call
from time import sleep
import re

from struct_pipe import StructMask

from scripts.util import N_PROC, B0_THRESHOLD, BET_THRESHOLD, QC_POLL, _mask_name, LIBDIR, TemporaryDirectory

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
    
        suffix= '_dwi.nii.gz'        
        dwi = local.path(self.input()['dwi'].replace('rawdata', self.derivatives_dir).rsplit(suffix)[0]+ '_desc-Xc'+ suffix)
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)

        return dict(dwi=dwi, bval=bval, bvec=bvec)



@requires(DwiAlign)
class CnnMask(Task):
    slicer_exec = Parameter(default='')
    dwi_mask_qc= BoolParameter(default=False)
    model_folder= Parameter(default='')
    percentile= IntParameter(default=99)

    def run(self):
        
        auto_mask = self.output()['mask'].replace('Qc_mask.nii.gz','_mask.nii.gz')

        if not isfile(auto_mask):
            
            with TemporaryDirectory() as tmpdir, local.cwd(tmpdir):
                symlink(self.input()['dwi'],self.input()['dwi'].basename)
                symlink(self.input()['bval'],self.input()['bval'].basename)
                symlink(self.input()['bvec'],self.input()['bvec'].basename)
                
                
                dwi_list= 'dwi_list.txt'
                with open(dwi_list,'w') as f:
                    f.write(pjoin(tmpdir,self.input()['dwi'].basename))
               

                cmd = (' ').join(['dwi_masking.py',
                                  '-i', dwi_list,
                                  '-f', self.model_folder,
                                  f'-p {self.percentile}'])
                p = Popen(cmd, shell=True)
                p.wait()
                
                prefix= basename(self.input()['dwi'].stem)+'_bse'
                move(prefix+'.nii.gz', self.output()['bse'])
                move(prefix+'-multi_BrainMask.nii.gz', auto_mask)



        # mask the baseline image
        cmd = (' ').join(['ImageMath', '3', self.output()['bse'], 'm', self.output()['bse'], auto_mask])
        p = Popen(cmd, shell=True)
        p.wait()


        if self.slicer_exec or self.dwi_mask_qc:
            print('\n\n** Check quality of created mask {} . Once you are done, save the (edited) mask as {} **\n\n'
                  .format(auto_mask,self.output()['mask']))


        if self.slicer_exec:
            cmd = (' ').join([self.slicer_exec, '--python-code',
                              '\"slicer.util.loadVolume(\'{}\'); '
                              'slicer.util.loadLabelVolume(\'{}\')\"'
                             .format(self.input(), auto_mask)])

            p = Popen(cmd, shell=True)
            p.wait()


        elif self.dwi_mask_qc:
            while 1:
                sleep(QC_POLL)
                if isfile(self.output()['mask']):
                    break


    def output(self):

        prefix= self.input()['dwi']._path
        desc= re.search('_desc-(.+?)_dwi.nii.gz', prefix).group(1)
        desc= 'dwi'+ desc
        outPrefix= prefix.split('_desc-')[0]+ '_desc-'+ desc
        
        bse= local.path(outPrefix+ '_bse.nii.gz')
        mask= _mask_name(local.path(outPrefix+ 'CNN'), self.slicer_exec, self.dwi_mask_qc)
        
        return dict(bse= bse, mask=mask)



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
        
        prefix= self.dwi._path
        desc= re.search('_desc-(.+?)_dwi.nii.gz', prefix).group(1)
        desc= 'dwi'+ desc        
        bse= local.path(prefix.split('_desc-')[0]+ '_desc-'+ desc+ '_bse.nii.gz')
        
        return bse



@requires(BseExtract)
class BseMask(Task):
    bet_threshold = FloatParameter(default=float(BET_THRESHOLD))
    mask_method = Parameter(default='Bet')
    slicer_exec = Parameter(default='')
    dwi_mask_qc= BoolParameter(default=False)
    model_folder= Parameter(default='')

    def run(self):
        
        auto_mask = self.output()['mask'].replace('Qc','')

        if not isfile(auto_mask):
            if self.mask_method=='Bet':
                cmd = (' ').join(['bet_mask.py',
                                  '-i', self.input(),
                                  '-o', auto_mask.rsplit('_mask.nii.gz')[0],
                                  f'-f {self.bet_threshold}' if self.bet_threshold else ''])
                p = Popen(cmd, shell=True)
                p.wait()
                
                if p.returncode:
                    return
            
            
            elif self.mask_method=='CNN':
                
                pass
                # see CnnMask task above
                # also see https://github.com/pnlbwh/luigi-pnlpipe/issues/5


        # mask the baseline image
        cmd = (' ').join(['ImageMath', '3', self.output()['bse'], 'm', self.output()['bse'], auto_mask])
        p = Popen(cmd, shell=True)
        p.wait()


        if self.slicer_exec or self.dwi_mask_qc:
            print('\n\n** Check quality of created mask {} . Once you are done, save the (edited) mask as {} **\n\n'
                  .format(auto_mask,self.output()['mask']))


        if self.slicer_exec:
            cmd = (' ').join([self.slicer_exec, '--python-code',
                              '\"slicer.util.loadVolume(\'{}\'); '
                              'slicer.util.loadLabelVolume(\'{}\')\"'
                             .format(self.input(), auto_mask)])

            p = Popen(cmd, shell=True)
            p.wait()


        elif self.dwi_mask_qc:
            while 1:
                sleep(QC_POLL)
                if isfile(self.output()['mask']):
                    break


    def output(self):
    
        prefix= local.path(self.input().rsplit('_bse.nii.gz')[0]+ self.mask_method)
        mask= _mask_name(prefix, self.slicer_exec, self.dwi_mask_qc)
        
        return dict(bse= self.input(), mask=mask)



@requires(DwiAlign)
@inherits(BseMask)
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
        yield self.clone(BseMask)


    def output(self):
    
        eddy_prefix= self.input()['dwi'].rsplit('_dwi.nii.gz')[0]+ 'Ed'                
        dwi = local.path(eddy_prefix+ '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth= 2)
        bvec = dwi.with_suffix('.bvec', depth= 2)
        
        bse_prefix= dwi._path
        desc= re.search('_desc-(.+?)_dwi.nii.gz', bse_prefix).group(1)
        desc= 'dwi'+ desc        
        bse= local.path(bse_prefix.split('_desc-')[0]+ '_desc-'+ desc+ '_bse.nii.gz')
        
        eddy_bse_mask_prefix= local.path(bse.rsplit('_bse.nii.gz')[0]+ self.mask_method)
        mask = _mask_name(eddy_bse_mask_prefix, self.slicer_exec, self.dwi_mask_qc)
        
        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)


@requires(DwiAlign,CnnMask)
class CnnMaskPnlEddy(Task):
    debug = BoolParameter(default=False)
    eddy_nproc = IntParameter(default=int(N_PROC))

    def run(self):

        for name in ['dwi', 'bval', 'bvec']:
            if not self.output()[name].exists():
                cmd = (' ').join(['pnl_eddy.py',
                                  '-i', self.input()[0]['dwi'],
                                  '--bvals', self.input()[0]['bval'],
                                  '--bvecs', self.input()[0]['bvec'],
                                  '-o', self.output()[0]['dwi'].rsplit('.nii.gz')[0],
                                  '-d' if self.debug else '',
                                  f'-n {self.eddy_nproc}' if self.eddy_nproc else ''])
                p = Popen(cmd, shell=True)
                p.wait()

                break


    def output(self):

        eddy_prefix = self.input()[0]['dwi'].rsplit('_dwi.nii.gz')[0] + 'Ed'
        dwi = local.path(eddy_prefix + '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)

        bse_prefix = dwi._path
        desc = re.search('_desc-(.+?)_dwi.nii.gz', bse_prefix).group(1)
        desc = 'dwi' + desc
        bse = local.path(bse_prefix.split('_desc-')[0] + '_desc-' + desc + '_bse.nii.gz')

        eddy_bse_mask_prefix = local.path(bse.rsplit('_bse.nii.gz')[0] + self.mask_method)
        mask = _mask_name(eddy_bse_mask_prefix, self.slicer_exec, self.dwi_mask_qc)

        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)


@requires(DwiAlign,CnnMask)
class FslEddy(Task):
    
    acqp = Parameter()
    index = Parameter()
    config = Parameter(default=pjoin(LIBDIR, 'scripts', 'eddy_config.txt'))
    useGpu = BoolParameter(default=False)
     
    def run(self):
        outDir= self.output()['dwi'].dirname.join('fsl_eddy')
        outDir.mkdir()
        outPrefix= outDir.join(self.output()['dwi'].stem)

        for name in ['dwi', 'bval', 'bvec']:
            if not self.output()[name].exists():
                cmd = (' ').join(['fsl_eddy.py',
                                  '--dwi', self.input()[0]['dwi'],
                                  '--bvals', self.input()[0]['bval'],
                                  '--bvecs', self.input()[0]['bvec'],
                                  '--mask', self.input()[1]['mask'],
                                  '--acqp', self.acqp,
                                  '--index', self.index,
                                  '--config', self.config,
                                  '--eddy-cuda' if self.useGpu else '',
                                  '-o', outPrefix])
                p = Popen(cmd, shell=True)
                p.wait()
                
                version_file= self.output()['dwi'].dirname.join('fsl_version.txt')
                check_call(f'eddy_openmp 2>&1 | grep Part > {version_file}', shell= True)
                
                move(outPrefix+'.nii.gz',self.output()['dwi'].dirname)
                move(outPrefix+'.bval',self.output()['dwi'].dirname)
                move(outPrefix+'.bvec',self.output()['dwi'].dirname)

                break

        # self.dwi= self.output()['dwi']
        # yield self.clone(BseExtract)


    def output(self):
    
        eddy_prefix= self.input()[0]['dwi'].rsplit('_dwi.nii.gz')[0]+ 'Ed'
        dwi = local.path(eddy_prefix+ '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth= 2)
        bvec = dwi.with_suffix('.bvec', depth= 2)
        
        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=self.input()[1]['bse'], mask=self.input()[1]['mask'])



@inherits(FslEddy,StructMask,BseExtract)
class FslEddyEpi(Task):
    
    debug= BoolParameter(default=False)
    epi_nproc= IntParameter(default=N_PROC)

    def requires(self):
        return dict(eddy= self.clone(FslEddy), t2= self.clone(StructMask))

    def run(self):
        
        eddy_epi_prefix= self.output()['dwi'].rsplit('.nii.gz')[0]

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
                                  '-o', eddy_epi_prefix,
                                  '-d' if self.debug else '',
                                  f'-n {self.epi_nproc}' if self.epi_nproc else ''])
                p = Popen(cmd, shell=True)
                p.wait()
                
                move(eddy_epi_prefix+'_mask.nii.gz', self.output()['mask'])

                break
                
        self.dwi= self.output()['dwi']
        yield self.clone(BseExtract)

    def output(self):

        eddy_epi_prefix= self.input()['eddy']['dwi'].rsplit('_dwi.nii.gz')[0]+ 'Ep'
        dwi = local.path(eddy_epi_prefix+ '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth= 2)
        bvec = dwi.with_suffix('.bvec', depth= 2)
        
        # adding EdEp suffix to be consistent with dwi
        mask_prefix= local.path(self.input()['eddy']['mask'].rsplit('_mask.nii.gz')[0]+ 'EdEp')
        
        # ENH
        # two things could be done:
        # * introduce `epi_mask_qc` param, separate from `dwi_mask_qc` param
        # * do not qc at all: the mask is generated at the beginning of the pipeline, hence no qc after warping
        # following the latter, the third argument is set to False
        mask = _mask_name(mask_prefix, self.slicer_exec, False)

        
        # adding EdEp suffix to be consistent with dwi
        bse_prefix= self.input()['eddy']['bse'].rsplit('_bse.nii.gz')[0]+ 'EdEp'
        bse = local.path(bse_prefix+ '_bse.nii.gz')
        
        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)
        

# ENH required, follow FslEddyEpi like eddy_epi_prefix determination in output()
@inherits(PnlEddy,BseMask,StructMask)
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
        
        mask = _mask_name(self.eddy_epi_bse_betmask_prefix, self.slicer_exec, self.dwi_mask_qc)

        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)



# ENH required, should support PnlEddy, PnlEddyEpi, FslEddy FslEddyEpi
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


@requires(CnnMaskPnlEddy)
class PnlEddyUkf(Task):

    ukf_params = Parameter(default='')

    def run(self):
        cmd = (' ').join(['ukf.py',
                          '-i', self.input()['dwi'],
                          '--bvals', self.input()['bval'],
                          '--bvecs', self.input()['bvec'],
                          '-m', self.input()['mask'],
                          '-o', self.output(),
                          '--params', self.ukf_params])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.input()['dwi'].rsplit('.nii.gz')[0] + '.vtk'

