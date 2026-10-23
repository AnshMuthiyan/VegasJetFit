! Purpose: Evolving-wind problem with a phase-aware boundary CFL constraint.
! Purpose: Fail-fast evolving wind with representable numerical energy rescue and auditing.
! Purpose: Matched 1D evolving-wind runs for all four conduction/cooling switches.
! Use the screenshot's MS/RSG/WR phases; keep the 100 K ambient independent of wind.
! All density conversions refer to TOTAL particles under the configured EOS.
module mod_usr
  use mod_hd
  use mod_physics, only: sub_small_values, phys_handle_small_values, phys_to_primitive
  implicit none
  double precision :: ambient_particles_cm3=1.0d4, ambient_temperature_k=100.d0
  character(len=256) :: stellar_param_file='stellar_evolution.dat'
  double precision :: ambient_rho, max_wind_signal
  double precision, allocatable :: ages(:), rates(:), speeds(:), temperatures(:)
  integer :: nages=0
  ! Numerical energy rescue is tied to representable spacing, not a physical T floor.
  double precision :: guard_ulps=32.d0, guard_max_cell_fraction=1.d-3
  double precision :: guard_max_budget_fraction=1.d-3
  double precision :: guard_events=0.d0, guard_energy_cgs=0.d0, guard_worst_fraction=0.d0
  logical :: audit_initialized=.false.
  procedure(sub_small_values), pointer :: stock_small_values => null()
contains
  subroutine usr_init()
    use mod_global_parameters
    integer :: n
    namelist /usr_list/ ambient_particles_cm3, ambient_temperature_k, &
      stellar_param_file, guard_ulps, guard_max_cell_fraction, guard_max_budget_fraction
    do n=1,size(par_files)
      open(unitpar,file=trim(par_files(n)),status='old')
      read(unitpar,usr_list,end=111)
111   close(unitpar)
    enddo
    unit_length=3.0857d18
    unit_density=1.0d-25
    unit_velocity=1.0d7
    usr_set_parameters=>set_parameters
    usr_init_one_grid=>initial_grid
    usr_special_bc=>wind_boundary
    usr_get_dt=>injection_dt
    usr_var_for_errest=>pressure_for_amr
    usr_aux_output=>temperature_output
    usr_add_aux_names=>temperature_name
    call set_coordinate_system('spherical')
    call hd_activate()
    stock_small_values=>phys_handle_small_values
    phys_handle_small_values=>guarded_small_values
    phys_to_primitive=>guarded_to_primitive
    usr_process_adv_grid=>checked_advance
    usr_process_adv_global=>audit_after_advance
  end subroutine usr_init

  subroutine set_parameters()
    use mod_global_parameters
    if(ambient_particles_cm3<=zero.or.ambient_temperature_k<=zero) &
      call mpistop('Invalid ambient parameters')
    ! mu=(1+4a)/(1+Hion+a*(1+Heion*(1+Heion2))). For the inherited
    ! fully ionized H/He EOS (a=0.1), mu=1.4/2.3. This defines n_total.
    ambient_rho=ambient_particles_cm3*mp_cgs*(1.d0+4.d0*He_abundance)/ &
      (1.d0+H_ion_fr+He_abundance*(1.d0+He_ion_fr*(1.d0+He_ion_fr2)))
    call load_history()
    ! Use a table-wide bound: the CFL must also be safe across wind transitions
    ! and when the first interior cells are initially stationary ambient gas.
    max_wind_signal=maxval(speeds/unit_velocity+sqrt(hd_gamma*temperatures/unit_temperature))
    length_convert_factor=unit_length
    time_convert_factor=unit_time
    w_convert_factor(rho_)=unit_density
    w_convert_factor(mom(1))=unit_velocity
    w_convert_factor(p_)=unit_pressure
    if(allocated(rc_fl)) then
      rc_fl%tlow=ambient_temperature_k/unit_temperature
      if(.not.rc_fl%Tfix) call mpistop('These tests require Tfix=T')
    endif
    if(mype==0) then
      write(*,'(A,ES24.16)') 'Ambient TOTAL particles [cm^-3]: ',ambient_particles_cm3
      write(*,'(A,ES24.16)') 'Ambient mass density [g cm^-3]: ',ambient_rho
      write(*,'(A,ES24.16)') 'Ambient temperature [K]: ',ambient_temperature_k
      write(*,'(A,A)') 'EVOLVING wind table: ',trim(stellar_param_file)
      write(*,'(A,I8)') 'Piecewise-constant wind phases: ',nages
      write(*,'(A,ES24.16)') 'Final phase end [yr]: ',ages(nages)
      write(*,'(A)') 'Phase changes use simulation age at the inner boundary (no travel delay).'
      write(*,'(A,ES24.16)') 'Temperature unit [K]: ',unit_temperature
      write(*,'(A,ES24.16)') 'Time unit [seconds]: ',unit_time
      if(allocated(rc_fl)) write(*,'(A,L1)') 'Cooling Tfix enabled: ',rc_fl%Tfix
    endif
  end subroutine set_parameters

  subroutine load_history()
    use mod_global_parameters
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    integer :: iu,ios,count
    double precision :: age,lograte,speed,temp
    character(len=1024) :: line
    if(allocated(ages)) return
    open(newunit=iu,file=trim(stellar_param_file),status='old',action='read',iostat=ios)
    if(ios/=0) call mpistop('Cannot open stellar history')
    count=0
    do
      read(iu,'(A)',iostat=ios) line
      if(ios<0) exit
      if(ios/=0) call mpistop('Cannot read stellar history')
      line=adjustl(line)
      if(len_trim(line)==0) cycle
      if(line(1:1)=='#'.or.line(1:1)=='!') cycle
      count=count+1
    enddo
    if(count<1) call mpistop('Empty stellar history')
    allocate(ages(count),rates(count),speeds(count),temperatures(count))
    rewind(iu)
    do
      read(iu,'(A)',iostat=ios) line
      if(ios<0) exit
      if(ios/=0) call mpistop('Cannot read stellar history')
      line=adjustl(line)
      if(len_trim(line)==0) cycle
      if(line(1:1)=='#'.or.line(1:1)=='!') cycle
      read(line,*,iostat=ios) age,lograte,speed,temp
      if(ios/=0) call mpistop('Malformed stellar history row')
      if(.not.all(ieee_is_finite([age,lograte,speed,temp]))) call mpistop('Nonfinite stellar history')
      if(age<zero.or.speed<=zero.or.temp<=zero) call mpistop('Invalid stellar history')
      if(lograte<=log10(tiny(one)).or.lograte>=log10(huge(one)/const_msun*const_years)) &
        call mpistop('Stellar mass loss outside representable range')
      if(nages>0) then
        if(age<=ages(nages)) call mpistop('Phase end ages must strictly increase')
        nages=nages+1
      else
        nages=1
      endif
      ages(nages)=age
      rates(nages)=10.d0**lograte*const_msun/const_years
      speeds(nages)=speed*1.d5
      temperatures(nages)=temp
    enddo
    close(iu)
    ! Discard unused storage left by rounded duplicate ages.
    ! maxval in the CFL bound must never inspect uninitialized array tails.
    rates=rates(:nages)
    speeds=speeds(:nages)
    temperatures=temperatures(:nages)
    ages=ages(:nages)
  end subroutine load_history

  subroutine phase_wind(time_code,mdot,speed,temp)
    use mod_global_parameters
    double precision,intent(in) :: time_code
    double precision,intent(out) :: mdot,speed,temp
    integer :: phase
    ! Ages are phase END ages. Keep parameters constant; never interpolate.
    ! Compare in code time to avoid reversing an exact transition by rounding.
    do phase=1,nages-1
      if(max(zero,time_code)<ages(phase)*const_years/unit_time) exit
    enddo
    mdot=rates(phase)
    speed=speeds(phase)
    temp=temperatures(phase)
  end subroutine phase_wind

  subroutine initial_grid(ixG^L, ix^L, w, x)
    use mod_global_parameters
    integer, intent(in) :: ixG^L, ix^L
    double precision, intent(in) :: x(ixG^S, 1:ndim)
    double precision, intent(inout) :: w(ixG^S, 1:nw)
    ! Start from undisturbed ambient gas. Do not impose a prebuilt bubble.
    w(ix^S, rho_) = ambient_rho / unit_density
    w(ix^S, mom(1)) = zero
    w(ix^S, p_) = w(ix^S, rho_) * ambient_temperature_k / unit_temperature
    call hd_to_conserved(ixG^L, ix^L, w, x)
  end subroutine initial_grid

  subroutine wind_boundary(qt, ixG^L, ixO^L, iB, w, x)
    use mod_global_parameters
    integer, intent(in) :: ixG^L, ixO^L, iB
    double precision, intent(in) :: qt, x(ixG^S, 1:ndim)
    double precision, intent(inout) :: w(ixG^S, 1:nw)
    double precision :: mdot_cgs,wind_speed,wind_temperature_k
    select case(iB)
    case(1)
      ! Exclude grids whose ghost cells cross the spherical origin.
      if (any(x(ixO^S, 1) <= zero)) call mpistop('Wind ghost radius <= 0: use stretching or larger xmin')
      call phase_wind(qt,mdot_cgs,wind_speed,wind_temperature_k)
      w(ixO^S, rho_) = mdot_cgs / (4.d0 * dpi * wind_speed * (x(ixO^S, 1) * unit_length)**2) / unit_density
      w(ixO^S, mom(1)) = wind_speed / unit_velocity
      w(ixO^S, p_) = w(ixO^S, rho_) * wind_temperature_k / unit_temperature
    case(2)
      w(ixO^S, rho_) = ambient_rho / unit_density
      w(ixO^S, mom(1)) = zero
      w(ixO^S, p_) = w(ixO^S, rho_) * ambient_temperature_k / unit_temperature
    case default
      call mpistop('Unexpected special boundary')
    end select
    call hd_to_conserved(ixG^L, ixO^L, w, x)
  end subroutine wind_boundary

  subroutine injection_dt(w, ixI^L, ixO^L, dtnew, dx1, x)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L
    double precision, intent(in) :: w(ixI^S, 1:nw), dx1, x(ixI^S, 1:ndim)
    double precision, intent(inout) :: dtnew
    double precision :: phase_end_code,tolerance,mdot_cgs,speed_cgs,temp_k,wind_signal
    integer :: phase
    dtnew = bigdouble
    ! Bound the currently injected wind; the standard CFL also bounds all
    ! interior gas, including surviving fast wind from the preceding phase.
    call phase_wind(global_time,mdot_cgs,speed_cgs,temp_k)
    wind_signal=speed_cgs/unit_velocity+sqrt(hd_gamma*temp_k/unit_temperature)
    ! Include the next phase inside the existing boundary-roundoff tolerance.
    ! This bounds a fast WR injection even if a checkpoint time is a few ULPs
    ! below its tabulated switch and RK stage times cross that switch.
    call phase_wind(global_time+100.d0*epsilon(one)*max(one,abs(global_time)), &
      mdot_cgs,speed_cgs,temp_k)
    wind_signal=max(wind_signal,speed_cgs/unit_velocity+sqrt(hd_gamma*temp_k/unit_temperature))
    ! Include the fast injected wind before the first interior CFL estimate.
    ! block%ds holds physical cell widths, including logarithmic stretching.
    if (minval(x(ixO^S, 1) - half * block%ds(ixO^S, 1)) <= xprobmin1 * (one + 1.d-10)) &
      dtnew = courantpar * minval(block%ds(ixO^S, 1)) / &
      wind_signal
    ! Land on phase boundaries instead of stepping across the wind switch.
    tolerance=100.d0*epsilon(one)*max(one,abs(global_time))
    do phase=1,nages-1
      phase_end_code=ages(phase)*const_years/unit_time
      if(phase_end_code>global_time+tolerance) dtnew=min(dtnew,phase_end_code-global_time)
    enddo
  end subroutine injection_dt

  subroutine pressure_for_amr(ixI^L, ixO^L, iflag, w, x, var)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L, iflag
    double precision, intent(in) :: w(ixI^S, 1:nw), x(ixI^S, 1:ndim)
    double precision, intent(out) :: var(ixI^S)
    if (iflag /= nw + 1) call mpistop('Unexpected AMR variable')
    call hd_get_pthermal(w, x, ixI^L, ixO^L, var)
  end subroutine pressure_for_amr

  subroutine temperature_output(ixI^L, ixO^L, w, x, normconv)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L
    double precision, intent(in) :: x(ixI^S, 1:ndim)
    double precision :: w(ixI^S, nw + nwauxio), normconv(0:nw + nwauxio), p(ixI^S)
    call hd_get_pthermal(w(:, 1:nw), x, ixI^L, ixO^L, p)
    ! Export physical kelvin so checkpoint audits do not guess normalization.
    w(ixO^S, nw + 1) = p(ixO^S) / w(ixO^S, rho_) * unit_temperature
    normconv(nw + 1) = one
  end subroutine temperature_output

  subroutine temperature_name(varnames)
    character(len=*)::varnames
    varnames='temperature_K'
  end subroutine temperature_name

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

end module mod_usr
