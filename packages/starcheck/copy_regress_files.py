from ska_test.runner import make_regress_files

regress_files = ['starcheck.txt',
                 'starcheck/ccd_temperature.png',
                 'starcheck/stars_18125.png',
                 'starcheck/pcad_att_check.txt']

clean = {'starcheck.txt': [(r'\s*Run on.*[\n\r]*', '')]}

make_regress_files(regress_files, clean=clean)
