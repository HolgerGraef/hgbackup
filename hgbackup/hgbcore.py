import os
import glob
import subprocess
import json
import uuid
import time
from datetime import datetime

config_file = os.path.join(os.environ['HOME'], 'hgbackup.json')

class HGBCore:
    i = 0
    percentage = 0
    length = 0
    thread = None
    config = {'targets': {}}

    def __init__(self):
        try:
            self.config = self.load_config()
        except Exception as e:
            print("Could not load config: "+str(e))

    def new_progress(self, label, length):
        self.i = 0
        self.percentage = 0
        self.length = length
        if self.thread is None:
            print(label+"..."+("done" if not self.length else ""))
        else:
            self.thread.new_progress.emit(label, length)
    
    def inc_progress(self):
        self.i += 1
        if self.thread is None:
            print("\r{}/{}".format(self.i, self.length), end='')
        else:
            if self.i/self.length*100 >= self.percentage+1:
                self.percentage += 1
                self.thread.set_progress.emit(self.percentage)

    def done_progress(self):
        if self.thread is None and self.length:
            if self.i:
                print('\r...done        ')
            else:
                print('...done')
        elif self.thread is not None:
            self.thread.done_progress.emit()

    def load_config(self):
        if not os.path.exists(config_file):
            self.save_config()
        with open(config_file, 'r') as json_file:           # raises exception if file not found
            data = json.load(json_file)                         # raises exception if JSON file corrupt
            if ('targets' not in data) or (not isinstance(data['targets'], dict)):
                raise Exception("Could not find any targets")
            # check targets
            for name, target in data['targets'].items():
                # check if it's a dict
                if not isinstance(target, dict):
                    raise Exception("Target {} not defined as a dictionary".format(name))
                # check for compulsory keys
                keys = ['src', 'dst', 'id']
                for key in keys:
                    if not key in target:
                        raise Exception("Key {} missing in target {}".format(key, name))
                # check if src is a directory
                if not os.path.isdir(target['src']):
                    raise Exception("Path does not exist or is not a directory: {}".format(target['src']))#
                target['dst_connected'] = False
                self.update_target_connection(target)
        return data

    def save_config(self):
        data = {'targets': {}}          # make a dictionary to store config
        keys = ['src', 'dst', 'id', 'last_backup', 'last_check', 'per_backup', 'per_check', 'exclude', 'optional']       # keys to be stored
        for name, target in self.config['targets'].items():
            data['targets'][name] = {}
            for key in keys:
                data['targets'][name][key] = target[key]
        with open(config_file, 'w') as json_file:
            json.dump(data, json_file, indent=4)

    def remove_target(self, targetname):
        if targetname not in self.config['targets']:
            raise Exception("Target {} is not defined.".format(targetname))
        del self.config['targets'][targetname]
        self.save_config()

    def add_target(self, targetname, src, dst):
        # remove trailing / from src and dst
        # TODO: careful if someone wants to back up root (/)
        src = src.rstrip('/')
        dst = dst.rstrip('/')

        if targetname in self.config['targets']:
            raise Exception("Target {} already defined.".format(targetname))

        # check if src exists and if it's a directory
        if not os.path.isdir(src):
            raise Exception("Not a directory: {}".format(src))
        
        # check if there are src folders with identical name that back up to the same dst
        for name, target in self.config['targets'].items():
            if target['dst'] == dst and os.path.basename(target['src']) == os.path.basename(src) and not target['src'] == src:
                raise Exception("Conflicting dst with target {}.".format(name))

        # check if dst is connected
        if not os.path.isdir(dst):
            raise Exception("Please make sure the destination is a folder: {}".format(dst))

        # check dst for ID file
        dst_conf_dir = os.path.join(dst, '.hgbackup')
        idfile = os.path.join(dst_conf_dir, 'id')
        verfile = os.path.join(dst_conf_dir, os.path.basename(src)+'.ver')
        if os.path.isdir(dst_conf_dir):
            if not os.path.isfile(idfile):
                raise Exception("Backup destination corrupt: {}".format(dst))
            with open(idfile) as f:
                id = f.read().strip()
            if os.path.isfile(verfile):
                print("A verification file already exists for the folder {}."
                      "You might want to check it.".format(os.path.basename(src)))
            else:
                with open(verfile, 'w') as f:
                    pass
        else:
            os.mkdir(dst_conf_dir)
            # create ID and verification files
            id = str(uuid.uuid4())
            with open(idfile, 'w') as f:
                f.write(id)
            with open(verfile, 'w') as f:
                pass
        if os.path.basename(src) in [os.path.basename(x) for x in glob.glob(os.path.join(dst, '*'))]:
            print("The destination already contains a folder named {}. If it's not a backup, you "
                  "might want to move it. It it's a backup, you might want to check the verification "
                  "file.".format(os.path.basename(src)))

        self.config['targets'][targetname] = {
            'src': src,
            'dst': dst,
            'id': id,
            'last_backup': None,
            'last_check': None,
            'per_backup': None,
            'per_check': None,
            'exclude': [],
            'optional': []
        }
        self.save_config()

    def update_target_connection(self, target):
        dst_connected = True

        dst_conf_dir = os.path.join(target['dst'], '.hgbackup')
        if os.path.isdir(dst_conf_dir):
            # check if target has the correct ID
            idfile = os.path.join(dst_conf_dir, 'id')
            if not os.path.isfile(idfile):
                dst_connected = False
            else:
                with open(idfile) as f:
                    id = f.read().strip()
                    if not id == target['id']:
                        dst_connected = False
        else:
            dst_connected = False
        # check target for verification file
        verfile = os.path.join(dst_conf_dir, os.path.basename(target['src'])+'.ver')
        if not os.path.isfile(verfile):
            dst_connected = False

        if dst_connected and target['dst_connected']:           # do nothing, target stays connecteed
            return True, False
        elif dst_connected and not target['dst_connected']:     # target just got connected
            target['dst_connected'] = dst_connected
            target['verfile'] = verfile
            target['verdict'] = None
            return True, True
        elif not dst_connected and target['dst_connected']:     # target just got disconnected
            target['dst_connected'] = dst_connected
            target['verfile'] = None
            target['verdict'] = None
            return False, True
        else:                                                   # do nothing, target stays disconnected
            return False, False

    def load_verdict(self, target):
        # check if target is connected (this implies that the verification file exists)
        if not target['dst_connected']:
            raise Exception("Target is not connected: {}".format(target['dst']))
        verdict = {}
        with open(target['verfile']) as f:
            for line in f:
                md5, path = line.rstrip().split(' ', 1)
                verdict[path] = md5
        return verdict

    def save_verdict(self, target):
        # check if target is connected (this implies that the verification file exists)
        if not target['dst_connected']:
            raise Exception("Target is not connected: {}".format(target['dst']))
        if target['verdict'] is None or target['verfile'] is None:
            raise Exception("Verification dictionary not loaded")
        print("Saving verification file...")
        with open(target['verfile'], 'w') as f:
            for key in target['verdict']:
                f.write('{} {}\n'.format(target['verdict'][key], key))

    def prepare_target(self, target):
        if target['verdict'] is None:
            target['verdict'] = self.load_verdict(target)

        return target['src'], target['dst'], target['verdict']

    def check_verdict(self, target, repair=False):
        t0 = time.time()
        src, dst, verdict = self.prepare_target(target)

        remove_list = []
        self.new_progress("Scanning for missing files", len(verdict))
        for key in verdict:
            self.inc_progress()
            # check if file exists
            if not os.path.exists(os.path.join(dst, key)):
                print("\r  File not found: {}".format(key))
                if repair:
                    remove_list.append(key)
        self.done_progress()

        if repair:
            self.new_progress("Removing missing files", len(remove_list))
            for key in remove_list:
                self.inc_progress()
                verdict.pop(key, None)
            self.done_progress()
        
        self.new_progress("Scanning dst directory", 1)
        files = []
        for dirpath, dirnames, filenames in os.walk(os.path.join(dst, os.path.basename(src))):       # does not follow links
            for f in filenames:
                f = os.path.join(dirpath, f)
                if not os.path.islink(f):
                    files.append(f)
        self.done_progress()

        self.new_progress("Scanning for missing checksums", len(files))
        for f in files:
            self.inc_progress()
            # check if MD5 sum exists
            relf = os.path.relpath(f, dst)
            if relf not in verdict:
                print("\r  MD5 sum not found: {}".format(relf))
                if repair:
                    # read MD5 sum from source file
                    src_file = os.path.join(os.path.dirname(src), relf)
                    if os.path.isfile(src_file):
                        proc = subprocess.Popen(['md5sum', src_file], stdout=subprocess.PIPE)
                        line = proc.stdout.readline()
                        verdict[relf] = line.rstrip().decode('utf-8').split(' ', 1)[0]
                    else:
                        print("  WARNING: {} not found in source directory".format(relf))
        self.done_progress()

        if repair:
            self.save_verdict(target)

        print("\n-- The operation took {:.1f} seconds.".format(time.time()-t0))

    def verify_backup(self, target):
        # NB: could also do this with: md5sum --check example.ver
        #     but we want status updates
        t0 = time.time()
        src, dst, verdict = self.prepare_target(target)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        logdir = os.path.join(dst, '.hgbackup', 'verification_log')
        if not os.path.exists(logdir):
            os.mkdir(logdir)
        logfile = os.path.join(logdir, os.path.basename(src)+'_'+timestamp+'.log')
        with open(logfile, "w") as log:
            self.new_progress("Verifying backup {}".format(timestamp), len(verdict))
            for key in verdict:
                self.inc_progress()
                if verdict[key] == 'HL':
                    continue
                proc = subprocess.Popen(['md5sum', os.path.join(dst, key)], stdout=subprocess.PIPE)
                md5 = proc.stdout.readline().rstrip().decode('utf-8').split(' ', 1)[0]
                if not md5 == verdict[key]:
                    print("\rInvalid checksum: {}".format(key))
                    log.write("Invalid checksum: {}, expected: {}, got: {}\n".format(key, verdict[key], md5))
            log.write("Verification took {:.1f} seconds.\n".format(time.time()-t0))
            self.done_progress()

        target['last_check'] = timestamp
        self.save_config()

        if self.thread:
            self.thread.done_verify.emit()

    def run_backup(self, target, dry=False, full=False):
        src, dst, verdict = self.prepare_target(target)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

        self.new_progress("Running backup {}".format(timestamp), 1)
        rsync = ['rsync']
        if dry:
            rsync.append('-n')

        # c.f. https://linux.die.net/man/1/rsync
        # -a: archive mode; equals -rlptgoD (no -H,-A,-X)
        #   -r = --recursive
        #   -l = --links
        #   -p = --perms
        #   -t = --times
        #   -g = --group
        #   -o = --owner
        #   -D = --devices --specials
        # -v = --verbose
        # -h = --humand-readable
        # --delete = delete extraneous files from dest dirs

        # main options
        rsync.extend(['-avh', '--delete', '--hard-links'])
        # log options
        if dry:
            logdir = os.path.join(dst, '.hgbackup', 'rsync_dry_log')
        else:
            logdir = os.path.join(dst, '.hgbackup', 'rsync_log')
        logfile = os.path.join(logdir, os.path.basename(src)+'_'+timestamp+'.log')
        if not os.path.exists(logdir):
            os.mkdir(logdir)
        rsync.extend(['--progress', '--itemize-changes', '--stats', '--log-file={}'.format(logfile)])
        if not dry:
            rsync.extend(['--out-format=%i md5:%C %n%L'])
        # backup options
        backupsuffix = ".backup_"+timestamp
        backupdir = os.path.join(dst, '.hgbackup', 'rsync_backup')
        if not os.path.exists(backupdir):
            os.mkdir(backupdir)
        rsync.extend(['--backup', '--suffix='+backupsuffix, '--backup-dir='+backupdir])
        # exclude options
        excludefile = os.path.join(logdir, os.path.basename(src)+'_'+timestamp+'.exc')
        with open(excludefile, 'w') as f:
            for x in target['exclude']:
                f.write(x+'\n')
            if not full:
                for x in target['optional']:
                    f.write(x+'\n')
        rsync.extend(['--exclude-from='+excludefile])
            
        # src and dst
        rsync.extend([src, dst])
        
        proc = subprocess.Popen(rsync, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip().decode('utf-8')
            print(line)
            if not dry:
                # detect deleted files
                if line.startswith('*deleting'):
                    i = line.find('md5:')
                    f = line[i+4+32+1:]
                    verdict.pop(f, None)
                # detect hard links
                elif line.startswith('hf'):
                    i = line.find('md5:')
                    f = line[i+4+32+1:]
                    j = f.find(' => ')
                    f = f[:j]
                    verdict[f] = 'HL'
                # detect received files
                elif line.startswith('>f'):
                    info = line[2:2+9]                    
                    i = line.find('md5:')
                    md5 = line[i+4:i+4+32]  # extract MD5 sum
                    f = line[i+4+32+1:]     # extract file name
                    if 's' in info or 't' in info or 'c' in info:
                        # MD5 sum needs to be updated
                        verdict[f] = md5
                    else:
                        # MD5 sum needs to be added
                        verdict[f] = md5

        if not dry:
            target['last_backup'] = timestamp
        self.save_config()
        self.save_verdict(target)

        self.done_progress()

        # obtain size of rsync backup folder
        # NB: Previously we did this with 'du -h -s $backupdir | cut -f 1'
        # The following method seems to yield a result compatible with Nautilus folder size.
        # c.f. https://askubuntu.com/a/729725
        self.new_progress("Obtaining size of rsync backup folder", 1)        
        cmd = "find "+backupdir+" -ls | awk \'{sum += $7} END {print sum}\'"
        proc = subprocess.Popen(['bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            line = proc.stdout.readline().rstrip()
            if not line:
                break
            # if awk returns scientific notation (for large ints, c.f. awk -W version), we want to be sure to parse it correctly
            line = line.decode("utf-8").replace(',', '.')
            size = int(float(line))
        print("rsync backup size: {:.1f} GB".format(size/1000./1000./1000.))
        self.done_progress()

        if self.thread:
            self.thread.done_backup.emit()
