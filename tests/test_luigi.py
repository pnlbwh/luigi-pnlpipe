import numpy as np

REL_DIFF_THRESH = 10

def test_header(gt_img, out_img):

    np.testing.assert_almost_equal(gt_img.header, out_img.header)


def test_data(gt_img, out_img):

    gt_data= gt_img.get_fdata()
    out_data= out_img.get_fdata()

    # relative percentage difference
    rel_diff = 2 * abs(gt_data - out_data).sum() / (gt_data + out_data).sum() * 100
    print('Relative difference: ', rel_diff)
    np.testing.assert_array_less(rel_diff, REL_DIFF_THRESH)

