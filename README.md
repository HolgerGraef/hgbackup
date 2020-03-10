### Installing

    /usr/bin/python3 setup.py install --user
    cp hgbackup.desktop ~/.config/autostart/

or, for development:

    /usr/bin/python3 setup.py develop --user

### Updating icon cache

In case you need to modify the icons in `hgbackup/pie/`, you should update the GTK icon
cache subsequently:

    sudo gtk-update-icon-cache --ignore-theme-index --force --include-image-data /usr/share/icons/hicolor

### TODO General
- fix display of rsync progress for individual files
- careful when root (/) folder is added as backup source
- estimate remaining time in progress
- enable user to modify backup periodicities, excluded and optional list
- hard links are created in backup destination, but no MD5 sum is recorded,
  which provokes "MD5 sum not found" in check_verdict()
  (they are not detected by os.path.islink()) -> fix this

### TODO GUI
- do not "refocus" on window when launching a new progress if it's hidden
- continuously check for changes in the configuration file and propose a reload
  (never do this while a backup/check/verification process is running)
- implement progress cancel button
  => NB: in particular for the rsync process we need some way to terminate the
  thread instead of checking some "mutex"
- implement adding and modifying targets

### References
- https://www.oreilly.com/library/view/linux-security-cookbook/0596003919/ch01s16.html
- https://techblog.jeppson.org/2014/10/verify-backup-integrity-with-rsync-sed-cat-and-tee/
- https://www.thegeekdiary.com/how-to-verify-the-integrity-of-a-file-with-md5-checksum/
- https://stackoverflow.com/questions/29624524/how-can-i-print-log-the-checksum-calculated-by-rsync
- https://www.devdungeon.com/content/desktop-notifications-linux-python