import xija
n_fail = xija.test('-v', '-k test_data_types')
if n_fail > 0:
    raise ValueError(str(n_fail) + ' test failures')
