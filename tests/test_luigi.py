import numpy as np
from os.path import isfile
import pytest
from conversion import read_bvals, read_bvecs

REL_DIFF_THRESH = 10

def test_header(params):

    np.testing.assert_almost_equal(params['gt_img'].affine, params['out_img'].affine)


def test_data(params):

    gt_data= params['gt_img'].get_fdata()
    out_data= params['out_img'].get_fdata()

    # relative percentage difference
    rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
    np.testing.assert_array_less(rel_diff, REL_DIFF_THRESH)



def test_vectors(params):

    bval_file= params['out_prefix']+ '.bval'
    bvec_file= params['out_prefix']+ '.bvec'

    if isfile(bval_file):
        # bvals
        out_data = np.array(read_bvals(bval_file))
        gt_data= np.array(read_bvals(params['gt_prefix']+ '.bval'))

        # relative percentage difference
        rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
        np.testing.assert_array_less(rel_diff, REL_DIFF_THRESH)


        # bvecs
        out_data = np.array(read_bvecs(bvec_file))
        gt_data= np.array(read_bvecs(params['gt_prefix']+ '.bvec'))

        # relative percentage difference
        rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
        np.testing.assert_array_less(rel_diff, REL_DIFF_THRESH)

    else:
        pytest.skip()


