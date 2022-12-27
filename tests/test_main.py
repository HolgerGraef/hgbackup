import os
import pytest

from hgbackup.hgbcore import HGBCore

CFG = "/tmp/.hgbackup.json"
SRC = "/tmp/hgb_test"
DST = "/tmp/hgb_test_backup"


def create_random_file(filepath, filesize=1024):
    with open(filepath, "wb") as f:
        f.write(os.urandom(filesize))


@pytest.mark.parametrize("reload", [True, False])
def test_backup(reload: bool):
    # make sure we start with a clean environment
    if os.path.exists(SRC):
        assert os.system(f"rm -rf {SRC}") == 0
    if os.path.exists(DST):
        assert os.system(f"rm -rf {DST}") == 0
    if os.path.exists(CFG):
        os.remove(CFG)

    # set up a backup source and destination
    os.makedirs(SRC)
    os.makedirs(DST)

    # add some files to the source
    create_random_file(f"{SRC}/file1")
    create_random_file(f"{SRC}/file2")
    create_random_file(f"{SRC}/file3")

    hgbcore = HGBCore(CFG)
    hgbcore.add_target("test", SRC, DST)

    if reload:
        hgbcore = HGBCore(CFG)

    # run backup and verification
    hgbcore.run_backup(hgbcore.config["targets"]["test"])
    assert hgbcore.verify_backup(hgbcore.config["targets"]["test"]) == True
