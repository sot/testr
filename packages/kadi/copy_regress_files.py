import glob

from ska_test.runner import make_regress_files

regress_files = glob.glob('events_cmds/*')
make_regress_files(regress_files)
