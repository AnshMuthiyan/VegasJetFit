# Purpose: Reproduce the first invalid floating-point operation in an isolated
# short copy of the failed hydro-only run, leaving production inputs unchanged.
from pathlib import Path
import datetime
import os
import re
import shutil
import subprocess
import manage

ROOT = manage.HERE
HERE = ROOT / ('diagnostic_nan_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
HERE.mkdir()
(HERE/'output').mkdir()
source = (ROOT/'mod_usr.t').read_text()
source = source.replace('    use mod_global_parameters\n    integer :: n\n',
    '    use mod_global_parameters\n'
    '    use mod_physics, only: phys_to_primitive\n'
    '    use, intrinsic :: ieee_exceptions, only: ieee_set_halting_mode, &\n'
    '      ieee_invalid, ieee_divide_by_zero, ieee_overflow\n'
    '    integer :: n\n', 1)
source = source.replace('    do n=1,size(par_files)\n',
    '    call ieee_set_halting_mode(ieee_invalid,.true.)\n'
    '    call ieee_set_halting_mode(ieee_divide_by_zero,.true.)\n'
    '    call ieee_set_halting_mode(ieee_overflow,.true.)\n'
    '    do n=1,size(par_files)\n', 1)
source = source.replace('    call hd_activate()\n',
    '    call hd_activate()\n    phys_to_primitive=>diagnostic_primitive\n', 1)
probe = '''
  ! Purpose: Capture the conserved state whose repaired primitive pressure fails.
  subroutine diagnostic_primitive(ixI^L,ixO^L,w,x)
    use mod_global_parameters
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    use, intrinsic :: iso_fortran_env, only: error_unit
    integer, intent(in) :: ixI^L,ixO^L
    double precision, intent(inout) :: w(ixI^S,1:nw)
    double precision, intent(in) :: x(ixI^S,1:ndim)
    double precision :: original(ixI^S,1:nw),ke
    integer :: i
    original=w
    call hd_to_primitive(ixI^L,ixO^L,w,x)
    do i=ixOmin1,ixOmax1
      if(w(i,rho_)<=zero.or.w(i,p_)<=zero.or.any(.not.ieee_is_finite(w(i,:)))) then
        ke=half*original(i,mom(1))**2/original(i,rho_)
        write(error_unit,*) 'INVALID PRIMITIVE: it,time,rank,cell,radius=',it,global_time,mype,i,x(i,1)
        write(error_unit,*) 'Conserved rho,momentum,total energy=',original(i,:)
        write(error_unit,*) 'Kinetic energy, original pressure=',ke,(hd_gamma-one)*(original(i,e_)-ke)
        write(error_unit,*) 'Repaired primitive rho,velocity,pressure=',w(i,:)
        write(error_unit,*) 'small_pressure,spacing(kinetic energy)=',small_pressure,spacing(ke)
        flush(error_unit)
        call mpistop('Diagnostic caught nonpositive primitive before logarithm')
      endif
    enddo
  end subroutine diagnostic_primitive
'''
source = source.replace('end module mod_usr', probe+'\nend module mod_usr')
(HERE/'mod_usr.t').write_text('! Purpose: Diagnostic copy with hardware floating-point traps enabled.\n'+source)
shutil.copy2(ROOT/'stellar_evolution.dat', HERE/'stellar_evolution.dat')
shutil.copy2(ROOT/'amrvac.h', HERE/'amrvac.h')
info = (ROOT/'build_info.txt').read_text()
library = Path(re.search(r'^Library: (.*)$', info, re.M).group(1))
flags = ['-cpp', '-ffree-form', '-fimplicit-none', '-O0', '-g',
         '-fcheck=all', '-fbacktrace', '-ffpe-trap=invalid,zero,overflow']
for name, src in [('mod_usr', HERE/'mod_usr.t'), ('amrvac', manage.SOURCE/'src/amrvac.t')]:
    dest = HERE/(name+'.f')
    with dest.open('w') as stream:
        stream.write('! Purpose: Generated trapped diagnostic Fortran.\n')
        stream.flush()
        subprocess.run([str(manage.SOURCE/'src/vacpp.pl'), '-d=1', str(src)],
                       cwd=HERE, stdout=stream, check=True)
    manage.execute(['mpif90', *flags, '-I'+str(library), '-c', str(dest), '-o', name+'.o'],
                   HERE, HERE/(name+'_compile.log'))
manage.execute(['mpif90', *flags, 'mod_usr.o', 'amrvac.o', '-L'+str(library),
                '-lamrvac', '-o', 'amrvac'], HERE, HERE/'link.log')
par = (ROOT/'tc_off_rc_off/run.par').read_text()
par = re.sub(r'time_max=\S+', f'time_max={300*manage.YEAR_CODE:.17e}', par)
par = re.sub(r'dtsave_dat=\S+', f'dtsave_dat={50*manage.YEAR_CODE:.17e}', par)
par = par.replace('ditsave_log=10000', 'ditsave_log=1000')
(HERE/'run.par').write_text('! Purpose: Reproduce first invalid hydro-only operation within 300 years.\n'+par)
print('Diagnostic folder: '+str(HERE), flush=True)
with (HERE/'run.log').open('w') as log:
    log.write('# Purpose: First-invalid-operation backtrace from isolated trapped run.\n')
    log.flush()
    result = subprocess.run(['mpirun', '-np', '4', str(HERE/'amrvac'), '-i', 'run.par'],
        cwd=HERE, env={**os.environ, 'OMP_NUM_THREADS':'1'}, stdout=log,
        stderr=subprocess.STDOUT, timeout=240)
print('Diagnostic exit code: '+str(result.returncode), flush=True)
print((HERE/'run.log').read_text(errors='replace')[-10000:], flush=True)
