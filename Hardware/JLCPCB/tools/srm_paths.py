"""
Resolve the SRM-controller design files.

This package lives inside the repo at Hardware/JLCPCB/, so the repo root is
derived from this file's own location. Override with $SRM_REPO if you move the
tools elsewhere.

The design data ships as zips. Rather than unpacking them into the working
tree, extract to a cache dir on demand: the tools then always read exactly what
the zip contains, a changed zip invalidates the cache automatically, and the
repo stays clean.
"""
import os, zipfile, hashlib, tempfile

# .../<repo>/Hardware/JLCPCB/tools/srm_paths.py  ->  <repo>
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_REPO = os.path.abspath(os.path.join(_HERE, os.pardir, os.pardir, os.pardir))

REPO = os.environ.get('SRM_REPO', _DEFAULT_REPO)
HW = os.path.join(REPO, 'Hardware')

def _extract(zip_name):
    """Unpack Hardware/<zip_name> into a cache dir keyed by the zip's hash."""
    src = os.path.join(HW, zip_name)
    if not os.path.isfile(src):
        raise FileNotFoundError(
            f"{src} not found. Set $SRM_REPO to your SRM-controller checkout "
            f"(currently {REPO!r}).")
    with open(src, 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()[:16]
    dest = os.path.join(tempfile.gettempdir(), f'srm-{zip_name}-{digest}')
    marker = os.path.join(dest, '.complete')
    if not os.path.exists(marker):
        os.makedirs(dest, exist_ok=True)
        with zipfile.ZipFile(src) as z:
            z.extractall(dest)
        open(marker, 'w').close()
    return dest

def _find(root, name):
    for dirpath, _, files in os.walk(root):
        if name in files:
            return os.path.join(dirpath, name)
    raise FileNotFoundError(f"{name} not found under {root}")

def kicad_pcb():
    return _find(_extract('SRM_KiCad_Designfiles.zip'), 'SRM_Converted.kicad_pcb')

def kicad_sch():
    return _find(_extract('SRM_KiCad_Designfiles.zip'),
                 'SRM_motor_controller_VX2.6.Sheet 1.kicad_sch')

def gerber_dir():
    return _extract('SRM_gerber.zip')

def gerber(name):
    return _find(gerber_dir(), name)

if __name__ == '__main__':
    print("repo      :", REPO)
    print("kicad_pcb :", kicad_pcb())
    print("kicad_sch :", kicad_sch())
    print("gerber dir:", gerber_dir())
