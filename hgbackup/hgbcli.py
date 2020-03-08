class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class HGBCLI:
    def __init__(self, hgbcore):
        self.hgbcore = hgbcore

    def list_targets(self):
        print("List of targets:")
        for name, target in self.hgbcore.config['targets'].items():
            print("{}{:<10}{}{:<40}{:<40}{:<8}".format(bcolors.BOLD, name, bcolors.ENDC, target['src'], target['dst'],
                                            bcolors.OKGREEN+"[ready]"+bcolors.ENDC if target['dst_connected'] 
                                            else bcolors.FAIL+"[N/A]"+bcolors.ENDC))

    def check_target(self, targetname):
        if targetname not in self.hgbcore.config['targets']:
            print("Target {} is not defined.".format(targetname))
        elif not self.hgbcore.config['targets'][targetname]['dst_connected']:
            print("Target {} is not connected.".format(targetname))
        else:
            return self.hgbcore.config['targets'][targetname]
        return None

    def parse_command_line(self, argv):
        if len(argv) == 2 and argv[1] == "list":
            self.list_targets()
        elif len(argv) == 3 and argv[1] == "remove":
            self.hgbcore.remove_target(argv[2])
        elif len(argv) == 3:
            target = self.check_target(argv[2])
            if target is None:
                return
            if argv[1] == "check":
                self.hgbcore.check_verdict(target)
            elif argv[1] == "repair":
                self.hgbcore.check_verdict(target, repair=True)
            elif argv[1] == "verify":
                self.hgbcore.verify_backup(target)
            elif argv[1] == "run":
                self.hgbcore.run_backup(target)
            elif argv[1] == "run-full":
                self.hgbcore.run_backup(target, full=True)
            elif argv[1] == "dryrun":
                self.hgbcore.run_backup(target, dry=True)
            elif argv[1] == "dryrun-full":
                self.hgbcore.run_backup(target, dry=True, full=True)
        elif len(argv) == 5 and argv[1] == "add":
            if argv[2] in self.hgbcore.config['targets']:
                print("Target {} is already defined.".format(argv[2]))
            else:
                self.hgbcore.add_target(argv[2], argv[3], argv[4])
        else:
            print("Invalid command line.")