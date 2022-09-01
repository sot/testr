"""
Generate complete list of subnets in HEAD network

This assumes running the following on a HEAD machine::

  nodeinfo 131.142 > nodes.dat

The notebook then selects all `Linux` or `Linux*` machines and outputs the
subnet values as a list of str to be pasted into
`testr.test_helper.on_head_network()`.
"""

from pathlib import Path

import numpy as np
from astropy.table import Table

lines = Path("nodes.dat").read_text().splitlines()

rows = []
for line in lines:
    vals = line.split()
    if vals[1].startswith("131.142"):
        row = {
            "name": vals[0],
            "ip": vals[1],
            "arch": vals[2],
            "os": vals[3],
            "room": vals[4],
            "rest": " ".join(vals[5:]),
        }
        rows.append(row)
dat = Table(rows)

ok = np.isin(dat["os"], ["Linux", "Linux*"])
dok = dat[ok]

print(set(dat["os"]))

dok.sort("ip")

# dok.pprint_all()

ip3s = set()
for ip in set(dok["ip"]):
    ip4s = ip.split(".")
    ip3s.add(ip4s[2])
ip3s = sorted(int(ip3) for ip3 in ip3s)


# Confirm known SOT MP machines
dok.add_index("name")
mps = """
statler
rife
cooper
treble
baffin
baires
tortuga
heimdall
""".split()

for mp in mps:
    print(mp, dok.loc[mp]["ip"])

# Print our final subnets
print("HEAD subnets:")
print(", ".join(repr(str(ip3)) for ip3 in ip3s))
