# Installing

    /usr/bin/python3 setup.py install --user
    cp hgbackup.desktop ~/.config/autostart/

or, for development:

    /usr/bin/python3 setup.py develop --user

# TODO General
- fix display of rsync progress for individual files
- careful when root (/) folder is added as backup source
- enable user to modify backup periodicities, excluded and optional list
- hard links are created in backup destination, but no MD5 sum is recorded,
  which provokes "MD5 sum not found" in check_verdict()
  (they are not detected by os.path.islink()) -> fix this

# TODO GUI:
- implement progress cancel button
  => NB: in particular for the rsync process we need some way to terminate the
  thread instead of checking some "mutex"
- after long verdict check process, the console keeps running although according
  to progress bar we are at 100% (maybe because percent counter is increased too early?)
- implement adding and modifying targets


# References
- https://www.oreilly.com/library/view/linux-security-cookbook/0596003919/ch01s16.html
- https://techblog.jeppson.org/2014/10/verify-backup-integrity-with-rsync-sed-cat-and-tee/
- https://www.thegeekdiary.com/how-to-verify-the-integrity-of-a-file-with-md5-checksum/
- https://stackoverflow.com/questions/29624524/how-can-i-print-log-the-checksum-calculated-by-rsync
- https://www.devdungeon.com/content/desktop-notifications-linux-python