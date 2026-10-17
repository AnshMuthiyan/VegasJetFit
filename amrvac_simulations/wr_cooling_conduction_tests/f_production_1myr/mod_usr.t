! Purpose: Isolated constant WR-like wind bubble tests with a 100 K ambient
! medium, exact radiative cooling, Tfix, and saturated thermal conduction.
! All density conversions refer to TOTAL particles under the configured EOS.
module mod_usr
  use mod_hd
  implicit none
  double precision :: ambient_particles_cm3=1.0d4, ambient_temperature_k=100.d0
  double precision :: wind_mdot_msunyr=1.0d-5, wind_velocity_kms=2000.d0
  double precision :: wind_temperature_k=1.0d4
  double precision :: ambient_rho, mdot_cgs, wind_speed
contains
  subroutine usr_init()
    use mod_global_parameters
    integer :: n
    namelist /usr_list/ ambient_particles_cm3, ambient_temperature_k, &
      wind_mdot_msunyr, wind_velocity_kms, wind_temperature_k
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
  end subroutine usr_init

  subroutine set_parameters()
    use mod_global_parameters
    if(ambient_particles_cm3<=zero.or.ambient_temperature_k<=zero.or. &
      wind_mdot_msunyr<=zero.or.wind_velocity_kms<=zero.or. &
      wind_temperature_k<ambient_temperature_k) call mpistop('Invalid wind/ambient parameters')
    ! mu=(1+4a)/(1+Hion+a*(1+Heion*(1+Heion2))). For the inherited
    ! fully ionized H/He EOS (a=0.1), mu=1.4/2.3. This defines n_total.
    ambient_rho=ambient_particles_cm3*mp_cgs*(1.d0+4.d0*He_abundance)/ &
      (1.d0+H_ion_fr+He_abundance*(1.d0+He_ion_fr*(1.d0+He_ion_fr2)))
    mdot_cgs=wind_mdot_msunyr*const_msun/const_years
    wind_speed=wind_velocity_kms*1.d5
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
      write(*,'(A,3ES24.16)') 'CONSTANT wind [Msun/yr, km/s, K]: ', &
        wind_mdot_msunyr,wind_velocity_kms,wind_temperature_k
      write(*,'(A,ES24.16)') 'Temperature unit [K]: ',unit_temperature
      write(*,'(A,ES24.16)') 'Time unit [seconds]: ',unit_time
      if(allocated(rc_fl)) write(*,'(A,L1)') 'Cooling Tfix enabled: ',rc_fl%Tfix
    endif
  end subroutine set_parameters

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
    select case(iB)
    case(1)
      ! Exclude grids whose ghost cells cross the spherical origin.
      if (any(x(ixO^S, 1) <= zero)) call mpistop('Wind ghost radius <= 0: use stretching or larger xmin')
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
    dtnew = bigdouble
    ! Include the fast injected wind before the first interior CFL estimate.
    ! block%ds holds physical cell widths, including logarithmic stretching.
    if (minval(x(ixO^S, 1) - half * block%ds(ixO^S, 1)) <= xprobmin1 * (one + 1.d-10)) &
      dtnew = courantpar * minval(block%ds(ixO^S, 1)) / &
      (wind_speed / unit_velocity + sqrt(hd_gamma * wind_temperature_k / unit_temperature))
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
end module mod_usr
