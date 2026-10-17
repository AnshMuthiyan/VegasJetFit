# Purpose: Create a separate, auditable repair campaign while preserving failed runs.
from pathlib import Path
import shutil

OLD = Path(__file__).resolve().parent
NEW = OLD.parent / 'evolving_wind_repaired'
if (NEW/'mod_usr.t').exists():
    raise SystemExit('Repair campaign already exists; preserve its tested source and inputs.')
NEW.mkdir(exist_ok=True)
for filename in ['manage.py', 'template.par', 'stellar_evolution.dat', 'amrvac.h',
                 'Makefile', '.gitignore', 'phase_probe.f', 'launch_campaign.py']:
    shutil.copy2(OLD/filename, NEW/filename)
manager = (NEW/'manage.py').read_text().replace("'-fcheck=bounds', '-fbacktrace']",
    "'-fcheck=bounds', '-fbacktrace', '-ffpe-trap=invalid,zero,overflow']")
(NEW/'manage.py').write_text(manager)
source = (OLD/'mod_usr.t').read_text()
source = source.replace('  use mod_hd\n', '  use mod_hd\n'
    '  use mod_physics, only: sub_small_values, phys_handle_small_values, phys_to_primitive\n', 1)
source = source.replace('contains\n', '''  ! Numerical energy rescue is tied to representable spacing, not a physical T floor.
  double precision :: guard_ulps=32.d0, guard_max_cell_fraction=1.d-3
  double precision :: guard_max_budget_fraction=1.d-3
  double precision :: guard_events=0.d0, guard_energy_cgs=0.d0, guard_worst_fraction=0.d0
  logical :: audit_initialized=.false.
  procedure(sub_small_values), pointer :: stock_small_values => null()
contains
''', 1)
source = source.replace('      stellar_param_file\n',
    '      stellar_param_file, guard_ulps, guard_max_cell_fraction, guard_max_budget_fraction\n', 1)
source = source.replace('    call hd_activate()\n', '''    call hd_activate()
    stock_small_values=>phys_handle_small_values
    phys_handle_small_values=>guarded_small_values
    phys_to_primitive=>guarded_to_primitive
    usr_process_adv_grid=>checked_advance
    usr_process_adv_global=>audit_after_advance
''', 1)
guard = '''
  !> Reject nonfinite values instead of allowing comparisons with NaN to bypass checks.
  subroutine assert_finite(ixI^L,ixO^L,w,x,context)
    use mod_global_parameters
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    use, intrinsic :: iso_fortran_env, only: error_unit
    integer, intent(in) :: ixI^L,ixO^L
    double precision, intent(in) :: w(ixI^S,1:nw),x(ixI^S,1:ndim)
    character(len=*), intent(in) :: context
    integer :: i
    do i=ixOmin1,ixOmax1
      if(any(.not.ieee_is_finite(w(i,:))).or.w(i,rho_)<small_density) then
        write(error_unit,*) 'Invalid state: ',context,' it,rank,radius=',it,mype,x(i,1)
        write(error_unit,*) 'State=',w(i,:)
        flush(error_unit)
        call mpistop('Nonfinite state or density below floor; refusing silent repair')
      endif
    enddo
  end subroutine assert_finite

  !> Rescue only small thermal deficits, using an energy increment that survives rounding.
  subroutine guarded_small_values(primitive,w,x,ixI^L,ixO^L,subname)
    use mod_global_parameters
    use, intrinsic :: iso_fortran_env, only: error_unit
    logical, intent(in) :: primitive
    integer, intent(in) :: ixI^L,ixO^L
    double precision, intent(inout) :: w(ixI^S,1:nw)
    double precision, intent(in) :: x(ixI^S,1:ndim)
    character(len=*), intent(in) :: subname
    double precision :: ke,emin,new_energy,delta,fraction,scale
    integer :: i
    call assert_finite(ixI^L,ixO^L,w,x,subname)
    if(.not.primitive) then
      do i=ixOmin1,ixOmax1
        ke=half*w(i,mom(1))**2/w(i,rho_)
        emin=small_pressure/(hd_gamma-one)
        scale=max(abs(ke),abs(w(i,e_)))
        emin=max(emin,guard_ulps*spacing(scale))
        if(w(i,e_)-ke<emin) then
          new_energy=ke+emin
          delta=max(zero,new_energy-w(i,e_))
          fraction=delta/max(scale,small_pressure)
          if(fraction>guard_max_cell_fraction) then
            write(error_unit,*) 'Excessive energy rescue: ',subname,it,mype,x(i,1),fraction
            write(error_unit,*) 'Conserved state, KE, delta=',w(i,:),ke,delta
            flush(error_unit)
            call mpistop('Hydro deficit exceeds allowed cell energy fraction')
          endif
          w(i,e_)=new_energy
          if(delta>zero) then
            guard_events=guard_events+one
            guard_worst_fraction=max(guard_worst_fraction,fraction)
            ! Diagnostic sum over corrected native-cell evaluations, including RK
            ! intermediates. It is not a measurement of net physical energy error.
            if(i>=ixMlo1.and.i<=ixMhi1.and.associated(block)) then
              if(associated(block%dvolume)) guard_energy_cgs=guard_energy_cgs+ &
                delta*block%dvolume(i)*4.d0*dpi*unit_density*unit_velocity**2*unit_length**3
            endif
          endif
        endif
      enddo
    endif
    call stock_small_values(primitive,w,x,ixI^L,ixO^L,subname)
    call assert_finite(ixI^L,ixO^L,w,x,subname)
  end subroutine guarded_small_values

  subroutine guarded_to_primitive(ixI^L,ixO^L,w,x)
    use mod_global_parameters
    integer, intent(in) :: ixI^L,ixO^L
    double precision, intent(inout) :: w(ixI^S,1:nw)
    double precision, intent(in) :: x(ixI^S,1:ndim)
    call guarded_small_values(.false.,w,x,ixI^L,ixO^L,'before primitive conversion')
    call hd_to_primitive(ixI^L,ixO^L,w,x)
    call assert_finite(ixI^L,ixO^L,w,x,'after primitive conversion')
    if(any(w(ixO^S,p_)<=zero)) call mpistop('Nonpositive pressure before log reconstruction')
  end subroutine guarded_to_primitive

  subroutine checked_advance(igrid,level,ixI^L,ixO^L,qt,w,x)
    use mod_global_parameters
    integer, intent(in) :: igrid,level,ixI^L,ixO^L
    double precision, intent(in) :: qt,x(ixI^S,1:ndim)
    double precision, intent(inout) :: w(ixI^S,1:nw)
    call guarded_small_values(.false.,w,x,ixI^L,ixO^L,'completed advance')
  end subroutine checked_advance

  double precision function injected_energy(qt) result(energy)
    use mod_global_parameters
    double precision, intent(in) :: qt
    double precision :: age,previous,duration
    integer :: phase
    age=max(zero,qt)*unit_time/const_years
    previous=zero
    energy=zero
    do phase=1,nages
      duration=max(zero,min(age,ages(phase))-previous)*const_years
      energy=energy+half*rates(phase)*speeds(phase)**2*duration
      previous=ages(phase)
    enddo
  end function injected_energy

  subroutine audit_after_advance(iit,qt)
    use mod_global_parameters
    integer, intent(in) :: iit
    double precision, intent(in) :: qt
    double precision :: local(2),total(2),worst,energy,ratio
    integer :: iu
    if(mod(iit,1000)/=0.and.qt+dt<time_max-1.d-10) return
    local=[guard_events,guard_energy_cgs]
    call MPI_ALLREDUCE(local,total,2,MPI_DOUBLE_PRECISION,MPI_SUM,icomm,ierrmpi)
    call MPI_ALLREDUCE(guard_worst_fraction,worst,1,MPI_DOUBLE_PRECISION,MPI_MAX,icomm,ierrmpi)
    energy=injected_energy(qt+dt)
    ratio=total(2)/max(energy,tiny(one))
    if(mype==0) then
      if(.not.audit_initialized) then
        open(newunit=iu,file=trim(base_filename)//'_guard.csv',status='replace')
        write(iu,'(A)') '# Purpose: Numerical rescue state-evaluation sums; '// &
          'not a measurement of net energy error.'
        write(iu,'(A)') 'age_yr,rescue_events,evaluation_energy_erg,'// &
          'wind_energy_erg,evaluation_fraction,worst_cell_fraction'
        audit_initialized=.true.
      else
        open(newunit=iu,file=trim(base_filename)//'_guard.csv',status='old',position='append')
      endif
      write(iu,'(ES24.16,5(A,ES24.16))') (qt+dt)*unit_time/const_years,',',total(1),',',total(2), &
        ',',energy,',',ratio,',',worst
      close(iu)
    endif
    if(ratio>guard_max_budget_fraction) call mpistop('Numerical rescue evaluation budget exceeded')
  end subroutine audit_after_advance
'''
source = source.replace('end module mod_usr', guard+'\nend module mod_usr')
with (NEW/'mod_usr.t').open('w', newline='\n') as stream:
    stream.write('! Purpose: Fail-fast evolving wind with representable numerical energy rescue and auditing.\n'+source)
template=(NEW/'template.par').read_text().replace(" stellar_param_file='stellar_evolution.dat'",
    " stellar_param_file='stellar_evolution.dat'\n"
    " ! Numerical rescue in units of representable spacing, without a new physical T floor.\n"
    " guard_ulps=32.d0\n guard_max_cell_fraction=1.d-3\n guard_max_budget_fraction=1.d-3")
(NEW/'template.par').write_text(template)
print(NEW)
