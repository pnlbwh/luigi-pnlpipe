#!/usr/bin/env python

import luigi
from luigi import Parameter, ListParameter, BoolParameter
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

    mabs_mask_prefix= Parameter()

    # for atlas.py
    debug= BoolParameter(default= False)
    csvFile= Parameter(default= None)
    fusion= Parameter(default= None)
    mabs_mask_nproc= Parameter(default= None)

    # for makeRigidMask.py
    struct_img= Parameter(default= None)
    struct_label= Parameter(default= None)

    slicer_exec= Parameter()


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

        if self.slicer_exec:
            cmd= (' ').join([self.slicer_exec, '--python-code',
                            '\"slicer.util.loadVolume(\'{}\'); '
                            'slicer.util.loadLabelVolume(\'{}\')\"'
                            .format(self.input()['aligned'],self.output()['mabs_mask'])])

            p = Popen(cmd, shell= True)
            p.wait()


    def output(self):
        return dict(mabs_mask= local.path(self.mabs_mask_prefix._path + '_mask.nii.gz'), aligned= self.input()['aligned'])



class T1T2Mask(luigi.Task):

    bids_data_dir= Parameter()
    bids_derivatives= Parameter()
    id= Parameter()
    t1_template= Parameter(default='')
    t2_template= Parameter(default='')

    # for atlas.py
    debug= BoolParameter(default=False)
    t1_csvFile= Parameter(default='')
    t2_csvFile= Parameter(default='')
    fusion= Parameter(default='')
    mabs_mask_nproc= Parameter(default='')

    # for makeRigidMask.py
    t1_struct_img= Parameter(default='')
    t1_struct_label= Parameter(default='')
    t2_struct_img= Parameter(default='')
    t2_struct_label= Parameter(default='')

    slicer_exec= Parameter(default='')


    def requires(self):

        inter= define_outputs_wf(self.id, self.bids_derivatives)

        yield StructMask(id=self.id,
                         bids_data_dir=self.bids_data_dir,
                         struct_template=self.t1_template,
                         struct_align_prefix=inter['t1_align_prefix'],
                         mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                         debug= self.debug,
                         csvFile= self.t1_csvFile,
                         fusion= self.fusion,
                         mabs_mask_nproc= self.mabs_mask_nproc,
                         struct_img= self.t1_struct_img,
                         struct_label= self.t1_struct_label,
                         slicer_exec= self.slicer_exec)


        yield StructMask(id=self.id,
                         bids_data_dir=self.bids_data_dir,
                         struct_template=self.t2_template,
                         struct_align_prefix=inter['t2_align_prefix'],
                         mabs_mask_prefix=inter['t2_mabsmask_prefix'],
                         debug= self.debug,
                         csvFile= self.t2_csvFile,
                         fusion= self.fusion,
                         mabs_mask_nproc= self.mabs_mask_nproc,
                         struct_img= self.t2_struct_img,
                         struct_label= self.t2_struct_label,
                         slicer_exec=self.slicer_exec)

    def output(self):
        inter= define_outputs_wf(self.id, self.bids_derivatives)
        return dict(t1_aligned= inter['t1_align_prefix'].with_suffix('.nii.gz'),
                    t1_mask= local.path(inter['t1_mabsmask_prefix']._path+'_mask.nii.gz'),
                    t2_aligned= inter['t2_align_prefix'].with_suffix('.nii.gz'),
                    t2_mask= local.path(inter['t2_mabsmask_prefix']._path+'_mask.nii.gz'))



@inherits(StructAlign,StructMask)
class FreesurferT1(luigi.Task):

    freesurfer_nproc= Parameter()
    expert_file= Parameter()
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)
    outDir= Parameter()

    def requires(self):
        return dict(aligned= self.clone(StructAlign), mabs_mask= self.clone(StructMask))

    def run(self):
        cmd = (' ').join(['fs.py',
                          '-i', self.input()['aligned']['aligned'],
                          '-m', self.input()['mabs_mask']['mabs_mask'],
                          '-o', self.outDir,
                          f'-n {self.freesurfer_nproc}' if self.freesurfer_nproc else '',
                          f'--expert {self.expert_file}' if self.expert_file else '',
                          '--nohires' if self.no_hires else '',
                          '--noskullstrip' if self.no_skullstrip else ''])

        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return dict(fsdir= self.outDir)


@requires(T1T2Mask)
class FreesurferT1T2(luigi.Task):

    freesurfer_nproc= Parameter()
    expert_file= Parameter()
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)
    outDir= Parameter()

    def run(self):

        cmd = (' ').join(['fs.py',
                          '-i', self.input()['t1_aligned'],
                          '-m', self.input()['t1_mask'],
                          '--t2', self.input()['t2_aligned'],
                          '--t2mask', self.input()['t2_mask'],
                          '-o', self.outDir,
                          f'-n {self.freesurfer_nproc}' if self.freesurfer_nproc else '',
                          f'--expert {self.expert_file}' if self.expert_file else '',
                          '--nohires' if self.no_hires else '',
                          '--noskullstrip' if self.no_skullstrip else ''])

        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return dict(fsdir= self.outDir)


class GenerateAllStructMask(luigi.WrapperTask):

    bids_data_dir= Parameter()
    bids_derivatives= Parameter()
    cases= ListParameter()
    t1_template= Parameter(default='')
    t2_template= Parameter(default='')

    # for atlas.py
    debug= BoolParameter(default=False)
    t1_csvFile= Parameter(default='')
    t2_csvFile= Parameter(default='')
    fusion= Parameter(default='')
    mabs_mask_nproc= Parameter(default='')

    # for makeRigidMask.py
    t1_struct_img= Parameter(default='')
    t1_struct_label= Parameter(default='')
    t2_struct_img= Parameter(default='')
    t2_struct_label= Parameter(default='')

    slicer_exec= Parameter(default='')

    def requires(self):
        for id in self.cases:

            inter= define_outputs_wf(id, self.bids_derivatives)

            yield StructMask(id=id,
                             bids_data_dir=self.bids_data_dir,
                             struct_template=self.t1_template,
                             struct_align_prefix=inter['t1_align_prefix'],
                             mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                             debug= self.debug,
                             csvFile= self.t1_csvFile,
                             fusion= self.fusion,
                             mabs_mask_nproc= self.mabs_mask_nproc,
                             struct_img= self.t1_struct_img,
                             struct_label= self.t1_struct_label,
                             slicer_exec= self.slicer_exec)

            if not self.t2_template:
                continue

            yield StructMask(id=id,
                             bids_data_dir=self.bids_data_dir,
                             struct_template=self.t2_template,
                             struct_align_prefix=inter['t2_align_prefix'],
                             mabs_mask_prefix=inter['t2_mabsmask_prefix'],
                             debug= self.debug,
                             csvFile= self.t2_csvFile,
                             fusion= self.fusion,
                             mabs_mask_nproc= self.mabs_mask_nproc,
                             struct_img= self.t2_struct_img,
                             struct_label= self.t2_struct_label,
                             slicer_exec=self.slicer_exec)


class RunFreesurferT1(luigi.WrapperTask):

    bids_data_dir= Parameter()
    bids_derivatives = Parameter()
    cases= ListParameter()
    t1_template= Parameter(default='')

    # for atlas.py
    debug= BoolParameter(default=False)
    t1_csvFile= Parameter(default='')
    fusion= Parameter(default='')
    mabs_mask_nproc= Parameter(default='')

    # for makeRigidMask.py
    t1_struct_img= Parameter(default='')
    t1_struct_label= Parameter(default='')

    slicer_exec= Parameter(default='')

    # for fs.py
    freesurfer_nproc= Parameter()
    expert_file= Parameter()
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)

    def requires(self):

        for id in self.cases:

            inter= define_outputs_wf(id, self.bids_derivatives)

            yield FreesurferT1(id=id,
                               bids_data_dir=self.bids_data_dir,
                               struct_template=self.t1_template,
                               struct_align_prefix=inter['t1_align_prefix'],
                               mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                               debug= self.debug,
                               csvFile= self.t1_csvFile,
                               fusion= self.fusion,
                               mabs_mask_nproc= self.mabs_mask_nproc,
                               struct_img= self.t1_struct_img,
                               struct_label= self.t1_struct_label,
                               slicer_exec= self.slicer_exec,
                               freesurfer_nproc= self.freesurfer_nproc,
                               expert_file= self.expert_file,
                               no_hires= self.no_hires,
                               no_skullstrip= self.no_skullstrip,
                               outDir= inter['fs_dir'])



class RunFreesurferT1T2(luigi.WrapperTask):

    bids_data_dir = Parameter()
    bids_derivatives = Parameter()
    cases = ListParameter()
    t1_template = Parameter(default='')
    t2_template = Parameter(default='')

    # for atlas.py
    debug = BoolParameter(default=False)
    t1_csvFile = Parameter(default='')
    t2_csvFile = Parameter(default='')
    fusion = Parameter(default='')
    mabs_mask_nproc = Parameter(default='')

    # for makeRigidMask.py
    t1_struct_img = Parameter(default='')
    t1_struct_label = Parameter(default='')
    t2_struct_img = Parameter(default='')
    t2_struct_label = Parameter(default='')

    slicer_exec = Parameter(default='')

    # for fs.py
    freesurfer_nproc= Parameter()
    expert_file= Parameter()
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)

    def requires(self):

        for id in self.cases:
            
            inter= define_outputs_wf(id, self.bids_derivatives)
            
            yield FreesurferT1T2(bids_data_dir = self.bids_data_dir,
                                 bids_derivatives = self.bids_derivatives,
                                 id = id,
                                 t1_template = self.t1_template,
                                 t2_template = self.t2_template,
                                 debug = self.debug,
                                 t1_csvFile = self.t1_csvFile,
                                 t2_csvFile = self.t2_csvFile,
                                 t1_struct_img = self.t1_struct_img,
                                 t1_struct_label = self.t1_struct_label,
                                 t2_struct_img=self.t2_struct_img,
                                 t2_struct_label=self.t2_struct_label,
                                 fusion = self.fusion,
                                 mabs_mask_nproc = self.mabs_mask_nproc,
                                 slicer_exec=self.slicer_exec,
                                 freesurfer_nproc= self.freesurfer_nproc,
                                 expert_file= self.expert_file,
                                 no_hires= self.no_hires,
                                 no_skullstrip= self.no_skullstrip,
                                 outDir= inter['fs_dir'])



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
    t1CsvFile= ''#'/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT1AHCC-8141805/trainingDataT1Masks-hdr.csv'
    t2CsvFile= ''#'/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT2Masks-12a14d9/trainingDataT2Masks-hdr.csv'

    # makeRigidMask.py
    t1SiteImg= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T1w.nii.gz'
    t1SiteMask= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T1wXcMabs_mask.nii.gz'
    t2SiteImg= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T2w.nii.gz'
    t2SiteMask= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T2wXcMabs_mask.nii.gz'

    # fs.py
    freesurfer_nproc= '1'
    expert_file= ''
    no_hires= False
    no_skullstrip= True

    slicer_exec= ''#'/home/tb571/Downloads/Slicer-4.10.2-linux-amd64/Slicer'

    inter= define_outputs_wf(cases[0], bids_derivatives)

    # individual task
    luigi.build([StructMask(id=cases[0],
                            bids_data_dir=bids_data_dir,
                            struct_template=t1_template,
                            struct_align_prefix=inter['t1_align_prefix'],
                            mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                            debug=debug,
                            csvFile=t1CsvFile,
                            fusion=fusion,
                            mabs_mask_nproc=mabs_mask_nproc,
                            struct_img=t1SiteImg,
                            struct_label=t1SiteMask,
                            slicer_exec=slicer_exec)])
    

    # individual task
    luigi.build([T1T2Mask(bids_data_dir = bids_data_dir,
                          bids_derivatives=bids_derivatives,
                          id = cases[0],
                          t1_template = t1_template,
                          t2_template= t2_template,
                          debug = debug,
                          t1_csvFile = t1CsvFile,
                          t2_csvFile= t2CsvFile,
                          t1_struct_img = t1SiteImg,
                          t1_struct_label = t1SiteMask,
                          t2_struct_img = t2SiteImg,
                          t2_struct_label = t2SiteMask,
                          fusion = fusion,
                          mabs_mask_nproc = mabs_mask_nproc,
                          slicer_exec=slicer_exec)])

    
    
    # individual task
    luigi.build([FreesurferT1(bids_data_dir = bids_data_dir,
                              id  = cases[0],
                              struct_template = t1_template,
                              struct_align_prefix=inter['t1_align_prefix'],
                              mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                              debug = debug,
                              csvFile = t1CsvFile,
                              fusion = fusion,
                              mabs_mask_nproc = mabs_mask_nproc,
                              struct_img = t1SiteImg,
                              struct_label = t1SiteMask,
                              slicer_exec=slicer_exec,
                              freesurfer_nproc= freesurfer_nproc,
                              expert_file= expert_file,
                              no_hires= no_hires,
                              no_skullstrip= no_skullstrip,
                              outDir= inter['fs_dir'])])


    # individual task
    luigi.build([FreesurferT1T2(bids_data_dir = bids_data_dir,
                                bids_derivatives=bids_derivatives,
                                id  = cases[0],
                                t1_template = t1_template,
                                t2_template = t2_template,
                                debug = debug,
                                t1_csvFile = t1CsvFile,
                                t2_csvFile = t2CsvFile,
                                t1_struct_img = t1SiteImg,
                                t1_struct_label = t1SiteMask,
                                t2_struct_img=t2SiteImg,
                                t2_struct_label=t2SiteMask,
                                fusion = fusion,
                                mabs_mask_nproc = mabs_mask_nproc,
                                slicer_exec=slicer_exec,
                                freesurfer_nproc= freesurfer_nproc,
                                expert_file= expert_file,
                                no_hires= no_hires,
                                no_skullstrip= no_skullstrip,
                                outDir= inter['fs_dir'])])



    # group task
    luigi.build([GenerateAllStructMask(bids_data_dir = bids_data_dir,
                                       bids_derivatives = bids_derivatives,
                                       cases = cases,
                                       t1_template = t1_template,
                                       t2_template= t2_template,
                                       debug = debug,
                                       t1_csvFile = t1CsvFile,
                                       t2_csvFile= t2CsvFile,
                                       t1_struct_img = t1SiteImg,
                                       t1_struct_label = t1SiteMask,
                                       t2_struct_img = t2SiteImg,
                                       t2_struct_label = t2SiteMask,
                                       fusion = fusion,
                                       mabs_mask_nproc = mabs_mask_nproc,
                                       slicer_exec=slicer_exec)], workers=4)
    
    
    # group task
    luigi.build([RunFreesurferT1(bids_data_dir = bids_data_dir,
                                 bids_derivatives = bids_derivatives,
                                 cases  = cases,
                                 t1_template = t1_template,
                                 debug = debug,
                                 t1_csvFile = t1CsvFile,
                                 t1_struct_img = t1SiteImg,
                                 t1_struct_label = t1SiteMask,
                                 fusion = fusion,
                                 mabs_mask_nproc = mabs_mask_nproc,
                                 slicer_exec=slicer_exec,
                                 freesurfer_nproc= freesurfer_nproc,
                                 expert_file= expert_file,
                                 no_hires= no_hires,
                                 no_skullstrip= no_skullstrip)], workers= 4)
    
    
    # group task
    luigi.build([RunFreesurferT1T2(bids_data_dir = bids_data_dir,
                                   bids_derivatives = bids_derivatives,
                                   cases = cases,
                                   t1_template = t1_template,
                                   t2_template = t2_template,
                                   debug = debug,
                                   t1_csvFile = t1CsvFile,
                                   t2_csvFile = t2CsvFile,
                                   t1_struct_img = t1SiteImg,
                                   t1_struct_label = t1SiteMask,
                                   t2_struct_img=t2SiteImg,
                                   t2_struct_label=t2SiteMask,
                                   fusion = fusion,
                                   mabs_mask_nproc = mabs_mask_nproc,
                                   slicer_exec=slicer_exec,
                                   freesurfer_nproc= freesurfer_nproc,
                                   expert_file= expert_file,
                                   no_hires= no_hires,
                                   no_skullstrip= no_skullstrip)], workers= 4)
    

