#!/usr/bin/env python

from luigi import Task, ExternalTask, Parameter, BoolParameter, IntParameter, FloatParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isfile, basename, dirname
from os import symlink, getenv
from shutil import move, rmtree

from plumbum import local
from subprocess import Popen, check_call
from time import sleep
import re

from struct_pipe import StructMask

from scripts.util import N_PROC, B0_THRESHOLD, BET_THRESHOLD, QC_POLL, _mask_name, LIBDIR, \
    load_nifti, TemporaryDirectory
N_PROC= int(N_PROC)

from _glob import _glob
from _provenance import write_provenance

from warnings import warn

class SelectDwiFiles(ExternalTask):
    id = Parameter()
    ses = Parameter(default='')
    bids_data_dir = Parameter()
    dwi_template = Parameter(default='')

    def output(self):

        _, dwi= _glob(self.bids_data_dir, self.dwi_template, self.id, self.ses)
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

        write_provenance(self, self.output()['dwi'])

    def output(self):
    
        suffix= '_dwi.nii.gz'        
        dwi = local.path(self.input()['dwi'].replace('rawdata', self.derivatives_dir).rsplit(suffix)[0]+ '_desc-Xc'+ suffix)
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)

        return dict(dwi=dwi, bval=bval, bvec=bvec)


@requires(DwiAlign)
class GibbsUn(Task):

    unring_nproc= IntParameter(default=N_PROC)

    def run(self):
        cmd = (' ').join(['unring.py',
                          self.input()['dwi'],
                          self.output()['dwi'].rsplit('.nii.gz')[0],
                          str(self.unring_nproc)])
        p = Popen(cmd, shell=True)
        p.wait()
        
        write_provenance(self, self.output()['dwi'])

    def output(self):

        dwi = local.path(re.sub('_desc-Xc_', '_desc-XcUn_', self.input()['dwi']))
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)

        return dict(dwi=dwi, bval=bval, bvec=bvec)



@requires(GibbsUn)
class CnnMask(Task):

    model_folder= Parameter(default='')
    percentile= IntParameter(default=99)
    filter= Parameter(default='')

    def run(self):
        
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
                              f'-p {self.percentile}',
                              f'-filter {self.filter}' if self.filter else ''])
            p = Popen(cmd, shell=True)
            p.wait()
            
            prefix= basename(self.input()['dwi'].stem)+'_bse'
            move(prefix+'.nii.gz', self.output()['bse'])
            move(prefix+'-multi_BrainMask.nii.gz', self.output()['mask'])



        # mask the baseline image
        cmd = (' ').join(['ImageMath', '3', self.output()['bse'], 'm', self.output()['bse'], self.output()['mask']])
        p = Popen(cmd, shell=True)
        p.wait()
        
        # print instruction for quality checking
        _mask_name(self.output()['mask'])
        
        write_provenance(self, self.output()['mask'])


    def output(self):

        prefix= self.input()['dwi']._path
        desc= re.search('_desc-(.+?)_dwi.nii.gz', prefix).group(1)
        desc= 'dwi'+ desc
        outPrefix= prefix.split('_desc-')[0]+ '_desc-'+ desc
        
        bse= local.path(outPrefix+ '_bse.nii.gz')
        mask= local.path(outPrefix+ 'CNN_mask.nii.gz')
        
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
    model_folder= Parameter(default='')

    def run(self):
        
        if self.mask_method=='Bet':
            cmd = (' ').join(['bet_mask.py',
                              '-i', self.input(),
                              '-o', self.output()['mask'].rsplit('_mask.nii.gz')[0],
                              f'-f {self.bet_threshold}' if self.bet_threshold else ''])
            p = Popen(cmd, shell=True)
            p.wait()
            
            # print instruction for quality checking
            _mask_name(self.output()['mask'])
            
        
        elif self.mask_method=='CNN':
            
            pass
            # see CnnMask task above
            # also see https://github.com/pnlbwh/luigi-pnlpipe/issues/5


        # mask the baseline image
        cmd = (' ').join(['ImageMath', '3', self.output()['bse'], 'm', self.output()['bse'], auto_mask])
        p = Popen(cmd, shell=True)
        p.wait()


    def output(self):
    
        prefix= self.input().rsplit('_bse.nii.gz')[0]
        mask= local.path(prefix+ 'Bet_mask.nii.gz')
        
        return dict(bse= self.input(), mask=mask)



@requires(GibbsUn,CnnMask)
class PnlEddy(Task):
    debug = BoolParameter(default=False)
    eddy_nproc = IntParameter(default=N_PROC)
    mask_qc= BoolParameter(default=True)

    def run(self):

        # TODO check Qc_mask.nii.gz here and print message if it is not? Write a function to do that may be?
        
        for name in ['dwi', 'bval', 'bvec']:
            if not self.output()[name].exists():
                cmd = (' ').join(['pnl_eddy.py',
                                  '-i', self.input()[0]['dwi'],
                                  '--bvals', self.input()[0]['bval'],
                                  '--bvecs', self.input()[0]['bvec'],
                                  '-o', self.output()['dwi'].rsplit('.nii.gz')[0],
                                  '-d' if self.debug else '',
                                  f'-n {self.eddy_nproc}' if self.eddy_nproc else ''])
                p = Popen(cmd, shell=True)
                p.wait()

                break


        write_provenance(self, self.output()['dwi'])


    def output(self):

        eddy_prefix = self.input()[0]['dwi'].rsplit('_dwi.nii.gz')[0] + 'Ed'
        dwi = local.path(eddy_prefix + '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)
        mask= _mask_name(self.input()[1]['mask'], self.mask_qc)
        
        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=self.input()[1]['bse'], mask=mask)



@requires(GibbsUn,CnnMask)
class FslEddy(Task):
    
    mask_qc= BoolParameter(default=True)
    acqp = Parameter()
    index = Parameter()
    config = Parameter(default=pjoin(LIBDIR, 'scripts', 'eddy_config.txt'))
    useGpu = BoolParameter(default=False)
     
    def run(self):
    
        # TODO check Qc_mask.nii.gz here and print message if it is not? Write a function to do that may be?
        
        outDir= self.output()['dwi'].dirname.join('fsl_eddy')

        for name in ['dwi', 'bval', 'bvec']:
            if not self.output()[name].exists():
                if outDir.exists():
                    rmtree(outDir)

                cmd = (' ').join(['fsl_eddy.py',
                                  '--dwi', self.input()[0]['dwi'],
                                  '--bvals', self.input()[0]['bval'],
                                  '--bvecs', self.input()[0]['bvec'],
                                  '--mask', self.output()['mask'],
                                  '--acqp', self.acqp,
                                  '--index', self.index,
                                  '--config', self.config,
                                  '--eddy-cuda' if self.useGpu else '',
                                  '--out', outDir])
                p = Popen(cmd, shell=True)
                p.wait()
                
                version_file= outDir.join('fsl_version.txt')
                check_call(f'eddy_openmp 2>&1 | grep Part > {version_file}', shell= True)
                
                # fsl_eddy.py writes with this outPrefix
                outPrefix= outDir.join(self.input()[0]['dwi'].stem)+'_Ed'
                move(outPrefix+'.nii.gz',self.output()['dwi'])
                move(outPrefix+'.bval',self.output()['bval'])
                move(outPrefix+'.bvec',self.output()['bvec'])

                break


        write_provenance(self, self.output()['dwi'])


        # self.dwi= self.output()['dwi']
        # yield self.clone(BseExtract)


    def output(self):
    
        eddy_prefix= self.input()[0]['dwi'].rsplit('_dwi.nii.gz')[0]+ 'Ed'
        dwi = local.path(eddy_prefix+ '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth= 2)
        bvec = dwi.with_suffix('.bvec', depth= 2)
        mask= _mask_name(self.input()[1]['mask'], self.mask_qc)
        
        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=self.input()[1]['bse'], mask=mask)



@inherits(FslEddy, PnlEddy, StructMask, BseExtract)
class EddyEpi(Task):
    debug = BoolParameter(default=False)
    epi_nproc = IntParameter(default=N_PROC)
    eddy_task = Parameter()

    def requires(self):
        self.eddy_task= self.eddy_task.lower()

        if self.eddy_task=='pnleddy':
            return dict(eddy=self.clone(PnlEddy), t2=self.clone(StructMask))
        elif self.eddy_task=='fsleddy':
            return dict(eddy=self.clone(FslEddy), t2=self.clone(StructMask))
        else:
            raise ValueError('Supported eddy tasks are {PnlEddy,FslEddy}. '
                f'Correct the value of eddy_task in {getenv("LUIGI_CONFIG_PATH")}')

    def run(self):

        eddy_epi_prefix = self.output()['dwi'].rsplit('.nii.gz')[0]

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

                move(eddy_epi_prefix + '_mask.nii.gz', self.output()['mask'])

                break


        write_provenance(self, self.output()['dwi'])


        self.dwi = self.output()['dwi']
        yield self.clone(BseExtract)

    def output(self):

        eddy_epi_prefix = self.input()['eddy']['dwi'].rsplit('_dwi.nii.gz')[0] + 'Ep'
        dwi = local.path(eddy_epi_prefix + '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)

        # adding EdEp suffix to be consistent with dwi
        mask_prefix = self.input()['eddy']['mask'].rsplit('_mask.nii.gz')[0] + 'EdEp'

        # ENH
        # two things could be done:
        # * introduce `epi_mask_qc` param, separate from `dwi_mask_qc` param
        # * do not qc at all: the mask is generated at the beginning of the pipeline, hence no qc after warping
        # following the latter at this time
        mask = local.path(mask_prefix+ '_mask.nii.gz')

        # adding EdEp suffix to be consistent with dwi
        bse_prefix = self.input()['eddy']['bse'].rsplit('_bse.nii.gz')[0] + 'EdEp'
        bse = local.path(bse_prefix + '_bse.nii.gz')

        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)


@inherits(GibbsUn,CnnMask)
class TopupEddy(Task):

    mask_qc= BoolParameter(default=True)
    
    pa_ap_template = Parameter(default='')
    acqp = Parameter()
    config = Parameter(default=pjoin(LIBDIR, 'scripts', 'eddy_config.txt'))

    useGpu = BoolParameter(default=False)
    numb0 = Parameter(default=1)
    whichVol = Parameter(default='1')
    scale = Parameter(default=2)
    
    TopupOutDir= Parameter(default='fsl_eddy')

    def requires(self):

        pa_template, ap_template= self.pa_ap_template.split(',')

        # acq-PA
        self.dwi_template= pa_template
        # pa= self.clone(DwiAlign)
        pa= self.clone(GibbsUn)
        pa_mask= self.clone(CnnMask)

        # acq-AP
        self.dwi_template= ap_template
        # ap= self.clone(DwiAlign)
        ap= self.clone(GibbsUn)
        ap_mask= self.clone(CnnMask)
        
        
        return (pa, pa_mask, ap, ap_mask)

    def run(self):

        # TODO check Qc_mask.nii.gz here and print message if it is not? Write a function to do that may be?
        mask_pa= _mask_name(self.input()[1]['mask'], self.mask_qc)
        mask_ap= _mask_name(self.input()[3]['mask'], self.mask_qc)
        if not(mask_pa.exists() and mask_ap.exists()):
            raise FileNotFoundError(f'One or both *Qc_mask.nii.gz do not exist')
            
        outDir = self.output()['dwi'].dirname.join(self.TopupOutDir)

        for name in ['dwi', 'bval', 'bvec']:
            if not self.output()[name].exists():
                if outDir.exists():
                   rmtree(outDir)
                cmd = (' ').join(['fsl_topup_epi_eddy.py',
                                  '--imain', '{},{}'.format(self.input()[0]['dwi'],self.input()[2]['dwi']),
                                  '--bvals', '{},{}'.format(self.input()[0]['bval'],self.input()[2]['bval']),
                                  '--bvecs', '{},{}'.format(self.input()[0]['bvec'],self.input()[2]['bvec']),
                                  '--mask', '{},{}'.format(mask_pa,mask_ap),
                                  '--acqp', self.acqp,
                                  '--config', self.config,
                                  '--eddy-cuda' if self.useGpu else '',
                                  '--whichVol', self.whichVol,
                                  '--numb0', self.numb0,
                                  '--scale', self.scale,
                                  '--out', outDir])
                p = Popen(cmd, shell=True)
                p.wait()

                version_file = outDir.join('fsl_version.txt')
                check_call(f'eddy_openmp 2>&1 | grep Part > {version_file}', shell=True)


                with open(outDir.join('.outPrefix.txt')) as f:
                    outPrefix= outDir.join(f.read().strip())

                move(outPrefix + '.nii.gz', self.output()['dwi'])
                move(outPrefix + '.bval', self.output()['bval'])
                move(outPrefix + '.bvec', self.output()['bvec'])

                move(outPrefix + '_mask.nii.gz', self.output()['mask'])
                move(outDir / 'B0_PA_AP_corrected_mean.nii.gz', self.output()['bse'])

                break
        
        write_provenance(self, self.output()['dwi'])


    def output(self):

        eddy_epi_prefix= self.input()[0]['dwi'].rsplit('_dwi.nii.gz')[0]
        eddy_epi_prefix= eddy_epi_prefix.replace('_acq-PA','')
        eddy_epi_prefix= eddy_epi_prefix.replace('_acq-AP','')
        eddy_epi_prefix+= 'EdEp'

        # find dir field
        if '_dir-' in self.input()[0]['dwi'] and '_dir-' in self.input()[1]['dwi'] and self.whichVol == '1,2':
            dir= load_nifti(self.input()[0]['dwi']).shape[3]+ load_nifti(self.input()[1]['dwi']).shape[3]
            eddy_epi_prefix= local.path(re.sub('_dir-(.+?)_', f'_dir-{dir}_', eddy_epi_prefix))

        dwi = local.path(eddy_epi_prefix+ '_dwi.nii.gz')
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)

        # adding EdEp suffix to be consistent with dwi
        mask_prefix = dwi.rsplit('_desc-')[0]
        desc= re.search('_desc-(.+?)_mask.nii.gz', basename(self.input()[1]['mask'])).group(1)
        desc= desc+ 'EdEp'
        mask_prefix= mask_prefix+ '_desc-'+ desc

        mask = local.path(mask_prefix+ '_mask.nii.gz')

        bse_prefix= dwi._path
        desc= re.search('_desc-(.+?)_dwi.nii.gz', bse_prefix).group(1)
        desc= 'dwi'+ desc
        bse= local.path(bse_prefix.split('_desc-')[0]+ '_desc-'+ desc+ '_bse.nii.gz')

        return dict(dwi=dwi, bval=bval, bvec=bvec, bse=bse, mask=mask)



@inherits(PnlEddy, FslEddy, EddyEpi, TopupEddy)
class Ukf(Task):

    ukf_params = Parameter(default='')
    bhigh = IntParameter(default=-1)
    eddy_epi_task = Parameter()

    def requires(self):
        self.eddy_epi_task=self.eddy_epi_task.lower()

        if self.eddy_epi_task=='pnleddy':
            return self.clone(PnlEddy)
        elif self.eddy_epi_task=='fsleddy':
            return self.clone(FslEddy)
        elif self.eddy_epi_task=='eddyepi':
            return self.clone(EddyEpi)
        elif self.eddy_epi_task=='topupeddy':
            return self.clone(TopupEddy)
        else:
            raise ValueError('Supported epi tasks are {EddyEpi,TopupEddy}. '
                f'Correct the value of eddy_epi_task in {getenv("LUIGI_CONFIG_PATH")}')


    def run(self):
        self.output().dirname.mkdir()

        cmd = (' ').join(['ukf.py',
                          '-i', self.input()['dwi'],
                          '--bvals', self.input()['bval'],
                          '--bvecs', self.input()['bvec'],
                          '-m', self.input()['mask'],
                          '-o', self.output(),
                          f'--bhigh {self.bhigh}' if self.bhigh>0 else '',
                          f'--params {self.ukf_params}' if self.ukf_params else ''])
        p = Popen(cmd, shell=True)
        p.wait()

        write_provenance(self)


    def output(self):
        return local.path(self.input()['dwi'].replace('/dwi/', '/tracts/').replace('_dwi.nii.gz', '.vtk'))



@requires(Ukf)
class Wma800(Task):

    slicer_exec= Parameter()
    FiberTractMeasurements= Parameter()
    atlas= Parameter()
    wma_nproc= IntParameter(default=N_PROC)
    xvfb= IntParameter(default=1)
    wma_cleanup= IntParameter(default=0)

    def run(self):

        cmd = (' ').join(['wm_apply_ORG_atlas_to_subject.sh',
                          '-i', self.input(),
                          '-a', self.atlas,
                          f'-s "{self.slicer_exec}"',
                          f'-m "{self.FiberTractMeasurements}"',
                          f'-x {self.xvfb}',
                          f'-n {self.wma_nproc}',
                          f'-c {self.wma_cleanup}',
                          '-d 1',
                          '-o', self.output()])
        p = Popen(cmd, shell=True)
        p.wait()

        write_provenance(self)

    def output(self):
        return self.input().dirname.join('wma800')

