#!/usr/bin/env python

import time
import luigi
from luigi import Parameter, BoolParameter, ListParameter, FloatParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isdir

from plumbum import local
from shutil import rmtree

from _define_outputs import define_outputs_wf, create_dirs
from struct_pipe_t1_t2 import StructMask

from util import N_PROC, B0_THRESHOLD, BET_THRESHOLD

from subprocess import Popen


class SelectFiles(luigi.Task):
    id = Parameter()
    bids_data_dir = Parameter()
    dwi_template = Parameter()

    def output(self):
        id_template = self.dwi_template.replace('id', self.id)

        dwi = local.path(glob(pjoin(abspath(self.bids_data_dir), id_template))[0])
        bval = dwi.with_suffix('.bval', depth=2)
        bvec = dwi.with_suffix('.bvec', depth=2)

        return dict(dwi=dwi, bval=bval, bvec=bvec)


@requires(SelectFiles)
class DwiAlign(luigi.Task):
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

        return dict(aligned_dwi=dwi, aligned_bval=bval, aligned_bvec=bvec)


@requires(DwiAlign)
class BseExtract(luigi.Task):
    bse_prefix = Parameter()
    b0_threshold= FloatParameter()
    which_bse= Parameter(default='')

    def run(self):

        cmd = (' ').join(['bse.py',
                          '-i', self.input()['aligned_dwi'],
                          '--bvals', self.input()['aligned_bval'],
                          '-o', self.output(),
                          f'-t {self.b0_threshold}' if self.b0_threshold else '',
                          self.which_bse if self.which_bse else ''])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.bse_prefix.with_suffix('.nii.gz')


@requires(BseExtract)
class BetMask(luigi.Task):
    bse_betmask_prefix = Parameter()
    bet_threshold= Parameter(default='')
    slicer_exec= Parameter()

    def run(self):
        cmd = (' ').join(['bet_mask.py',
                          '-i', self.input(),
                          '-o', self.bse_betmask_prefix._path,
                          f'-f {self.bet_threshold}' if self.bet_threshold else ''])
        p = Popen(cmd, shell=True)
        p.wait()

        if self.slicer_exec:
            cmd= (' ').join([self.slicer_exec, '--python-code',
                            '\"slicer.util.loadVolume(\'{}\'); '
                            'slicer.util.loadLabelVolume(\'{}\')\"'
                            .format(self.input(),self.output())])

            p = Popen(cmd, shell= True)
            p.wait()

    def output(self):
        return dict(mask= local.path(self.bse_betmask_prefix._path + '_mask.nii.gz'), bse= self.input())


@requires(DwiAlign)
class PnlEddy(luigi.Task):
    eddy_prefix = Parameter()
    debug= BoolParameter(default='')
    eddy_nproc= Parameter(default='')

    def run(self):
        cmd = (' ').join(['pnl_eddy.py',
                          '-i', self.input()['aligned_dwi'],
                          '--bvals', self.input()['aligned_bval'],
                          '--bvecs', self.input()['aligned_bvec'],
                          '-o', self.eddy_prefix,
                          '-d' if self.debug else '',
                          f'-n {self.eddy_nproc}' if self.eddy_nproc else ''])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        dwi = self.eddy_prefix.with_suffix('.nii.gz')
        bval = self.eddy_prefix.with_suffix('.bval')
        bvec = self.eddy_prefix.with_suffix('.bvec')

        return dict(eddy_dwi=dwi, eddy_bval=bval, eddy_bvec=bvec)


@inherits(DwiAlign,BetMask)
class FslEddy(luigi.Task):
    eddy_prefix = Parameter()
    acqp= Parameter()
    index= Parameter()
    config= Parameter()

    def requires(self):
        return dict(aligned= self.clone(DwiAlign), bet=self.clone(BetMask))

    def run(self):
        cmd = (' ').join(['fsl_eddy.py',
                          '--dwi', self.input()['aligned']['aligned_dwi'],
                          '--bvals', self.input()['aligned']['aligned_bval'],
                          '--bvecs', self.input()['aligned']['aligned_bvec'],
                          '--mask', self.input()['bet']['mask'],
                          '-o', self.eddy_prefix,
                          '--acqp', self.acqp,
                          '--index', self.index,
                          '--config', self.config])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        dwi = self.eddy_prefix.with_suffix('.nii.gz')
        bval = self.eddy_prefix.with_suffix('.bval')
        bvec = self.eddy_prefix.with_suffix('.bvec')

        return dict(eddy_dwi=dwi, eddy_bval=bval, eddy_bvec=bvec)


@inherits(PnlEddy,BetMask,StructMask)
class PnlEpi(luigi.Task):
    eddy_epi_prefix = Parameter()
    debug= BoolParameter(default='')
    epi_nproc= Parameter(default='')

    def requires(self):
        return dict(eddy= self.clone(PnlEddy), bet= self.clone(BetMask), t2= self.clone(StructMask))

    def run(self):
        cmd = (' ').join(['pnl_epi.py',
                          '--dwi', self.input()['eddy']['eddy_dwi'],
                          '--bvals', self.input()['eddy']['eddy_bval'],
                          '--bvecs', self.input()['eddy']['eddy_bvec'],
                          '--dwimask', self.input()['bet']['mask'],
                          '--bse', self.input()['bet']['bse'],
                          '--t2', self.input()['t2']['aligned'],
                          '--t2mask', self.input()['t2']['mabs_mask'],
                          '-o', self.eddy_epi_prefix,
                          '-d' if self.debug else '',
                          f'-n {self.epi_nproc}' if self.epi_nproc else ''])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        dwi = self.eddy_epi_prefix.with_suffix('.nii.gz')
        bval = self.eddy_epi_prefix.with_suffix('.bval')
        bvec = self.eddy_epi_prefix.with_suffix('.bvec')

        return dict(epi_dwi=dwi, epi_bval=bval, epi_bvec=bvec, epi_mask= local.path(self.eddy_epi_prefix._path+'_mask.nii.gz'))



@inherits(PnlEddy,BetMask)
class PnlEddyUkf(luigi.Task):
    tract_prefix = Parameter()
    ukf_params = Parameter()

    def requires(self):
        return dict(eddy=self.clone(PnlEddy), bet=self.clone(BetMask))

    def run(self):
        cmd = (' ').join(['ukf.py',
                          '-i', self.input()['eddy']['eddy_dwi'],
                          '--bvals', self.input()['eddy']['eddy_bval'],
                          '--bvecs', self.input()['eddy']['eddy_bvec'],
                          '-m', self.input()['bet']['mask'],
                          '-o', self.output(),
                          '--params', self.ukf_params])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.tract_prefix.with_suffix('.vtk')


@requires(PnlEpi)
class PnlEddyEpiUkf(luigi.Task):
    tract_prefix = Parameter()
    ukf_params = Parameter()

    def run(self):
        cmd = (' ').join(['ukf.py',
                          '-i', self.input()['epi_dwi'],
                          '--bvals', self.input()['epi_bval'],
                          '--bvecs', self.input()['epi_bvec'],
                          '-m', self.input()['epi_mask'],
                          '-o', self.output(),
                          '--params', self.ukf_params])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.tract_prefix.with_suffix('.vtk')


@inherits(FslEddy,BetMask)
class FslEddyUkf(luigi.Task):
    tract_prefix = Parameter()
    ukf_params = Parameter()

    def requires(self):
        return dict(eddy=self.clone(FslEddy), bet=self.clone(BetMask))

    def run(self):
        cmd = (' ').join(['ukf.py',
                          '-i', self.input()['eddy']['eddy_dwi'],
                          '--bvals', self.input()['eddy']['eddy_bval'],
                          '--bvecs', self.input()['eddy']['eddy_bvec'],
                          '-m', self.input()['bet']['mask'],
                          '-o', self.output(),
                          '--params', self.ukf_params])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.tract_prefix.with_suffix('.vtk')


class PnlEddyPipe(luigi.WrapperTask):
    bids_data_dir = Parameter()
    bids_derivatives = Parameter()
    cases = ListParameter()
    dwi_template = Parameter()
    eddy_nproc= Parameter(default='')

    # bse.py
    which_bse= Parameter(default='')
    b0_threshold= FloatParameter()

    # bet_mask.py
    bet_threshold= Parameter(default='')
    slicer_exec= Parameter(default='')

    debug= BoolParameter(default='')

    # ukf.py
    ukf_params = Parameter(default='')

    def requires(self):

        for id in self.cases:

            inter = define_outputs_wf(id, self.bids_derivatives)

            yield PnlEddyUkf(id=id,
                          bids_data_dir=self.bids_data_dir,
                          dwi_template=self.dwi_template,
                          dwi_align_prefix=inter['dwi_align_prefix'],
                          eddy_prefix=inter['eddy_prefix'],
                          eddy_nproc= self.eddy_nproc,
                          bse_prefix=inter['eddy_bse_prefix'],
                          bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                          which_bse=self.which_bse,
                          b0_threshold=self.b0_threshold,
                          bet_threshold=self.bet_threshold,
                          slicer_exec= self.slicer_exec,
                          tract_prefix=inter['eddy_tract_prefix'],
                          ukf_params=self.ukf_params)



class FslEddyPipe(luigi.WrapperTask):
    bids_data_dir = Parameter()
    bids_derivatives = Parameter()
    cases = ListParameter()
    dwi_template = Parameter()
    eddy_nproc= Parameter(default='')

    # bse.py
    which_bse= Parameter(default='')
    b0_threshold= FloatParameter()

    # bet_mask.py
    bet_threshold= Parameter(default='')
    slicer_exec= Parameter(default='')

    debug= BoolParameter(default='')

    # fsl_eddy.py
    acqp= Parameter()
    index= Parameter()
    config= Parameter()

    # ukf.py
    ukf_params = Parameter(default='')

    def requires(self):

        for id in self.cases:

            inter = define_outputs_wf(id, self.bids_derivatives)

            yield FslEddyUkf(id=id,
                             bids_data_dir=self.bids_data_dir,
                             dwi_template=self.dwi_template,
                             dwi_align_prefix=inter['dwi_align_prefix'],
                             eddy_prefix=inter['eddy_prefix'],
                             acqp=self.acqp,
                             index= self.index,
                             config = self.config,
                             bse_prefix=inter['eddy_bse_prefix'],
                             bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                             which_bse=which_bse,
                             b0_threshold=b0_threshold,
                             bet_threshold=bet_threshold,
                             slicer_exec= self.slicer_exec,
                             tract_prefix=inter['eddy_tract_prefix'],
                             ukf_params=self.ukf_params)


class PnlEddyEpiPipe(luigi.WrapperTask):
    bids_data_dir = Parameter()
    bids_derivatives = Parameter()
    cases = ListParameter()
    dwi_template = Parameter()
    t2_template= Parameter()

    # bse.py
    which_bse= Parameter(default='')
    b0_threshold= FloatParameter()

    # bet_mask.py
    bet_threshold= Parameter(default='')
    slicer_exec= Parameter(default='')

    debug= BoolParameter(default='')

    # pnl_eddy.py
    eddy_nproc= Parameter(default='')
    epi_nproc= Parameter(default='')

    # atlas.py
    mabs_mask_nproc= Parameter(default='')
    fusion= Parameter(default='')
    debug = BoolParameter(default=False)
    t2_csvFile= Parameter(default='')

    # makeRigidMask.py
    t2_struct_img= Parameter(default='')
    t2_struct_label= Parameter(default='')

    # ukf.py
    ukf_params = Parameter(default='')

    def requires(self):

        for id in self.cases:

            inter = define_outputs_wf(id, self.bids_derivatives)

            yield PnlEddyEpiUkf(id=id,
                         bids_data_dir=self.bids_data_dir,
                         dwi_template=self.dwi_template,
                         dwi_align_prefix=inter['dwi_align_prefix'],
                         eddy_prefix=inter['eddy_prefix'],
                         eddy_epi_prefix=inter['eddy_epi_prefix'],
                         bse_prefix=inter['eddy_bse_prefix'],
                         bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                         which_bse=self.which_bse,
                         b0_threshold=self.b0_threshold,
                         bet_threshold=self.bet_threshold,
                         slicer_exec=self.slicer_exec,
                         debug=self.debug,
                         eddy_nproc=self.eddy_nproc,
                         epi_nproc=self.epi_nproc,
                         struct_template=self.t2_template,
                         struct_align_prefix=inter['t2_align_prefix'],
                         mabs_mask_prefix=inter['t2_mabsmask_prefix'],
                         csvFile=self.t2_csvFile,
                         struct_img= self.t2_struct_img,
                         struct_label= self.t2_struct_label,
                         fusion=self.fusion,
                         mabs_mask_nproc=self.mabs_mask_nproc,
                         tract_prefix=inter['eddy_epi_tract_prefix'],
                         ukf_params=self.ukf_params)


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
                p= Popen(f'rm -rf {bids_derivatives}/sub-{id}/dwi {bids_derivatives}/sub-{id}/fs2dwi {bids_derivatives}/sub-{id}/tracts', shell= True)
                p.wait()
        except:
            pass


    create_dirs(cases, bids_derivatives)

    dwi_template = 'sub-id/dwi/*_dwi.nii.gz'
    t2_template = 'sub-id/anat/*_T2w.nii.gz'

    # bse.py
    which_bse= '' # '', '--min', '--avg', or '--all'
    b0_threshold= B0_THRESHOLD

    # bet_mask.py
    bet_threshold= BET_THRESHOLD
    slicer_exec = ''  # '/home/tb571/Downloads/Slicer-4.10.2-linux-amd64/Slicer'

    debug= False

    # pnl_eddy.py
    eddy_nproc= N_PROC

    # pnl_epi.py
    epi_nproc= N_PROC

    # fsl_eddy.py
    acqp_file= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/acqp.txt'
    index_file= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/index.txt'
    eddy_config= '/home/tb571/luigi-pnlpipe/scripts/eddy_config.txt'

    # ukf.py
    ukf_params= '--seedingThreshold,0.4,--seedsPerVoxel,1'

    # fs2dwi.py
    mode= 'direct' # 'direct', or 'witht2'

    # atlas.py
    mabs_mask_nproc= N_PROC
    fusion= '' # 'avg', 'wavg', or 'antsJointFusion'
    t2CsvFile= ''#'/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT2Masks-12a14d9/trainingDataT2Masks-hdr.csv'

    # makeRigidMask.py
    t2SiteImg= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T2w.nii.gz'
    t2SiteMask= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T2wXcMabs_mask.nii.gz'

    inter= define_outputs_wf(cases[0], bids_derivatives)


    # group task
    luigi.build([PnlEddyPipe(bids_data_dir = bids_data_dir,
                             bids_derivatives = bids_derivatives,
                             cases = cases,
                             dwi_template = dwi_template,
                             which_bse= which_bse,
                             b0_threshold= b0_threshold,
                             bet_threshold= bet_threshold,
                             slicer_exec= slicer_exec,
                             debug= debug,
                             eddy_nproc= eddy_nproc,
                             ukf_params = ukf_params)], workers=4)


    # group task
    luigi.build([FslEddyPipe(bids_data_dir = bids_data_dir,
                             bids_derivatives = bids_derivatives,
                             cases = cases,
                             dwi_template = dwi_template,
                             which_bse= which_bse,
                             b0_threshold= b0_threshold,
                             bet_threshold= bet_threshold,
                             slicer_exec= slicer_exec,
                             acqp= acqp_file,
                             index= index_file,
                             config= eddy_config,
                             ukf_params = ukf_params)], workers=4)

    
    # group task
    luigi.build([PnlEddyEpiPipe(bids_data_dir = bids_data_dir,
                                bids_derivatives = bids_derivatives,
                                cases = cases,
                                dwi_template = dwi_template,
                                t2_template = t2_template,
                                t2_csvFile= t2CsvFile,
                                t2_struct_img= t2SiteImg,
                                t2_struct_label= t2SiteMask,
                                which_bse= which_bse,
                                b0_threshold= b0_threshold,
                                bet_threshold= bet_threshold,
                                slicer_exec= slicer_exec,
                                debug= debug,
                                eddy_nproc= eddy_nproc,
                                epi_nproc= epi_nproc,
                                ukf_params= ukf_params)], workers=4)

    
    # individual task
    luigi.build([PnlEpi(id=cases[0],
                        bids_data_dir = bids_data_dir,
                        dwi_template = dwi_template,
                        dwi_align_prefix=inter['dwi_align_prefix'],
                        eddy_prefix=inter['eddy_prefix'],
                        eddy_epi_prefix=inter['eddy_epi_prefix'],
                        bse_prefix=inter['eddy_bse_prefix'],
                        bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
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
                        csvFile=t2CsvFile,
                        fusion=fusion,
                        mabs_mask_nproc=mabs_mask_nproc,
                        struct_img=t2SiteImg,
                        struct_label=t2SiteMask)], workers=1)
    
    

    # individual task
    luigi.build([FslEddy(id=cases[0],
                         bids_data_dir=bids_data_dir,
                         dwi_template=dwi_template,
                         dwi_align_prefix=inter['dwi_align_prefix'],
                         eddy_prefix=inter['eddy_prefix'],
                         bse_prefix=inter['eddy_bse_prefix'],
                         bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                         which_bse=which_bse,
                         b0_threshold=b0_threshold,
                         bet_threshold=bet_threshold,
                         slicer_exec= slicer_exec,
                         acqp= acqp_file,
                         index= index_file,
                         config= eddy_config)], workers=1)

    
