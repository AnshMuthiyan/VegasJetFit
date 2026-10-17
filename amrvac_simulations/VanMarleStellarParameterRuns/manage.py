# Purpose: Prepare, build, smoke-test, and launch four matched evolving-wind runs.
# Run simulation/build actions under Linux or WSL with MPI-AMRVAC installed.
import argparse
import csv
import datetime
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get('AMRVAC_DIR', '/home/anshm/amrvac'))
YEAR_CODE = 3.1536e7 / 3.0857e11
CASES = {'tc_off_rc_off': (False, False), 'tc_on_rc_off': (True, False),
         'tc_off_rc_on': (False, True), 'tc_on_rc_on': (True, True)}
FLAGS = ['-cpp', '-ffree-form', '-fimplicit-none', '-O2', '-g',
         '-fcheck=bounds', '-fbacktrace', '-ffpe-trap=invalid,zero,overflow']


def history():
    rows = []
    for line in (HERE / 'stellar_evolution.dat').read_text().splitlines():
        if not line.strip() or line.lstrip().startswith(('#', '!')):
            continue
        row = tuple(map(float, line.split()))
        if len(row) != 4 or not all(math.isfinite(x) for x in row):
            raise ValueError('Invalid stellar history row')
        age, lograte, speed, temperature = row
        if age < 0 or speed <= 0 or temperature <= 0:
            raise ValueError('Invalid stellar history values')
        if rows and age <= rows[-1][0]:
            raise ValueError('Phase end ages must strictly increase')
        rows.append(row)
    if not rows:
        raise ValueError('Empty stellar history')
    return rows


def prepare(years):
    rows = history()
    if not 0 < years <= rows[-1][0]:
        raise ValueError('Duration must be positive and within the supplied history')
    template = (HERE / 'template.par').read_text()
    for name, (tc, rc) in CASES.items():
        case = HERE / name
        case.mkdir(exist_ok=True)
        if list((case / 'output').glob('test*.dat')):
            raise RuntimeError(f'{name}: existing production output; preserve it before preparing new inputs')
        for filename in ('mod_usr.t', 'stellar_evolution.dat'):
            shutil.copy2(HERE / filename, case / filename)
        par = template.replace('@CASE@', name).replace('@TC@', str(tc).lower())
        par = par.replace('@RC@', str(rc).lower())
        par = par.replace('@TIME_MAX@', f'{years * YEAR_CODE:.17e}')
        par = par.replace('@SAVE_DT@', f'{min(years / 10, 100000) * YEAR_CODE:.17e}')
        (case / 'run.par').write_text(par)
        (case / 'output').mkdir(exist_ok=True)
    validate()
    print(f'Prepared four matched runs to {years:g} years.', flush=True)


def validate():
    normalized = []
    source_hash = hashlib.sha256((HERE / 'mod_usr.t').read_bytes()).hexdigest()
    history_hash = hashlib.sha256((HERE / 'stellar_evolution.dat').read_bytes()).hexdigest()
    for name, (tc, rc) in CASES.items():
        folder = HERE / name
        text = (folder / 'run.par').read_text()
        assert f'hd_thermal_conduction=.{str(tc).lower()}.' in text, name
        assert f'hd_radiative_cooling=.{str(rc).lower()}.' in text, name
        assert 'Tfix=.true.' in text, name
        assert '@' not in text, name
        for filename, expected in [('mod_usr.t', source_hash), ('stellar_evolution.dat', history_hash)]:
            assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == expected, (name, filename)
        body = '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('!'))
        normalized.append(re.sub(r'hd_(thermal_conduction|radiative_cooling)=\.(true|false)\.',
                                 r'hd_\1=.SWITCH.', body))
    assert len(set(normalized)) == 1, 'Unintended differences between cases'
    rows = history()
    assert len(rows) == 3
    assert [row[0] for row in rows] == [4300000, 4500000, 4770000]
    assert [row[2] for row in rows] == [2000, 15, 2000]
    for row, expected in zip(rows, [1e-6, 5e-5, 1e-5]):
        assert math.isclose(10**row[1], expected, rel_tol=1e-14)
    print('Validated: only the two physics switches differ; MS/RSG/WR phase ends '
          '4.3 / 4.5 / 4.77 Myr match the screenshot.', flush=True)


def execute(command, cwd, log):
    with log.open('w') as stream:
        stream.write('# Purpose: '+log.stem+' transcript for the four-case evolving-wind campaign.\n')
        stream.flush()
        result = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text(errors='replace')[-6000:], flush=True)
        raise RuntimeError(f'Command failed ({result.returncode}); see {log}')


def build(library):
    build_dir = HERE / 'build'
    build_dir.mkdir(exist_ok=True)
    if library is None:
        library = HERE / 'library'
        library.mkdir(exist_ok=True)
        shutil.copy2(HERE / 'amrvac.h', library / 'amrvac.h')
        execute(['make', '-j4', '-f', str(SOURCE / 'arch/lib.make'),
                 'AMRVAC_DIR='+str(SOURCE), 'ARCH=default', 'NDIM=1',
                 'F90FLAGS='+' '.join(FLAGS)], library, HERE / 'library_build.log')
    else:
        library = Path(library).resolve()
        if not (library / 'libamrvac.a').is_file():
            raise RuntimeError('Requested prebuilt 1D AMRVAC library does not exist')
    shutil.copy2(HERE / 'amrvac.h', build_dir / 'amrvac.h')
    for name, path in [('mod_usr', HERE / 'mod_usr.t'), ('amrvac', SOURCE / 'src/amrvac.t')]:
        dest = build_dir / (name + '.f')
        with dest.open('w') as stream:
            stream.write('! Purpose: Generated 1D Fortran for the evolving-wind comparison.\n')
            stream.flush()
            subprocess.run([str(SOURCE / 'src/vacpp.pl'), '-d=1', str(path)],
                           cwd=build_dir, stdout=stream, check=True)
        execute(['mpif90', *FLAGS, '-I'+str(library), '-c', str(dest), '-o', name+'.o'],
                build_dir, HERE / (name+'_compile.log'))
    execute(['mpif90', *FLAGS, 'mod_usr.o', 'amrvac.o', '-L'+str(library),
             '-lamrvac', '-o', 'amrvac'], build_dir, HERE / 'link.log')
    execute(['mpif90', *FLAGS, '-I'+str(library), '-I'+str(build_dir),
             str(HERE/'phase_probe.f'), 'mod_usr.o', '-L'+str(library),
             '-lamrvac', '-o', 'phase_probe'], build_dir, HERE/'phase_probe_compile.log')
    execute([str(build_dir/'phase_probe')], HERE, HERE/'phase_probe.log')
    commit = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    (HERE / 'build_info.txt').write_text('# Purpose: Identify the AMRVAC build used for this campaign.\n'
        f'Source: {SOURCE}\nCommit: {commit}\nLibrary: {library}\n'
        f'Flags: {" ".join(FLAGS)}\n'
        f'mod_usr.t SHA256: {hashlib.sha256((HERE / "mod_usr.t").read_bytes()).hexdigest()}\n')
    print('Built build/amrvac.', flush=True)


def run(cases, ranks, smoke_years=None):
    validate()
    exe = HERE / 'build/amrvac'
    if not exe.is_file():
        raise RuntimeError('Build first: python3 manage.py build')
    fingerprint = 'mod_usr.t SHA256: '+hashlib.sha256((HERE/'mod_usr.t').read_bytes()).hexdigest()
    if not (HERE/'build_info.txt').is_file() or fingerprint not in (HERE/'build_info.txt').read_text():
        raise RuntimeError('The executable does not match mod_usr.t; rebuild before running')
    env = os.environ.copy()
    env['OMP_NUM_THREADS'] = '1'
    results = []
    for name in cases:
        folder = HERE / name
        par = folder / 'run.par'
        if smoke_years is not None:
            subdir = 'smoke_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            output = folder / subdir
            output.mkdir()
            text = par.read_text().replace("base_filename='output/test'", f"base_filename='{subdir}/test'")
            text = re.sub(r'time_max=\S+', f'time_max={smoke_years*YEAR_CODE:.17e}', text)
            text = re.sub(r'dtsave_dat=\S+', f'dtsave_dat={smoke_years*YEAR_CODE:.17e}', text)
            text = '! Purpose: Short startup validation; production run.par is unchanged.\n' + text
            par = output / 'smoke.par'
            par.write_text(text)
            log = output / 'run.log'
        else:
            if list((folder / 'output').glob('test*.dat')) or (folder / 'run.log').exists():
                raise RuntimeError(f'{name}: production output exists; refusing to overwrite it')
            log = folder / 'run.log'
        print(f'Starting {name} ({"smoke" if smoke_years is not None else "production"}), {ranks} MPI ranks.', flush=True)
        try:
            # AMRVAC v3.1 splits its -i argument on spaces internally. Use a
            # relative input path even though subprocess passes argv correctly.
            execute(['mpirun', '--bind-to', 'none', '-np', str(ranks), str(exe), '-i', str(par.relative_to(folder))], folder, log)
            transcript = log.read_text(errors='replace')
            tc, rc = CASES[name]
            assert 'Finished AMRVAC' in transcript, 'Missing completion marker'
            assert ('Spitzer HD par:' in transcript) == tc, 'Conduction activation mismatch'
            assert ('Cooling Tfix enabled: T' in transcript) == rc, 'Cooling activation mismatch'
            assert 'EVOLVING wind table:' in transcript, 'Missing evolving wind activation'
            if smoke_years is None:
                from validation_tools.audit_native import audit
                snapshots=[audit(path) for path in sorted((folder/'output').glob('test*.dat'))]
                assert snapshots, 'Missing native production snapshots'
                target=float(re.search(r'time_max=(\S+)',par.read_text()).group(1).lower().replace('d','e'))/YEAR_CODE
                assert math.isclose(snapshots[-1]['age_yr'],target,rel_tol=1e-10), 'Incorrect final age'
                with (folder/'native_audit.csv').open('w',newline='') as stream:
                    stream.write('# Purpose: Final native-cell positivity and physical-state audit.\n')
                    writer=csv.DictWriter(stream,fieldnames=snapshots[0])
                    writer.writeheader()
                    writer.writerows(snapshots)
            results.append(f'{name}: PASS; {log.relative_to(HERE)}')
        except (RuntimeError, AssertionError, ValueError) as exc:
            results.append(f'{name}: FAIL; {exc}')
    report_name = 'smoke_results.txt' if smoke_years is not None else 'run_results.txt'
    if smoke_years is None and len(cases)==1:
        report_name='run_results_'+cases[0]+'.txt'
    report = HERE / report_name
    report.write_text('# Purpose: Completion and physics-activation checks for the four runs.\n'
                      + '\n'.join(results) + '\n')
    print('\n'.join(results), flush=True)
    if any(': FAIL;' in line for line in results):
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'validate', 'build', 'smoke', 'run'])
    parser.add_argument('--years', type=float, default=4_770_000)
    parser.add_argument('--smoke-years', type=float, default=100)
    parser.add_argument('--ranks', type=int, default=4)
    parser.add_argument('--case', choices=['all', *CASES], default='all')
    parser.add_argument('--library', help='Optional compatible prebuilt 1D AMRVAC library (read only)')
    args = parser.parse_args()
    if args.ranks < 1 or args.smoke_years <= 0:
        parser.error('Ranks and smoke duration must be positive')
    if args.action == 'prepare': prepare(args.years)
    elif args.action == 'validate': validate()
    elif args.action == 'build': build(args.library)
    else: run(list(CASES) if args.case == 'all' else [args.case], args.ranks,
              args.smoke_years if args.action == 'smoke' else None)
