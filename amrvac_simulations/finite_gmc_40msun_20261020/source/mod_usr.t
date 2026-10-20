module mod_usr
  use mod_hd
  implicit none

  double precision, parameter :: pc_cm = 3.085677581d18
  double precision, parameter :: proton_g = 1.6726219d-24
  double precision, parameter :: alpha_b = 2.6d-13
  double precision, parameter :: n_h = 1.0d3
  double precision, parameter :: q_h = 2.0d49
  double precision, parameter :: mu_hd = 1.4d0 / 2.3d0
  double precision, parameter :: mu_molecular = 2.33d0
  double precision, parameter :: ionized_temp_k = 1.0d4
  double precision, parameter :: molecular_temp_equiv_k = 20.0d0 * mu_hd / mu_molecular
  double precision, parameter :: ambient_rho_cgs = 1.4d0 * proton_g * n_h
  double precision :: stromgren_pc

contains

  subroutine usr_init()
    use mod_global_parameters
    unit_length = pc_cm
    unit_density = 1.0d-25
    unit_velocity = 1.0d7
    usr_set_parameters => set_parameters
    usr_init_one_grid => init_grid
    usr_special_bc => wind_boundary
    usr_get_dt => wind_boundary_dt
    call set_coordinate_system('spherical')
    call hd_activate()
    stromgren_pc = (3.0d0*q_h/(4.0d0*dpi*alpha_b*n_h**2))**(1.0d0/3.0d0)/pc_cm
  end subroutine usr_init

  subroutine set_parameters()
    hd_gamma = 5.0d0 / 3.0d0
  end subroutine set_parameters

  subroutine wind_at_time(qt, mdot, speed, temp)
    use mod_global_parameters
    double precision, intent(in) :: qt
    double precision, intent(out) :: mdot, speed, temp
    double precision :: age_myr

    age_myr = qt*time_convert_factor/(1.0d6*const_years)
    if (age_myr < 4.3d0) then
      mdot = 1.0d-6 * const_msun / const_years
      speed = 2.0d8
      temp = 1.0d4
    else if (age_myr < 4.5d0) then
      mdot = 5.0d-5 * const_msun / const_years
      speed = 1.5d6
      temp = 1.0d3
    else
      mdot = 1.0d-5 * const_msun / const_years
      speed = 2.0d8
      temp = 1.0d4
    endif
  end subroutine wind_at_time

  subroutine init_grid(ixG^L, ix^L, w, x)
    use mod_global_parameters
    integer, intent(in) :: ixG^L, ix^L
    double precision, intent(in) :: x(ixG^S, 1:ndim)
    double precision, intent(inout) :: w(ixG^S, 1:nw)
    integer :: i

    w(ix^S, rho_) = ambient_rho_cgs / unit_density
    w(ix^S, mom(1)) = zero
    do i = ixmin1, ixmax1
      if (x(i,1) < stromgren_pc) then
        w(i,p_) = w(i,rho_) * ionized_temp_k / unit_temperature
      else
        w(i,p_) = w(i,rho_) * molecular_temp_equiv_k / unit_temperature
      endif
    enddo
    call hd_to_conserved(ixG^L, ix^L, w, x)
  end subroutine init_grid

  subroutine wind_boundary(qt, ixG^L, ixO^L, iB, w, x)
    use mod_global_parameters
    integer, intent(in) :: ixG^L, ixO^L, iB
    double precision, intent(in) :: qt, x(ixG^S, 1:ndim)
    double precision, intent(inout) :: w(ixG^S, 1:nw)
    double precision :: mdot, speed, temp

    select case(iB)
    case(1)
      call wind_at_time(qt, mdot, speed, temp)
      w(ixO^S, rho_) = mdot / (4.0d0*dpi*speed*(x(ixO^S,1)*pc_cm)**2) / unit_density
      w(ixO^S, mom(1)) = speed / unit_velocity
      w(ixO^S, p_) = w(ixO^S, rho_) * temp / unit_temperature
    case(2)
      w(ixO^S, rho_) = ambient_rho_cgs / unit_density
      w(ixO^S, mom(1)) = zero
      w(ixO^S, p_) = w(ixO^S, rho_) * molecular_temp_equiv_k / unit_temperature
    case default
      call mpistop('Unexpected boundary')
    end select
    call hd_to_conserved(ixG^L, ixO^L, w, x)
  end subroutine wind_boundary

  subroutine wind_boundary_dt(w, ixI^L, ixO^L, dtnew, dx1, x)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L
    double precision, intent(in) :: w(ixI^S, 1:nw), dx1, x(ixI^S, 1:ndim)
    double precision, intent(inout) :: dtnew
    double precision :: mdot, speed, temp, signal

    dtnew = bigdouble
    if (minval(x(ixO^S, 1)) <= xprobmin1 + 0.51d0*dx1) then
      call wind_at_time(global_time, mdot, speed, temp)
      signal = speed/unit_velocity + sqrt(hd_gamma*temp/unit_temperature)
      dtnew = courantpar*dx1/signal
    endif
  end subroutine wind_boundary_dt

end module mod_usr
