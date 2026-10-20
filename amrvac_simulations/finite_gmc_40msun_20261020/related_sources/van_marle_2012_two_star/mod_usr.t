module mod_usr
  use mod_hd
  implicit none

  integer :: case_id = 0
  double precision, parameter :: pc_cm = 3.0857d18
  double precision, parameter :: injection_radius_pc = 1.5d0
  double precision, parameter :: sn_radius_pc = 0.75d0
  double precision, parameter :: ambient_rho_cgs = 10.0d0**(-22.5d0)
  double precision, parameter :: ambient_temp_k = 100.0d0

contains

  subroutine usr_params_read(files)
    use mod_global_parameters
    character(len=*), intent(in) :: files(:)
    integer :: n
    namelist /usr_list/ case_id

    do n = 1, size(files)
      open(unitpar, file=trim(files(n)), status='old')
      read(unitpar, usr_list, end=100)
100   close(unitpar)
    enddo
    if (case_id < 1 .or. case_id > 3) call mpistop('case_id must be 1, 2 or 3')
  end subroutine usr_params_read

  subroutine usr_init()
    use mod_global_parameters
    call usr_params_read(par_files)
    unit_length = pc_cm
    unit_density = 1.0d-25
    unit_velocity = 1.0d7
    usr_set_parameters => set_parameters
    usr_init_one_grid => wind_init_one_grid
    usr_source => inject_sources
    usr_refine_grid => refine_sources
    call set_coordinate_system('cylindrical_2D')
    call hd_activate()
  end subroutine usr_init

  subroutine set_parameters()
    hd_gamma = 5.0d0 / 3.0d0
  end subroutine set_parameters

  subroutine star_position(star, z_pc)
    integer, intent(in) :: star
    double precision, intent(out) :: z_pc
    z_pc = 0.0d0
    if (case_id == 3) then
      if (star == 40) z_pc = -8.1d0
      if (star == 25) z_pc = 8.1d0
    endif
  end subroutine star_position

  subroutine wind_at_age(star, age_myr, active, mdot_cgs, speed_cgs, temp_k)
    use mod_global_parameters
    integer, intent(in) :: star
    double precision, intent(in) :: age_myr
    logical, intent(out) :: active
    double precision, intent(out) :: mdot_cgs, speed_cgs, temp_k
    active = .true.
    if (star == 40) then
      if (age_myr < 4.3d0) then
        mdot_cgs = 1.0d-6 * const_msun / const_years
        speed_cgs = 2.0d8
        temp_k = 1.0d4
      else if (age_myr < 4.5d0) then
        mdot_cgs = 5.0d-5 * const_msun / const_years
        speed_cgs = 1.5d6
        temp_k = 1.0d3
      else if (age_myr < 4.77d0) then
        mdot_cgs = 1.0d-5 * const_msun / const_years
        speed_cgs = 2.0d8
        temp_k = 1.0d4
      else
        active = .false.
      endif
    else
      if (age_myr < 6.5d0) then
        mdot_cgs = 2.0d-7 * const_msun / const_years
        speed_cgs = 1.5d8
        temp_k = 1.0d4
      else if (age_myr < 7.0d0) then
        mdot_cgs = 1.0d-5 * const_msun / const_years
        speed_cgs = 1.5d6
        temp_k = 1.0d3
      else
        active = .false.
      endif
    endif
  end subroutine wind_at_age

  subroutine wind_init_one_grid(ixG^L, ix^L, w, x)
    use mod_global_parameters
    integer, intent(in) :: ixG^L, ix^L
    double precision, intent(in) :: x(ixG^S, 1:ndim)
    double precision, intent(inout) :: w(ixG^S, 1:nw)

    w(ix^S, rho_) = ambient_rho_cgs / unit_density
    w(ix^S, mom(1)) = zero
    w(ix^S, mom(2)) = zero
    w(ix^S, p_) = w(ix^S, rho_) * ambient_temp_k / unit_temperature
    if (case_id /= 2) call inject_wind(ixG^L, ix^L, w, x, 40, zero, .false.)
    if (case_id /= 1) call inject_wind(ixG^L, ix^L, w, x, 25, zero, .false.)
    call hd_to_conserved(ixG^L, ix^L, w, x)
  end subroutine wind_init_one_grid

  subroutine inject_wind(ixI^L, ixO^L, w, x, star, age_myr, conserved)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L, star
    double precision, intent(in) :: x(ixI^S, 1:ndim), age_myr
    double precision, intent(inout) :: w(ixI^S, 1:nw)
    logical, intent(in) :: conserved
    logical :: active
    double precision :: center, mdot, speed, temp, radius(ixI^S)
    double precision :: rho_code(ixI^S), vr_code(ixI^S), vz_code(ixI^S)
    double precision :: pressure_code(ixI^S), safe_radius(ixI^S)

    call wind_at_age(star, age_myr, active, mdot, speed, temp)
    if (.not. active) return
    call star_position(star, center)
    radius(ixO^S) = sqrt(x(ixO^S, 1)**2 + (x(ixO^S, 2)-center)**2)
    safe_radius(ixO^S) = max(radius(ixO^S), injection_radius_pc/4.0d0)
    rho_code(ixO^S) = mdot / (4.0d0*dpi*speed*(safe_radius(ixO^S)*pc_cm)**2) / unit_density
    vr_code(ixO^S) = speed / unit_velocity * x(ixO^S, 1) / safe_radius(ixO^S)
    vz_code(ixO^S) = speed / unit_velocity * (x(ixO^S, 2)-center) / safe_radius(ixO^S)
    pressure_code(ixO^S) = rho_code(ixO^S) * temp / unit_temperature
    if (conserved) then
      where (radius(ixO^S) < injection_radius_pc)
        w(ixO^S, rho_) = rho_code(ixO^S)
        w(ixO^S, mom(1)) = rho_code(ixO^S) * vr_code(ixO^S)
        w(ixO^S, mom(2)) = rho_code(ixO^S) * vz_code(ixO^S)
        w(ixO^S, e_) = pressure_code(ixO^S)/(hd_gamma-one) + &
          half*rho_code(ixO^S)*(vr_code(ixO^S)**2+vz_code(ixO^S)**2)
      endwhere
    else
      where (radius(ixO^S) < injection_radius_pc)
        w(ixO^S, rho_) = rho_code(ixO^S)
        w(ixO^S, mom(1)) = vr_code(ixO^S)
        w(ixO^S, mom(2)) = vz_code(ixO^S)
        w(ixO^S, p_) = pressure_code(ixO^S)
      endwhere
    endif
  end subroutine inject_wind

  subroutine inject_supernova(ixI^L, ixO^L, w, x, star)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L, star
    double precision, intent(in) :: x(ixI^S, 1:ndim)
    double precision, intent(inout) :: w(ixI^S, 1:nw)
    double precision :: center, ejecta_mass, volume, rho_code, energy_code
    double precision :: radius(ixI^S)

    call star_position(star, center)
    ejecta_mass = 10.0d0 * const_msun
    if (star == 25) ejecta_mass = 7.0d0 * const_msun
    volume = 4.0d0*dpi*(sn_radius_pc*pc_cm)**3/3.0d0
    rho_code = ejecta_mass/volume/unit_density
    energy_code = 1.0d51/volume/unit_pressure
    radius(ixO^S) = sqrt(x(ixO^S, 1)**2 + (x(ixO^S, 2)-center)**2)
    where (radius(ixO^S) < sn_radius_pc)
      w(ixO^S, rho_) = rho_code
      w(ixO^S, mom(1)) = zero
      w(ixO^S, mom(2)) = zero
      w(ixO^S, e_) = energy_code
    endwhere
  end subroutine inject_supernova

  subroutine inject_sources(qdt, ixI^L, ixO^L, iw^LIM, qtC, wCT, qt, w, x)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L, iw^LIM
    double precision, intent(in) :: qdt, qtC, qt
    double precision, intent(in) :: x(ixI^S, 1:ndim), wCT(ixI^S, 1:nw)
    double precision, intent(inout) :: w(ixI^S, 1:nw)
    double precision :: age_myr, sn40, sn25

    age_myr = qt*time_convert_factor/(1.0d6*const_years)
    if (case_id /= 2) call inject_wind(ixI^L, ixO^L, w, x, 40, age_myr, .true.)
    if (case_id /= 1) call inject_wind(ixI^L, ixO^L, w, x, 25, age_myr, .true.)
    sn40 = 4.77d6*const_years/time_convert_factor
    sn25 = 7.0d6*const_years/time_convert_factor
    if (case_id /= 2 .and. qt < sn40 .and. qt+qdt >= sn40) &
      call inject_supernova(ixI^L, ixO^L, w, x, 40)
    if (case_id /= 1 .and. qt < sn25 .and. qt+qdt >= sn25) &
      call inject_supernova(ixI^L, ixO^L, w, x, 25)
  end subroutine inject_sources

  subroutine refine_sources(igrid, level, ixG^L, ix^L, qt, w, x, refine, coarsen)
    use mod_global_parameters
    integer, intent(in) :: igrid, level, ixG^L, ix^L
    double precision, intent(in) :: qt, w(ixG^S, 1:nw), x(ixG^S, 1:ndim)
    integer, intent(inout) :: refine, coarsen
    double precision :: center, radius(ixG^S)
    integer :: star

    do star = 25, 40, 15
      if (star == 25 .and. case_id == 1) cycle
      if (star == 40 .and. case_id == 2) cycle
      call star_position(star, center)
      radius(ix^S) = sqrt(x(ix^S, 1)**2+(x(ix^S, 2)-center)**2)
      if (any(radius(ix^S) < 3.0d0)) then
        coarsen = -1
        if (level < refine_max_level) refine = 1
      endif
    enddo
  end subroutine refine_sources

end module mod_usr
