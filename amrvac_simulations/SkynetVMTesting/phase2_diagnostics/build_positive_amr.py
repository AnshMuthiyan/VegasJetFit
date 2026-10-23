# Purpose: Build an isolated AMRVAC 3.2 executable with conservative admissibility fallback for 1D HD refinement.
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--build-name', default='positive_amr_build')
parser.add_argument('--phase-aware-dt', action='store_true')
parser.add_argument('--exact-wind-flux', action='store_true')
parser.add_argument('--audit-tc-floor', action='store_true')
args = parser.parse_args()
HERE = Path(__file__).resolve().parent
BASE = Path('/tmp/skynet-v32-qdvc32bu')
BUILD = HERE/args.build_name
BUILD.mkdir(exist_ok=True)
# AMRVAC setup invokes shell commands without quoting AMRVAC_DIR. Build on
# the Linux filesystem without spaces, then copy reviewable artifacts back.
TEMP = Path(tempfile.mkdtemp(prefix='positive-amr-'))
SOURCE = TEMP/'amrvac_source'
SOURCE.mkdir()
for name in ('src', 'arch', 'lib'):
    shutil.copytree(BASE/'amrvac'/name, SOURCE/name)
shutil.copy2(BASE/'amrvac/setup.pl', SOURCE/'setup.pl')
PROBLEM = TEMP/'problem'
PROBLEM.mkdir()
for name in ('mod_usr.t', 'amrvac.h'):
    shutil.copy2(HERE.parent/name, PROBLEM/name)
if args.phase_aware_dt:
    usr = (PROBLEM/'mod_usr.t').read_text()
    usr = usr.replace('    double precision :: phase_end_code,tolerance',
                      '    double precision :: phase_end_code,tolerance,mdot_cgs,speed_cgs,temp_k,wind_signal', 1)
    usr = usr.replace('    dtnew = bigdouble', '''    dtnew = bigdouble
    ! Bound the currently injected wind; the standard CFL also bounds all
    ! interior gas, including surviving fast wind from the preceding phase.
    call phase_wind(global_time,mdot_cgs,speed_cgs,temp_k)
    wind_signal=speed_cgs/unit_velocity+sqrt(hd_gamma*temp_k/unit_temperature)
    ! Include the next phase inside the existing boundary-roundoff tolerance.
    ! This bounds a fast WR injection even if a checkpoint time is a few ULPs
    ! below its tabulated switch and RK stage times cross that switch.
    call phase_wind(global_time+100.d0*epsilon(one)*max(one,abs(global_time)), &
      mdot_cgs,speed_cgs,temp_k)
    wind_signal=max(wind_signal,speed_cgs/unit_velocity+sqrt(hd_gamma*temp_k/unit_temperature))''', 1)
    usr = usr.replace('      max_wind_signal', '      wind_signal', 1)
    (PROBLEM/'mod_usr.t').write_text('! Purpose: Evolving-wind problem with a phase-aware boundary CFL constraint.\n'+usr)
if args.exact_wind_flux:
    usr=(PROBLEM/'mod_usr.t').read_text()
    usr=usr.replace('  subroutine usr_init()',
                    '  subroutine usr_init()\n    use mod_physics, only: phys_modify_wLR',1)
    usr=usr.replace('    call hd_activate()',
                    '    call hd_activate()\n    phys_modify_wLR=>prescribed_wind_face',1)
    routine='''
  ! Set identical analytic states at the inner boundary face so the numerical
  ! Riemann flux equals the prescribed stellar mass, momentum, and energy flux.
  ! Only the physical injection face is changed; interior faces retain TVDLF.
  subroutine prescribed_wind_face(ixI^L,ixO^L,qt,wLC,wRC,wLp,wRp,s,idir)
    use mod_global_parameters
    integer, intent(in) :: ixI^L,ixO^L,idir
    double precision, intent(in) :: qt
    double precision, intent(inout) :: wLC(ixI^S,1:nw),wRC(ixI^S,1:nw)
    double precision, intent(inout) :: wLp(ixI^S,1:nw),wRp(ixI^S,1:nw)
    type(state) :: s
    double precision :: mdot_cgs,speed_cgs,temp_k,rho_code,speed_code,pressure_code
    integer :: i
    if(idir/=1) return
    if(.not.s%is_physical_boundary(1)) return
    i=ixMlo1-1
    if(i<ixOmin1.or.i>ixOmax1) return
    if(nw/=3) call mpistop('Prescribed wind flux requires the supplied 1D HD layout')
    call phase_wind(qt,mdot_cgs,speed_cgs,temp_k)
    rho_code=mdot_cgs/(4.d0*dpi*speed_cgs*(xprobmin1*unit_length)**2)/unit_density
    speed_code=speed_cgs/unit_velocity
    pressure_code=rho_code*temp_k/unit_temperature
    wLp(i,rho_)=rho_code
    wLp(i,mom(1))=speed_code
    wLp(i,p_)=pressure_code
    wRp(i,:)=wLp(i,:)
    wLC(i,rho_)=rho_code
    wLC(i,mom(1))=rho_code*speed_code
    wLC(i,e_)=pressure_code/(hd_gamma-one)+half*rho_code*speed_code**2
    wRC(i,:)=wLC(i,:)
  end subroutine prescribed_wind_face
'''
    usr=usr.replace('end module mod_usr',routine+'\nend module mod_usr',1)
    (PROBLEM/'mod_usr.t').write_text('! Purpose: Conservative phase-aware wind injection with an exact prescribed inner-face flux.\n'+usr)
if args.audit_tc_floor:
    usr=(PROBLEM/'mod_usr.t').read_text()
    usr=usr.replace('    if(mod(iit,1000)/=0.and.qt+dt<time_max-1.d-10) return',
      '    if(mod(iit,1000)/=0.and.qt+dt<time_max-1.d-10.and.iit+1<it_max) return',1)
    usr=usr.replace('  logical :: audit_initialized=.false.', '''  logical :: audit_initialized=.false.
  double precision :: tc_floor_events=0.d0,tc_floor_energy=0.d0,tc_floor_worst=0.d0
  logical :: tc_floor_audit_initialized=.false.''',1)
    usr=usr.replace('  subroutine usr_init()',
      '  subroutine usr_init()\n    use mod_supertimestepping, only: set_error_handling_to_head',1)
    usr=usr.replace('    call hd_activate()',
      '    call hd_activate()\n    if(hd_thermal_conduction) call set_error_handling_to_head(observe_tc_floor)',1)
    usr=usr.replace("    if(ratio>guard_max_budget_fraction)",
      "    if(hd_thermal_conduction) call audit_tc_floor(qt+dt)\n    if(ratio>guard_max_budget_fraction)",1)
    routines='''
  ! Observe the same internal-energy floor used by AMRVAC's stock HD STS
  ! handler. Counts are state-evaluation diagnostics, not net added energy.
  subroutine observe_tc_floor(w,x,ixI^L,ixO^L,step)
    use mod_global_parameters
    use mod_small_values, only: small_values_method
    integer, intent(in) :: ixI^L,ixO^L,step
    double precision, intent(inout) :: w(ixI^S,1:nw)
    double precision, intent(in) :: x(ixI^S,1:ndim)
    double precision :: floor_e,delta,scale
    integer :: i
    floor_e=small_pressure/(hd_gamma-one)
    if(.not.any(w(ixO^S,e_)<floor_e)) return
    if(small_values_method/='replace') call mpistop('TC audit needs replace')
    call assert_finite(ixI^L,ixO^L,w,x,'TC stage before existing floor')
    do i=ixOmin1,ixOmax1
      if(w(i,e_)>=floor_e) cycle
      delta=floor_e-w(i,e_)
      scale=max(half*w(i,mom(1))**2/w(i,rho_)+abs(w(i,e_)),floor_e)
      tc_floor_events=tc_floor_events+one
      tc_floor_worst=max(tc_floor_worst,delta/scale)
      if(i>=ixMlo1.and.i<=ixMhi1.and.associated(block)) then
        if(associated(block%dvolume)) tc_floor_energy=tc_floor_energy+ &
          delta*block%dvolume(i)*4.d0*dpi*unit_pressure*unit_length**3
      end if
      w(i,e_)=floor_e
    end do
  end subroutine observe_tc_floor

  subroutine audit_tc_floor(qt)
    use mod_global_parameters
    double precision, intent(in) :: qt
    double precision :: local(2),total(2),worst
    integer :: iu
    local=[tc_floor_events,tc_floor_energy]
    call MPI_ALLREDUCE(local,total,2,MPI_DOUBLE_PRECISION,MPI_SUM,icomm,ierrmpi)
    call MPI_ALLREDUCE(tc_floor_worst,worst,1,MPI_DOUBLE_PRECISION,MPI_MAX,icomm,ierrmpi)
    if(mype/=0) return
    if(.not.tc_floor_audit_initialized) then
      open(newunit=iu,file=trim(base_filename)//'_tc_floor.csv',status='replace')
      write(iu,'(A)') '# Purpose: Existing TC floor evaluation sums.'
      write(iu,'(A)') 'age_yr,tc_floor_events,'// &
        'tc_floor_evaluation_energy_erg,worst_cell_fraction'
      tc_floor_audit_initialized=.true.
    else
      open(newunit=iu,file=trim(base_filename)//'_tc_floor.csv',status='old',position='append')
    endif
    write(iu,'(ES24.16,3(A,ES24.16))') qt*unit_time/const_years,',',total(1),',',total(2),',',worst
    close(iu)
  end subroutine audit_tc_floor
'''
    usr=usr.replace('end module mod_usr',routines+'\nend module mod_usr',1)
    (PROBLEM/'mod_usr.t').write_text('! Purpose: Stable prescribed-wind problem with separate audit of existing TC energy floors.\n'+usr)
shutil.copy2(PROBLEM/'mod_usr.t', BUILD/'mod_usr.t')
shutil.copy2(PROBLEM/'amrvac.h', BUILD/'amrvac.h')

target = SOURCE/'src/amr/mod_refine.t'
original = target.read_text()
text = original.replace('    use mod_physics, only: phys_to_conserved, phys_handle_small_values',
'''    use mod_physics, only: phys_to_conserved, phys_handle_small_values, phys_gamma
    use mod_variables, only: iw_rho, iw_mom, iw_e
    use mod_comm_lib, only: mpistop
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite''', 1)
text = text.replace('    logical :: fine_^L', '''    logical :: fine_^L
    logical :: positivity_fallback
    double precision :: minimum_internal_energy, candidate_internal_energy
    double precision :: conservation_error, child_volume''', 1)
anchor = '       {end do\\}\n    {end do\\}\n    if(stagger_grid) then'
replacement = r'''       {end do\}
       {^IFONED
       ! Purpose: Preserve a valid conservative parent average if second-order
       ! reconstruction creates invalid 1D HD children; never add thermal energy.
       if (.not.prolongprimitive) then
         if(nw/=3.or.iw_rho/=1.or.iw_e/=3.or.size(iw_mom)/=1) &
           call mpistop('Positive AMR fallback is restricted to this 1D HD layout')
         minimum_internal_energy=small_pressure/(phys_gamma-one)
         positivity_fallback=.false.
         do ix1=ixFi1,ixFi1+1
           if(any(.not.ieee_is_finite(wFi(ix1,1:nw)))) then
             positivity_fallback=.true.
           else if(wFi(ix1,iw_rho)<=small_density) then
             positivity_fallback=.true.
           else
             candidate_internal_energy=wFi(ix1,iw_e) &
               -half*wFi(ix1,iw_mom(1))**2/wFi(ix1,iw_rho)
             if(candidate_internal_energy<minimum_internal_energy) positivity_fallback=.true.
           end if
         end do
         if(positivity_fallback) then
           if(any(.not.ieee_is_finite(wCo(ixCo1,1:nw)))) &
             call mpistop('Invalid parent in positive AMR fallback')
           if(wCo(ixCo1,iw_rho)<=small_density) &
             call mpistop('Invalid parent density in positive AMR fallback')
           candidate_internal_energy=wCo(ixCo1,iw_e) &
             -half*wCo(ixCo1,iw_mom(1))**2/wCo(ixCo1,iw_rho)
           if(candidate_internal_energy<minimum_internal_energy) &
             call mpistop('Invalid parent thermal energy in positive AMR fallback')
           ! Identical child states preserve each volume-weighted conserved
           ! quantity since the two child volumes partition the parent volume.
           do ix1=ixFi1,ixFi1+1
             wFi(ix1,1:nw)=wCo(ixCo1,1:nw)
           end do
           child_volume=sum(sFi%dvolume(ixFi1:ixFi1+1))
           conservation_error=maxval(abs(child_volume*wCo(ixCo1,1:nw) &
             -sCo%dvolume(ixCo1)*wCo(ixCo1,1:nw))/ &
             max(abs(sCo%dvolume(ixCo1)*wCo(ixCo1,1:nw)),tiny(one)))
           if(conservation_error>1.d-12) &
             call mpistop('Positive refinement fallback failed conservative volume check')
           write(*,*) 'AMR parent-copy fallback it,rank,r=',it,mype,sCo%x(ixCo1,1)
         end if
       end if
       }
    {end do\}
    if(stagger_grid) then'''
if text.count(anchor) != 1:
    raise RuntimeError('Unexpected AMRVAC source: refinement insertion point changed')
text = text.replace(anchor, replacement, 1)
target.write_text('! Purpose: AMRVAC refinement with conservative 1D HD admissibility fallback.\n'+text)
# The copied compiled library contains dereferenced template symlinks.
# Update its local template too so make actually regenerates this module.
(SOURCE/'lib/1d1_default/mod_refine.t').write_text(target.read_text())
(BUILD/'original_mod_refine.t').write_text('! Purpose: Unmodified reference source for reviewing the local refinement experiment.\n'+original)
shutil.copy2(target, BUILD/'patched_mod_refine.t')
FLAGS = '-cpp -ffree-form -fimplicit-none -O3 -g -fcheck=bounds -fbacktrace -ffpe-trap=invalid,zero,overflow'
env = dict(os.environ, AMRVAC_DIR=str(SOURCE), OMP_NUM_THREADS='1')
if (BUILD/'build.log').exists():
    shutil.copy2(BUILD/'build.log', BUILD/'previous_build.log')
with (BUILD/'build.log').open('w') as log:
    log.write('# Purpose: Isolated positivity-fallback AMRVAC compilation transcript.\n')
    log.flush()
    for command in (['perl',str(SOURCE/'setup.pl'),'-d=1'],
                    ['make','hdr','F90=mpifort','F90FLAGS='+FLAGS],
                    ['make','-j4','F90=mpifort','F90FLAGS='+FLAGS]):
        print('BUILD',command,flush=True)
        subprocess.run(command,cwd=PROBLEM,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
shutil.copy2(PROBLEM/'amrvac', BUILD/'amrvac')
report={'purpose':'Build provenance for conservative 1D HD refinement fallback.',
        'baseline_source_commit':'c45d84650ed3379eb22dcfa6fb927a45734e5d8c', 'flags':FLAGS,
        'phase_aware_boundary_cfl':args.phase_aware_dt,
        'prescribed_inner_wind_flux':args.exact_wind_flux,
        'tc_floor_observer':args.audit_tc_floor,
        'original_source_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'patched_source_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'executable':str(BUILD/'amrvac'), 'temporary_build':str(TEMP)}
(BUILD/'build.json').write_text(json.dumps(report,indent=2)+'\n')
print('EXECUTABLE',BUILD/'amrvac',flush=True)
