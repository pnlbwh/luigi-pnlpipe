import numpy as np
from nibabel import load
import json
from conversion import read_bvals, read_bvecs
import pandas as pd

REL_DIFF_MAX = 1
DICE_COEFF_MIN = 0.95

def test_header(params):

    gt_data= load(params['gt_name'])
    out_data= load(params['out_name'])

    np.testing.assert_almost_equal(gt_data.affine, out_data.affine)


def test_data(params):

    gt_data= load(params['gt_name']).get_fdata()
    out_data= load(params['out_name']).get_fdata()

    # relative percentage difference
    rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
    print(f'Difference {rel_diff}%')
    np.testing.assert_array_less(rel_diff, REL_DIFF_MAX)


def test_bvals(params):

    gt_data= np.array(read_bvals(params['gt_name']))
    out_data= np.array(read_bvals(params['out_name']))

    # relative percentage difference
    rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
    np.testing.assert_array_less(rel_diff, REL_DIFF_MAX)


def test_bvecs(params):

    gt_data = np.array(read_bvecs(params['gt_name']))
    out_data = np.array(read_bvecs(params['out_name']))

    # relative percentage difference
    rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
    np.testing.assert_array_less(rel_diff, REL_DIFF_MAX)


def test_json(params):

    with open(params['gt_name']) as f:
        gt_data = json.load(f)

    with open(params['out_name']) as f:
        out_data = json.load(f)

    np.testing.assert_equal(gt_data, out_data)


def test_html(params):

    with open(params['gt_name']) as f:
        gt_data = f.read()

    with open(params['out_name']) as f:
        out_data = f.read()

    np.testing.assert_equal(gt_data, out_data)


def test_wmparc(params):

    gt_data= load(params['gt_name'])
    out_data= load(params['out_name'])

    ref_labels = gt_data.get_fdata()
    out_labels = out_data.get_fdata()

    labels= np.unique(ref_labels)

    dice_coeff = labels.copy()
    for i, l in enumerate(labels):
        temp_ref = (ref_labels == l) * 1
        temp_out = (out_labels == l) * 1

        intersection = (temp_ref * temp_out).sum()
        dice = 2 * intersection / (temp_ref.sum() + temp_out.sum())

        dice_coeff[i]= dice

    np.testing.assert_array_less(DICE_COEFF_MIN, dice_coeff.min())


def test_tracts(params):

    from tract_compare import tract2vol, calc_dice

    gt_bse, gt_tract = params['gt_name'].split(',')
    out_bse, out_tract = params['out_name'].split(',')

    voxel_data_1 = tract2vol(gt_tract, gt_bse)
    voxel_data_2 = tract2vol(out_tract, out_bse)

    d_standard, d_weighted= calc_dice(voxel_data_1, voxel_data_2)
    np.testing.assert_array_less(DICE_COEFF_MIN, d_weighted)



def test_wmql(params):

    gt_data= pd.read_csv(params['gt_name']).values
    out_data= pd.read_csv(params['out_name']).values

    # check if all tracts have been found
    np.testing.assert_equal(gt_data[:,0], out_data[:,0])
    
    # compare attributes of the found tracts
    # relative percentage difference
    rel_diff = 2 * abs(gt_data[:,1:] - out_data[:,1:]).sum() / (gt_data[:,1:] + out_data[:,1:]).sum() * 100
    np.testing.assert_array_less(rel_diff, REL_DIFF_MAX)

