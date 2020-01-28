#!/usr/bin/env python

from luigi import Task, build, Parameter, BoolParameter
from luigi.util import inherits, requires

from dwi_pipe import BetMask, PnlEddyUkf
from struct_pipe_t1_t2 import FreesurferT1

from subprocess import Popen
from plumbum import local

from _define_outputs import create_dirs

from util import N_PROC, B0_THRESHOLD, BET_THRESHOLD

from _define_outputs import define_outputs_wf

@inherits(FreesurferT1,BetMask)
class FsT1Dwi(Task):

    fs2dwi_dir= Parameter()
    outDir= Parameter() # freesurfer directory
    debug= BoolParameter(default=False)

    def requires(self):
        return dict(fs= self.clone(FreesurferT1), bet= self.clone(BetMask))

    def run(self):
        cmd = (' ').join(['fs2dwi.py',
                          '-f', self.outDir,
                          '--bse', self.input()['bet']['bse'],
                          '--dwimask', self.input()['bet']['mask'],
                          '-o', self.fs2dwi_dir,
                          '-d' if self.debug else '',
                          'direct'])
        p = Popen(cmd, shell=True)
        p.wait()

    def output(self):
        return self.fs2dwi_dir / 'wmparc.nii.gz'


if __name__=='__main__':

    bids_data_dir = local.path('/home/tb571/Downloads/INTRuST_BIDS/')
    bids_derivatives = bids_data_dir / 'derivatives' / 'luigi-pnlpipe'

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
    dwi_template = 'sub-id/dwi/*_dwi.nii.gz'

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

    # bse.py
    which_bse = ''  # '', '--min', '--avg', or '--all'
    b0_threshold = B0_THRESHOLD

    # bet_mask.py
    bet_threshold = BET_THRESHOLD

    # pnl_eddy.py
    eddy_nproc = N_PROC

    # pnl_epi.py
    epi_nproc = N_PROC

    # fsl_eddy.py
    acqp_file = '/home/tb571/Downloads/INTRuST_BIDS/derivatives/acqp.txt'
    index_file = '/home/tb571/Downloads/INTRuST_BIDS/derivatives/index.txt'
    eddy_config = '/home/tb571/luigi-pnlpipe/scripts/eddy_config.txt'

    # ukf.py
    ukf_params = '--seedingThreshold,0.4,--seedsPerVoxel,1'

    '''
    t1_align_prefix= bids_derivatives / 'sub-id' / 'anat' / 'sub-id_desc-Xc_T1w'
    dwi_align_prefix= bids_derivatives / 'sub-id' / 'dwi' / 'sub-id_desc-Xc_dwi'

    t1_mabsmask_prefix= bids_derivatives / 'sub-id' / 'anat' / 'sub-id_desc-T1wXcMabs'

    fs_dir= bids_derivatives / 'sub-id' / 'anat' / 'freesurfer'

    eddy_bse_betmask_prefix= bids_derivatives / 'sub-id' / 'dwi' / 'sub-id_desc-XcBseBet'
    eddy_bse_prefix= bids_derivatives / 'sub-id' / 'dwi' / 'sub-id_desc-dwiXcEd_bse'
    eddy_prefix= bids_derivatives / 'sub-id' / 'dwi' / 'sub-id_desc-XcEd_dwi'

    eddy_fs2dwi_dir= bids_derivatives / 'sub-id' / 'fs2dwi' / 'eddy_fs2dwi'
    fs_in_eddy= bids_derivatives / 'sub-id' / 'fs2dwi' / 'eddy_fs2dwi' / 'wmparcInDwi.nii.gz'

    eddy_tract_prefix= bids_derivatives / 'sub-id' / 'tracts' / 'sub-id_desc-XcEd'

    # group task through iterable
    build([FsT1Dwi(id=id,
                   bids_data_dir = bids_data_dir,
                   dwi_template = dwi_template,
                   dwi_align_prefix= dwi_align_prefix.replace('id',id),
                   eddy_prefix= eddy_prefix.replace('id',id),
                   bse_prefix= eddy_bse_prefix.replace('id',id),
                   bse_betmask_prefix= eddy_bse_betmask_prefix.replace('id',id),
                   which_bse= which_bse,
                   b0_threshold= b0_threshold,
                   bet_threshold= bet_threshold,
                   slicer_exec= slicer_exec,
                   debug= debug,
                   eddy_nproc= eddy_nproc,
                   struct_template= t1_template,
                   struct_align_prefix= t1_align_prefix.replace('id',id),
                   mabs_mask_prefix= t1_mabsmask_prefix.replace('id',id),
                   csvFile=t1CsvFile,
                   fusion=fusion,
                   mabs_mask_nproc=mabs_mask_nproc,
                   struct_img=t1SiteImg,
                   struct_label=t1SiteMask,
                   freesurfer_nproc=freesurfer_nproc,
                   expert_file=expert_file,
                   no_hires=no_hires,
                   no_skullstrip=no_skullstrip,
                   outDir=eddy_fs2dwi_dir.replace('id',id),
                   ukf_params=ukf_params,
                   tract_prefix= eddy_tract_prefix.replace('id',id)) for id in cases], workers=3)
    
    
    build([FsT1Dwi(id=id,
                   bids_data_dir = bids_data_dir,
                   dwi_template = dwi_template,
                   dwi_align_prefix= dwi_align_prefix.replace('id',id),
                   bse_prefix= eddy_bse_prefix.replace('id',id),
                   bse_betmask_prefix= eddy_bse_betmask_prefix.replace('id',id),
                   which_bse= which_bse,
                   b0_threshold= b0_threshold,
                   bet_threshold= bet_threshold,
                   slicer_exec= slicer_exec,
                   debug= debug,
                   struct_template= t1_template,
                   struct_align_prefix= t1_align_prefix.replace('id',id),
                   mabs_mask_prefix= t1_mabsmask_prefix.replace('id',id),
                   csvFile=t1CsvFile,
                   fusion=fusion,
                   mabs_mask_nproc=mabs_mask_nproc,
                   struct_img=t1SiteImg,
                   struct_label=t1SiteMask,
                   freesurfer_nproc=freesurfer_nproc,
                   expert_file=expert_file,
                   no_hires=no_hires,
                   no_skullstrip=no_skullstrip,
                   outDir=eddy_fs2dwi_dir.replace('id',id)) for id in cases], workers=3)
    '''

    tasks= []
    for id in cases:

        inter= define_outputs_wf(id, bids_derivatives)

        tasks.append(FsT1Dwi(id=id,
                             bids_data_dir=bids_data_dir,
                             dwi_template=dwi_template,
                             dwi_align_prefix=inter['dwi_align_prefix'],
                             bse_prefix=inter['eddy_bse_prefix'],
                             bse_betmask_prefix=inter['eddy_bse_betmask_prefix'],
                             which_bse=which_bse,
                             b0_threshold=b0_threshold,
                             bet_threshold=bet_threshold,
                             slicer_exec=slicer_exec,
                             debug=debug,
                             struct_template=t1_template,
                             struct_align_prefix=inter['t1_align_prefix'],
                             mabs_mask_prefix=inter['t1_mabsmask_prefix'],
                             csvFile=t1CsvFile,
                             fusion=fusion,
                             mabs_mask_nproc=mabs_mask_nproc,
                             struct_img=t1SiteImg,
                             struct_label=t1SiteMask,
                             freesurfer_nproc=freesurfer_nproc,
                             expert_file=expert_file,
                             no_hires=no_hires,
                             no_skullstrip=no_skullstrip,
                             fs2dwi_dir= inter['eddy_fs2dwi_dir'],
                             outDir=inter['fs_dir']))

    build(tasks, workers= 4)

