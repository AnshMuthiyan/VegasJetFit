module mod_usr
  use mod_hd
  implicit none

  double precision, parameter :: pc_cm = 3.0857d18
  double precision :: ambient_rho_cgs = -1.0d0
  double precision, parameter :: ambient_temp_k = 100.0d0

contains

  subroutine usr_params_read(files)
    use mod_global_parameters
    character(len=*), intent(in) :: files(:)
    integer :: n
    namelist /usr_list/ ambient_rho_cgs

    do n = 1, size(files)
      open(unitpar, file=trim(files(n)), status='old')
      read(unitpar, usr_list, end=100)
100   close(unitpar)
    enddo
    if (ambient_rho_cgs <= zero) call mpistop('ambient_rho_cgs must be positive')
  end subroutine usr_params_read

  subroutine usr_init()
    use mod_global_parameters
    call usr_params_read(par_files)
    unit_length = pc_cm
    unit_density = 1.0d-25
    unit_velocity = 1.0d7
    usr_set_parameters => set_parameters
    usr_init_one_grid => init_grid
    usr_special_bc => wind_boundary
    usr_get_dt => wind_boundary_dt
    call set_coordinate_system('spherical')
    call hd_activate()
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

    w(ix^S, rho_) = ambient_rho_cgs / unit_density
    w(ix^S, mom(1)) = zero
    w(ix^S, p_) = w(ix^S, rho_) * ambient_temp_k / unit_temperature
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
      w(ixO^S, rho_) = mdot / (4.0d0*dpi*speed*(x(ixO^S, 1)*pc_cm)**2) / unit_density
      w(ixO^S, mom(1)) = speed / unit_velocity
      w(ixO^S, p_) = w(ixO^S, rho_) * temp / unit_temperature
    case(2)
      w(ixO^S, rho_) = ambient_rho_cgs / unit_density
      w(ixO^S, mom(1)) = zero
      w(ixO^S, p_) = w(ixO^S, rho_) * ambient_temp_k / unit_temperature
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
