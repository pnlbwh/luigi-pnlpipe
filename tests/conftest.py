import pytest
from os.path import abspath, basename, dirname, join as pjoin

REF_DIR = pjoin(abspath(dirname(__file__)), 'Reference')

def pytest_addoption(parser):

    parser.addoption(
        "--filename",
        help="reference filename",
    )

    parser.addoption(
        "--outroot",
        help="root directory containing CTE/ and HCP/ folders",
    )


@pytest.fixture
def params(request):

    filename= abspath(request.config.getoption('filename'))
    outroot = abspath(request.config.getoption('outroot'))

    print('Testing', basename(filename))

    params = {}
    params['gt_name']= filename
    params['out_name']= filename.replace(REF_DIR, outroot)


    return params
