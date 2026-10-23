# Purpose: Install or restore the reviewed conservative 1D-HD refinement patch in a separate AMRVAC 3.2 source tree.
import argparse
import base64
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--amrvac-dir', type=Path, required=True)
    parser.add_argument('--patch-dir', type=Path,
                        default=Path(__file__).resolve().parent/'positive_amr_phase_dt_build')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    root = args.amrvac_dir.resolve(strict=True)
    backup = root/'positive_amr_backup.json'
    if args.restore:
        saved = json.loads(backup.read_text())
        targets = [(root/row['path'], base64.b64decode(row['original_base64'])) for row in saved['files']]
        for path, _ in targets:
            path.resolve().relative_to(root)
        for path, data in targets:
            path.write_bytes(data)
            print('RESTORED', path)
        return
    info = json.loads((args.patch_dir/'build.json').read_text())
    patch = (args.patch_dir/'patched_mod_refine.t').read_bytes().replace(b'\r\n', b'\n')
    if digest(patch) != info['patched_source_sha256']:
        raise RuntimeError('Patch file does not match the recorded build hash')
    source = root/'src/amr/mod_refine.t'
    targets = [source.resolve(strict=True)]
    # Standard v3.2 uses template symlinks; also handle a dereferenced library copy.
    for template in (root/'lib').glob('1d1_*/mod_refine.t'):
        resolved = template.resolve(strict=True)
        if resolved not in targets:
            targets.append(resolved)
    originals = []
    for target in targets:
        relative = target.relative_to(root)
        data = target.read_bytes()
        if digest(data) == info['patched_source_sha256']:
            continue
        if digest(data) != info['original_source_sha256']:
            raise RuntimeError('Unrecognized source; refusing to overwrite local changes: '+str(target))
        originals.append({'path': str(relative), 'original_base64': base64.b64encode(data).decode()})
    if not originals:
        print('The reviewed patch is already installed.')
        return
    if backup.exists():
        raise RuntimeError('A backup already exists; inspect it before reinstalling: '+str(backup))
    backup.write_text(json.dumps({'purpose': 'Exact original files for restoring the 1D HD AMR refinement patch.',
                                 'files': originals}, indent=2)+'\n')
    for row in originals:
        target = root/row['path']
        target.write_bytes(patch)
        print('PATCHED', target)
    print('Rebuild the supplied 1D HD problem before running. No executable was changed by this installer.')


if __name__ == '__main__':
    main()
