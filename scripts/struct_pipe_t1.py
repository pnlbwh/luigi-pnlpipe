#!/usr/bin/env python

import luigi
from luigi import Parameter, LocalTarget
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isdir

from plumbum import local
from shutil import rmtree

from _define_outputs import define_outputs_wf, create_dirs
from util import N_PROC

from subprocess import Popen


class SelectFiles(luigi.Task):
    id = Parameter()
    bids_data_dir = Parameter()
    struct_template = Parameter()

    def output(self):
        id_template = self.struct_template.replace('id', self.id)

        struct = local.path(glob(pjoin(abspath(self.bids_data_dir), id_template))[0])

        return struct


@requires(SelectFiles)
class StructAlign(luigi.Task):
    struct_align_prefix = Parameter()

    def run(self):
        cmd = (' ').join(['align.py',
                          '-i', self.input(),
                          '-o', self.struct_align_prefix])
        p = Popen(cmd, shell=True)
        p.wait()


    def output(self):
        aligned = self.struct_align_prefix.with_suffix('.nii.gz')

        return dict(aligned= aligned)


@requires(StructAlign)
class StructMask(luigi.Task):

    mabs_mask_prefix= luigi.Parameter()

    # for atlas.py
    debug= luigi.BoolParameter(default= False)
    csvFile= luigi.Parameter(default= None)
    fusion= luigi.Parameter(default= None)
    mabs_mask_nproc= luigi.Parameter(default= None)

    # for makeRigidMask.py
    struct_img= luigi.Parameter(default= None)
    struct_label= luigi.Parameter(default= None)


    def run(self):

        if self.csvFile:
            cmd = (' ').join(['atlas.py',
                              '-t', self.input()['aligned'],
                              '--train', self.csvFile,
                              '-o', self.mabs_mask_prefix,
                              '-n', self.mabs_mask_nproc,
                              '-d' if self.debug else '',
                              f'--fusion {self.fusion}' if self.fusion else ''])

            p = Popen(cmd, shell=True)
            p.wait()

        else:
            cmd = (' ').join(['makeRigidMask.py',
                              '-t', self.input()['aligned'],
                              '-o', self.output()['mabs_mask'],
                              '-i', self.struct_img,
                              '-l', self.struct_label])

            p = Popen(cmd, shell=True)
            p.wait()


    def output(self):
        return dict(mabs_mask= local.path(self.mabs_mask_prefix._path + '_mask.nii.gz'))


class GenerateStructMask(luigi.WrapperTask):

    bids_data_dir= luigi.Parameter()
    cases= luigi.ListParameter()
    struct_template = luigi.Parameter()

    # for atlas.py
    debug= luigi.BoolParameter(default=False)
    csvFile= luigi.Parameter(default='')
    fusion= luigi.Parameter(default='')
    mabs_mask_nproc= luigi.Parameter(default='')

    # for makeRigidMask.py
    struct_img= luigi.Parameter(default='')
    struct_label= luigi.Parameter(default='')


    def requires(self):
        bids_derivatives = pjoin(abspath(bids_data_dir), 'derivatives', 'luigi-pnlpipe')
        for id in cases:

            inter= define_outputs_wf(id, bids_derivatives)

            yield StructMask(id=id,
                             bids_data_dir=self.bids_data_dir,
                             struct_template=self.struct_template,
                             struct_align_prefix=inter['t1_align_prefix'],
                             mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                             debug= self.debug,
                             csvFile= self.csvFile,
                             fusion= self.fusion,
                             mabs_mask_nproc= self.mabs_mask_nproc,
                             struct_img= self.struct_img,
                             struct_label= self.struct_label)



@inherits(StructAlign,StructMask)
class FreesurferT1(luigi.Task):

    freesurfer_nproc= luigi.Parameter()
    expert_file= luigi.Parameter()
    no_hires= luigi.Parameter()
    no_skullstrip= luigi.Parameter()
    outDir= luigi.Parameter()

    def requires(self):
        return dict(aligned= self.clone(StructAlign), mask= self.clone(StructMask))

    def run(self):
        cmd = (' ').join(['fs.py',
                          '-i', self.input()['aligned'],
                          '-m', self.input()['mask'],
                          '-o', self.outDir,
                          '-n' if self.freesurfer_nproc else '',
                          '--expert' if self.expert_file else '',
                          '--nohires' if self.no_hires else '',
                          '--noskullstrip' if self.no_skullstrip else ''])

        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return dict(fsdir= self.outDir)



if __name__ == '__main__':

    bids_data_dir = '/home/tb571/Downloads/INTRuST_BIDS/'
    bids_derivatives = pjoin(abspath(bids_data_dir), 'derivatives', 'luigi-pnlpipe')

    # cases= ['003GNX007']
    # cases= ['003GNX012', '003GNX021']
    cases = ['003GNX007', '003GNX012', '003GNX021']

    overwrite = True
    if overwrite:
        try:
            for id in cases:
                p= Popen(f'rm -rf {bids_derivatives}/sub-{id}/anat', shell= True)
                p.wait()
        except:
            pass


    create_dirs(cases, bids_derivatives)

    t1_template = 'sub-id/anat/*_T1w.nii.gz'
    t2_template = 'sub-id/anat/*_T2w.nii.gz'

    # atlas.py
    mabs_mask_nproc= N_PROC
    fusion= '' # 'avg', 'wavg', or 'antsJointFusion'
    debug = False
    t1CsvFile= '/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT1AHCC-8141805/trainingDataT1Masks-hdr.csv'
    # t2CsvFile= '' # '/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT2Masks-12a14d9/trainingDataT2Masks-hdr.csv'

    # makeRigidMask.py
    t1SiteImg= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T1w.nii.gz'
    t1SiteMask= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T1wXcMabs_mask.nii.gz'
    # t2SiteImg= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T2w.nii.gz'
    # t2SiteMask= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T2wXcMabs_mask.nii.gz'

    # fs.py
    freesurfer_nproc= 1
    expert_file= ''
    no_hires= False
    no_skullstrip= False


    luigi.build([GenerateStructMask(bids_data_dir = bids_data_dir,
                                    cases = cases,
                                    struct_template = t1_template,
                                    debug = debug,
                                    csvFile = t1CsvFile,
                                    struct_img = t1SiteImg,
                                    struct_label = t1SiteMask,
                                    fusion = fusion,
                                    mabs_mask_nproc = mabs_mask_nproc)], workers=3)

