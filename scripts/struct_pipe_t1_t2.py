#!/usr/bin/env python

from luigi import Task, build, ExternalTask, Parameter, BoolParameter, IntParameter
from luigi.util import inherits, requires
from glob import glob
from os.path import join as pjoin, abspath, isdir

from plumbum import local
from shutil import rmtree

from _define_outputs import define_outputs_wf, create_dirs
from util import N_PROC

from subprocess import Popen


class SelectStructFiles(ExternalTask):
    id = Parameter()
    bids_data_dir = Parameter()
    struct_template = Parameter(default='')

    def output(self):
        struct = glob(pjoin(abspath(self.bids_data_dir), self.struct_template.replace('id', self.id)))[0]

        return local.path(struct)


@requires(SelectStructFiles)
class StructAlign(Task):
    struct_align_prefix = Parameter(default='')

    def run(self):
        cmd = (' ').join(['align.py',
                          '-i', self.input(),
                          '-o', self.struct_align_prefix])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.struct_align_prefix.with_suffix('.nii.gz')



@requires(StructAlign)
class StructMask(Task):

    mabs_mask_prefix= Parameter(default='')

    # for atlas.py
    debug= BoolParameter(default= False)
    csvFile= Parameter(default= '')
    fusion= Parameter(default= '')
    mabs_mask_nproc= IntParameter(default= int(N_PROC))

    # for makeRigidMask.py
    model_img= Parameter(default= '')
    model_mask= Parameter(default= '')

    # for qc'ing the created mask
    slicer_exec= Parameter(default= '')


    def run(self):

        if not (self.model_img and self.model_mask):
            cmd = (' ').join(['atlas.py',
                              '-t', self.input(),
                              '--train', self.csvFile,
                              '-o', self.mabs_mask_prefix,
                              '-n', self.mabs_mask_nproc,
                              '-d' if self.debug else '',
                              f'--fusion {self.fusion}' if self.fusion else ''])

            p = Popen(cmd, shell=True)
            p.wait()

        else:
            cmd = (' ').join(['makeSynMask.py',
                              '-t', self.input(),
                              '-o', self.output()['mask'],
                              '-i', self.model_img,
                              '-l', self.model_mask])

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
        return dict(aligned= self.input(), mask=local.path(self.mabs_mask_prefix._path + '_mask.nii.gz'))



@inherits(StructMask)
class Freesurfer(Task):

    t1_template= Parameter()
    t1_align_prefix= Parameter()
    t1_mask_prefix= Parameter()
    t1_csvFile = Parameter(default='')
    t1_model_img= Parameter(default='')
    t1_model_mask= Parameter(default='')

    t2_template= Parameter(default='')
    t2_align_prefix= Parameter(default='')
    t2_mask_prefix= Parameter(default='')
    t2_csvFile = Parameter(default='')
    t2_model_img= Parameter(default='')
    t2_model_mask= Parameter(default='')

    freesurfer_nproc= IntParameter(default=1)
    expert_file= Parameter()
    no_hires= BoolParameter(default=False)
    no_skullstrip= BoolParameter(default=False)
    fs_dir= Parameter()

    def requires(self):
        self.struct_template= self.t1_template
        self.struct_align_prefix= self.t1_align_prefix
        self.mabs_mask_prefix= self.t1_mask_prefix
        self.csvFile= self.t1_csvFile
        self.model_img= self.t1_model_img
        self.model_mask= self.t1_model_mask

        t1_attr= yield self.clone(StructMask)

        if self.t2_template:
            self.struct_template = self.t2_template
            self.struct_align_prefix = self.t2_align_prefix
            self.mabs_mask_prefix = self.t2_mask_prefix
            self.csvFile = self.t2_csvFile
            self.model_img = self.t2_model_img
            self.model_mask = self.t2_model_mask

            t2_attr= yield self.clone(StructMask)

            return (t1_attr,t2_attr)

        else:
            return (t1_attr)


    def run(self):
        cmd = (' ').join(['fs.py',
                          '-i', self.input()[0]['aligned'],
                          '-m', self.input()[0]['mask'],
                          '-o', self.fs_dir,
                          f'-n {self.freesurfer_nproc}' if self.freesurfer_nproc else '',
                          f'--expert {self.expert_file}' if self.expert_file else '',
                          '--nohires' if self.no_hires else '',
                          '--noskullstrip' if self.no_skullstrip else '',
                          '--t2 {} --t2mask {}'.format(self.input()[1]['aligned'],self.input()[1]['mask'])
                                                if self.t2_template else ''])

        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.fs_dir


if __name__ == '__main__':

    bids_data_dir = '/home/tb571/Downloads/INTRuST_BIDS/'
    bids_derivatives = pjoin(abspath(bids_data_dir), 'derivatives', 'luigi-pnlpipe')

    # cases= ['003GNX007']
    cases= ['003GNX012','003GNX021']
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
    mabs_mask_nproc= int(N_PROC)
    fusion= '' # 'avg', 'wavg', or 'antsJointFusion'
    debug = False
    t1_csvFile= ''#'/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT1AHCC-8141805/trainingDataT1Masks-hdr.csv'
    t2_csvFile= ''#'/home/tb571/Downloads/pnlpipe/soft_light/trainingDataT2Masks-12a14d9/trainingDataT2Masks-hdr.csv'

    # makeRigidMask.py
    t1_model_img= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T1w.nii.gz'
    t1_model_mask= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T1wXcMabs_mask.nii.gz'
    t2_model_img= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-Xc_T2w.nii.gz'
    t2_model_mask= '/home/tb571/Downloads/INTRuST_BIDS/derivatives/luigi-pnlpipe/sub-003GNX007/anat/sub-003GNX007_desc-T2wXcMabs_mask.nii.gz'

    # fs.py
    freesurfer_nproc= 1
    expert_file= ''
    no_hires= False
    no_skullstrip= True
    mode= 'witht2'

    # for qc'ing the created mask
    slicer_exec= ''#'/home/tb571/Downloads/Slicer-4.10.2-linux-amd64/Slicer'


    inter= define_outputs_wf(cases[0], bids_derivatives)


    # individual task
    build([StructMask(bids_data_dir=bids_data_dir,
                      id=cases[0],
                      struct_template=t1_template,
                      struct_align_prefix=inter['t1_align_prefix'],
                      mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                      debug=debug,
                      csvFile=t1_csvFile,
                      fusion=fusion,
                      mabs_mask_nproc=mabs_mask_nproc,
                      struct_img=t1_model_img,
                      struct_label=t1_model_mask,
                      slicer_exec=slicer_exec)])



    # individual task with both t1 and t2
    build([Freesurfer(bids_data_dir=bids_data_dir,
                      id=cases[0],
                      t1_template=t1_template,
                      t2_template=t2_template,
                      t1_align_prefix=inter['t1_align_prefix'],
                      t1_mask_prefix=inter['t1_mabsmask_prefix'],
                      t2_align_prefix=inter['t2_align_prefix'],
                      t2_mask_prefix=inter['t2_mabsmask_prefix'],
                      t1_csvFile=t1_csvFile,
                      t2_csvFile=t2_csvFile,
                      t1_model_img=t1_model_img,
                      t1_model_mask=t1_model_mask,
                      t2_model_img=t2_model_img,
                      t2_model_mask=t2_model_mask,
                      debug=debug,
                      fusion=fusion,
                      mabs_mask_nproc=mabs_mask_nproc,
                      slicer_exec=slicer_exec,
                      freesurfer_nproc=freesurfer_nproc,
                      expert_file=expert_file,
                      no_hires=no_hires,
                      no_skullstrip=no_skullstrip,
                      fs_dir=inter['fs_dir'])])
    


    # individual task with t1
    build([Freesurfer(bids_data_dir=bids_data_dir,
                      id=cases[0],
                      t1_template=t1_template,
                      t1_align_prefix=inter['t1_align_prefix'],
                      t1_mask_prefix=inter['t1_mabsmask_prefix'],
                      t1_csvFile=t1_csvFile,
                      t1_model_img=t1_model_img,
                      t1_model_mask=t1_model_mask,
                      debug=debug,
                      fusion=fusion,
                      mabs_mask_nproc=mabs_mask_nproc,
                      slicer_exec=slicer_exec,
                      freesurfer_nproc=freesurfer_nproc,
                      expert_file=expert_file,
                      no_hires=no_hires,
                      no_skullstrip=no_skullstrip,
                      fs_dir=inter['fs_dir'])])

