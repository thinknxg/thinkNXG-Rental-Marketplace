import json, sys, importlib
from lib import MANIFEST, ROOT
mods = sys.argv[1:] or ["build_info"]
for m in mods:
    importlib.import_module(m).build()
json.dump(MANIFEST, open(ROOT + "/source-files/manifest.json", "w"), indent=1)
print(len(MANIFEST), "assets")
