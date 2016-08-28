from ska_test.runner import make_regress_files

regress_files = ['out/index.rst',
                 'out/run.dat',
                 'out/states.dat',
                 'out/temperatures.dat']

clean = {'out/index.rst': [(r'^Run time.*', '')],
         'out/run.dat': [(r'#.*py run at.*', '')]}

make_regress_files(regress_files, clean=clean)
