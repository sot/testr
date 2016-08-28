from ska_test.runner import make_regress_files

regress_files = ['test_unit.py.log']
clean = {'test_unit.py.log':
             [(r'.*\d+ passed.*seconds.*', ''),
              (r'^platform.+py.+pytest.+', ''),
              (r'^Bash-\d\d:\d\d:\d\d', 'Bash-HH:MM:SS')]
         }

make_regress_files(regress_files, clean=clean)

