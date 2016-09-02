from ska_test.runner import make_regress_files

regress_files = ['packages']

clean = {'packages': [(r'^#.*[\r\n]*', r''),
                      (r'^(\S+)\s+(\S+).+', r'\1 \2')]}

make_regress_files(regress_files, clean=clean)
