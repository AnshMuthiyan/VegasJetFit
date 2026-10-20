module mod_usr
  use mod_hd
  implicit none

  double precision, parameter :: pc_cm = 3.085677581d18
  double precision, parameter :: proton_g = 1.6726219d-24
  double precision, parameter :: alpha_b = 2.6d-13
  double precision, parameter :: temp_ion_k = 1.0d4
  double precision, parameter :: mass_per_h = 1.4d0 * proton_g
  double precision, parameter :: grav_cgs = 6.67430d-8
  integer, parameter :: atmosphere_nodes = 16385
  logical :: wind_enabled = .true.
  logical :: ionization_enabled = .true.
  logical :: cloud_gravity_enabled = .true.
  logical :: finite_gmc_enabled = .false.
  double precision :: n_ref_cm3 = 3.0d2
  double precision :: r_flat_pc = 0.2d0
  double precision :: slope_p = 1.8d0
  double precision :: cloud_pc = 2.0d0
  double precision :: edge_width_pc = 0.2d0
  double precision :: n_bg_cm3 = 10.0d0
  double precision :: n_ext_cm3 = 10.0d0
  double precision :: gmc_pc = 15.0d0
  double precision :: gmc_edge_width_pc = 1.0d0
  double precision :: star_mass_msun = 40.0d0
  double precision :: support_kms = 0.72d0
  double precision :: q_ms = 2.0d49
  double precision :: q_rsg = 0.0d0
  double precision :: q_wr = 2.0d49
  double precision :: wind_phase_age_offset_myr = 0.0d0
  double precision :: atmosphere_outer_pc = -1.0d0
  double precision :: front_pc = 0.0d0
  double precision :: ionized_atoms = 0.0d0
  logical :: front_initialized = .false.
  logical :: map_ready = .false.
  integer, allocatable :: map_grid(:), map_cell(:)
  double precision, allocatable :: map_lo(:), map_hi(:)
  double precision :: atm_r(atmosphere_nodes), atm_p(atmosphere_nodes)
  double precision :: atm_g(atmosphere_nodes), atm_m(atmosphere_nodes)
  logical :: atmosphere_ready = .false.

contains

  subroutine read_case(files)
    use mod_global_parameters
    character(len=*), intent(in) :: files(:)
    integer :: n
    namelist /usr_list/ wind_enabled, ionization_enabled, &
      cloud_gravity_enabled, n_ref_cm3, r_flat_pc, slope_p, cloud_pc, &
      edge_width_pc, n_bg_cm3, finite_gmc_enabled, n_ext_cm3, &
      gmc_pc, gmc_edge_width_pc, star_mass_msun, support_kms, &
      q_ms, q_rsg, q_wr, wind_phase_age_offset_myr, atmosphere_outer_pc

    do n = 1, size(files)
      open(unitpar, file=trim(files(n)), status='old')
      read(unitpar, usr_list, end=100)
100   close(unitpar)
    enddo
    if (min(n_ref_cm3,r_flat_pc,slope_p,cloud_pc,edge_width_pc, &
      n_bg_cm3,n_ext_cm3,gmc_pc,gmc_edge_width_pc,support_kms) <= zero) &
      call mpistop('Cloud parameters must be positive')
    if (r_flat_pc >= cloud_pc .or. n_ref_cm3 <= n_bg_cm3 .or. &
      star_mass_msun < zero .or. min(q_ms,q_rsg,q_wr) < zero .or. &
      wind_phase_age_offset_myr < zero) &
      call mpistop('Invalid cloud, stellar mass or photon rate')
    if (finite_gmc_enabled .and. (n_ref_cm3 <= n_bg_cm3 .or. &
      n_bg_cm3 <= n_ext_cm3 .or. cloud_pc >= gmc_pc)) &
      call mpistop('Invalid finite-GMC hierarchy')
    if (atmosphere_outer_pc /= -1.0d0 .and. atmosphere_outer_pc < xprobmax1) &
      call mpistop('Atmosphere outer radius must cover the evolved domain')
  end subroutine read_case

  subroutine usr_init()
    use mod_global_parameters
    call read_case(par_files)
    if (npe /= 1) call mpistop('Evolving 1D photon sweep is serial only')
    unit_length = pc_cm
    unit_density = 1.0d-25
    unit_velocity = 1.0d7
    usr_set_parameters => set_parameters
    usr_init_one_grid => init_grid
    usr_special_bc => wind_boundary
    usr_get_dt => wind_boundary_dt
    usr_gravity => cloud_mass_gravity
    usr_process_adv_global => update_front_and_thermal_state
    call set_coordinate_system('spherical')
    call hd_activate()
  end subroutine usr_init

  subroutine set_parameters()
    hd_gamma = 5.0d0 / 3.0d0
  end subroutine set_parameters

  double precision function profile_nh(r)
    double precision, intent(in) :: r
    double precision :: core, taper, ambient
    core = n_ref_cm3*((1.0d0+(1.0d0/r_flat_pc)**2)/ &
      (1.0d0+(r/r_flat_pc)**2))**(half*slope_p)
    taper = half*(one-tanh((r-cloud_pc)/edge_width_pc))
    ambient = n_bg_cm3
    if (finite_gmc_enabled) ambient = n_ext_cm3 + &
      (n_bg_cm3-n_ext_cm3)*half*(one-tanh((r-gmc_pc)/gmc_edge_width_pc))
    profile_nh = ambient+max(zero,core-ambient)*taper
  end function profile_nh

  subroutine build_atmosphere()
    use mod_global_parameters
    integer :: i
    double precision :: dlnr, dr_cm, rmid, excess, rho, gmid
    double precision :: mass_g, p_cgs, outer_r

    outer_r = xprobmax1
    ! Keep the full-cloud pressure anchor when evolving only the inner domain.
    if (atmosphere_outer_pc > zero) outer_r = atmosphere_outer_pc
    dlnr = log(outer_r/xprobmin1)/dble(atmosphere_nodes-1)
    do i = 1, atmosphere_nodes
      atm_r(i) = xprobmin1*exp(dble(i-1)*dlnr)
    enddo
    atm_r(atmosphere_nodes) = outer_r
    mass_g = star_mass_msun*const_msun
    atm_m(1) = mass_g
    do i = 2, atmosphere_nodes
      rmid = half*(atm_r(i)+atm_r(i-1))
      dr_cm = (atm_r(i)-atm_r(i-1))*pc_cm
      excess = max(zero,profile_nh(rmid)-n_bg_cm3)*mass_per_h
      if (finite_gmc_enabled) excess = profile_nh(rmid)*mass_per_h
      mass_g = mass_g+4.0d0*dpi*(rmid*pc_cm)**2*excess*dr_cm
      atm_m(i) = mass_g
    enddo
    do i = 1, atmosphere_nodes
      atm_g(i) = -grav_cgs*atm_m(i)/(atm_r(i)*pc_cm)**2 * &
        (unit_length/unit_velocity**2)
    enddo
    p_cgs = n_bg_cm3*mass_per_h*(support_kms*1.0d5)**2
    if (finite_gmc_enabled) &
      p_cgs = n_ext_cm3*mass_per_h*(support_kms*1.0d5)**2
    atm_p(atmosphere_nodes) = p_cgs/(unit_density*unit_velocity**2)
    do i = atmosphere_nodes-1, 1, -1
      rmid = half*(atm_r(i)+atm_r(i+1))
      rho = profile_nh(rmid)*mass_per_h
      gmid = -grav_cgs*half*(atm_m(i)+atm_m(i+1))/(rmid*pc_cm)**2
      p_cgs = p_cgs-rho*gmid*(atm_r(i+1)-atm_r(i))*pc_cm
      atm_p(i) = p_cgs/(unit_density*unit_velocity**2)
    enddo
    atmosphere_ready = .true.
    write(*,'(A,4ES16.7)') ' CLOUD_MASS ',n_ref_cm3,slope_p, &
      atm_m(atmosphere_nodes)/const_msun,atm_p(1)
  end subroutine build_atmosphere

  double precision function table_value(r, values)
    use mod_global_parameters
    double precision, intent(in) :: r, values(atmosphere_nodes)
    integer :: low, high, mid
    double precision :: fraction
    if (r <= atm_r(1)) then
      table_value = values(1)
      return
    endif
    if (r >= atm_r(atmosphere_nodes)) then
      table_value = values(atmosphere_nodes)
      return
    endif
    low = 1
    high = atmosphere_nodes
    do while (high-low > 1)
      mid = (low+high)/2
      if (atm_r(mid) <= r) then
        low = mid
      else
        high = mid
      endif
    enddo
    fraction = (r-atm_r(low))/(atm_r(high)-atm_r(low))
    table_value = values(low)+fraction*(values(high)-values(low))
  end function table_value

  double precision function pressure_code(r)
    double precision, intent(in) :: r
    pressure_code = table_value(r,atm_p)
  end function pressure_code

  double precision function support_code()
    use mod_global_parameters
    support_code = support_kms * 1.0d5 / unit_velocity
  end function support_code

  double precision function photons(qt)
    use mod_global_parameters
    double precision, intent(in) :: qt
    double precision :: age_myr
    age_myr = wind_phase_age_offset_myr + &
      qt*(unit_length/unit_velocity)/(1.0d6*const_years)
    if (age_myr < 4.3d0) then
      photons = q_ms
    else if (age_myr < 4.5d0) then
      photons = q_rsg
    else
      photons = q_wr
    endif
  end function photons

  subroutine initial_front()
    use mod_global_parameters
    integer :: i
    double precision :: dr, lo, hi, vol, nh, rec, used, f, q

    front_pc = xprobmin1
    ionized_atoms = zero
    if (.not.ionization_enabled) return
    q = photons(zero)
    if (q <= zero) return
    dr = (xprobmax1-xprobmin1)/100000.0d0
    used = zero
    do i = 1, 100000
      lo = xprobmin1 + (i-1)*dr
      hi = lo + dr
      nh = profile_nh(half*(lo+hi))
      vol = 4.0d0*dpi/3.0d0 * (hi**3-lo**3) * pc_cm**3
      rec = alpha_b*nh**2*vol
      if (used+rec >= q) then
        f = (q-used)/rec
        front_pc = (lo**3+f*(hi**3-lo**3))**(1.0d0/3.0d0)
        ionized_atoms = ionized_atoms + f*nh*vol
        return
      endif
      used = used+rec
      ionized_atoms = ionized_atoms+nh*vol
    enddo
    front_pc = xprobmax1
  end subroutine initial_front

  subroutine wind_at_time(qt, mdot, speed, temp)
    use mod_global_parameters
    double precision, intent(in) :: qt
    double precision, intent(out) :: mdot, speed, temp
    double precision :: age_myr
    age_myr = wind_phase_age_offset_myr + &
      qt*(unit_length/unit_velocity)/(1.0d6*const_years)
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
    double precision :: rho, pbase

    if (.not.front_initialized) then
      call build_atmosphere()
      call initial_front()
      front_initialized = .true.
    endif
    do i = ixmin1, ixmax1
      rho = profile_nh(x(i,1))*mass_per_h/unit_density
      pbase = pressure_code(x(i,1))
      w(i,rho_) = rho
      w(i,mom(1)) = zero
      w(i,p_) = pbase
      if (ionization_enabled .and. x(i,1) < front_pc) &
        w(i,p_) = max(pbase,rho*temp_ion_k/unit_temperature)
    enddo
    call hd_to_conserved(ixG^L, ix^L, w, x)
  end subroutine init_grid

  subroutine wind_boundary(qt, ixG^L, ixO^L, iB, w, x)
    use mod_global_parameters
    integer, intent(in) :: ixG^L, ixO^L, iB
    double precision, intent(in) :: qt, x(ixG^S, 1:ndim)
    double precision, intent(inout) :: w(ixG^S, 1:nw)
    double precision :: mdot, speed, temp
    integer :: i

    select case(iB)
    case(1)
      if (wind_enabled) then
        call wind_at_time(qt, mdot, speed, temp)
        w(ixO^S,rho_) = mdot/(4.0d0*dpi*speed*(x(ixO^S,1)*pc_cm)**2)/unit_density
        w(ixO^S,mom(1)) = speed/unit_velocity
        w(ixO^S,p_) = w(ixO^S,rho_)*temp/unit_temperature
      else
        do i = ixOmin1, ixOmax1
          w(i,rho_) = profile_nh(x(i,1))*mass_per_h/unit_density
          w(i,mom(1)) = zero
          w(i,p_) = pressure_code(x(i,1))
        enddo
      endif
    case(2)
      do i = ixOmin1, ixOmax1
        w(i,rho_) = profile_nh(x(i,1))*mass_per_h/unit_density
        w(i,mom(1)) = zero
        w(i,p_) = pressure_code(x(i,1))
      enddo
    case default
      call mpistop('Unexpected boundary')
    end select
    call hd_to_conserved(ixG^L, ixO^L, w, x)
  end subroutine wind_boundary

  subroutine wind_boundary_dt(w, ixI^L, ixO^L, dtnew, dx1, x)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L
    double precision, intent(in) :: w(ixI^S,1:nw), dx1, x(ixI^S,1:ndim)
    double precision, intent(inout) :: dtnew
    double precision :: mdot, speed, temp, signal
    dtnew = bigdouble
    if (wind_enabled .and. minval(x(ixO^S,1)) <= xprobmin1+0.51d0*dx1) then
      call wind_at_time(global_time,mdot,speed,temp)
      signal = speed/unit_velocity+sqrt(hd_gamma*temp/unit_temperature)
      dtnew = courantpar*dx1/signal
    endif
  end subroutine wind_boundary_dt

  subroutine cloud_mass_gravity(ixI^L,ixO^L,wCT,x,gravity_field)
    use mod_global_parameters
    integer, intent(in) :: ixI^L, ixO^L
    double precision, intent(in) :: x(ixI^S,1:ndim),wCT(ixI^S,1:nw)
    double precision, intent(out) :: gravity_field(ixI^S,ndim)
    integer :: i
    double precision :: r
    gravity_field(ixO^S,1) = zero
    if (.not.cloud_gravity_enabled) return
    do i = ixOmin1, ixOmax1
      r = x(i,1)
      gravity_field(i,1) = table_value(r,atm_g)
    enddo
  end subroutine cloud_mass_gravity

  subroutine build_cell_map()
    use mod_global_parameters
    integer :: iigrid, igrid, i, j, k, temp_grid, temp_cell
    double precision :: temp_lo, temp_hi

    allocate(map_grid(domain_nx1),map_cell(domain_nx1))
    allocate(map_lo(domain_nx1),map_hi(domain_nx1))
    k = 0
    do iigrid = 1, igridstail
      igrid = igrids(iigrid)
      do i = ixMlo1, ixMhi1
        k = k+1
        if (k > domain_nx1) call mpistop('Photon map contains too many cells')
        map_grid(k) = igrid
        map_cell(k) = i
        map_lo(k) = ps(igrid)%x(i,1)-half*ps(igrid)%dx(i,1)
        map_hi(k) = ps(igrid)%x(i,1)+half*ps(igrid)%dx(i,1)
      enddo
    enddo
    if (k /= domain_nx1) call mpistop('Photon map missing cells; AMR unsupported')
    do i = 2, k
      temp_grid = map_grid(i)
      temp_cell = map_cell(i)
      temp_lo = map_lo(i)
      temp_hi = map_hi(i)
      j = i-1
      do while (j >= 1)
        if (map_lo(j) <= temp_lo) exit
        map_grid(j+1) = map_grid(j)
        map_cell(j+1) = map_cell(j)
        map_lo(j+1) = map_lo(j)
        map_hi(j+1) = map_hi(j)
        j = j-1
      enddo
      map_grid(j+1) = temp_grid
      map_cell(j+1) = temp_cell
      map_lo(j+1) = temp_lo
      map_hi(j+1) = temp_hi
    enddo
    if (abs(map_lo(1)-xprobmin1)>1.0d-8 .or. &
        abs(map_hi(k)-xprobmax1)>1.0d-8) &
      call mpistop('Photon map does not span full radial domain')
    do i = 2, k
      if (abs(map_lo(i)-map_hi(i-1)) > 1.0d-8) &
        call mpistop('Photon map has gap or overlap')
    enddo
    map_ready = .true.
  end subroutine build_cell_map

  subroutine update_front_and_thermal_state(iit,qt)
    use mod_global_parameters
    integer, intent(in) :: iit
    double precision, intent(in) :: qt
    integer :: k, igrid, i
    double precision :: dt_s, available, nh, vol, demand, fraction, new_atoms
    double precision :: rlo, rhi, rho, mom1, kinetic, pold, pnew, pfloor
    double precision :: ionfrac, neutral_fraction, trec, decay, t_equiv, ambient_rho

    if (.not.map_ready) call build_cell_map()
    dt_s = dt*(unit_length/unit_velocity)
    if (ionization_enabled) then
      available = ionized_atoms+photons(qt)*dt_s
      new_atoms = zero
      front_pc = xprobmin1
      do k = 1, domain_nx1
        igrid = map_grid(k)
        i = map_cell(k)
        nh = ps(igrid)%w(i,rho_)*unit_density/mass_per_h
        rlo = map_lo(k)
        rhi = map_hi(k)
        vol = 4.0d0*dpi/3.0d0*(rhi**3-rlo**3)*pc_cm**3
        demand = nh*vol+dt_s*alpha_b*nh**2*vol
        if (available >= demand) then
          fraction = one
        else
          fraction = max(zero,available/demand)
        endif
        new_atoms = new_atoms+fraction*nh*vol
        front_pc = (rlo**3+fraction*(rhi**3-rlo**3))**(one/3.0d0)
        available = max(zero,available-fraction*demand)
        if (fraction < one) exit
      enddo
      ionized_atoms = new_atoms
    else
      front_pc = xprobmin1
      ionized_atoms = zero
    endif

    do k = 1, domain_nx1
      igrid = map_grid(k)
      i = map_cell(k)
      rlo = map_lo(k)
      rhi = map_hi(k)
      ionfrac = zero
      if (ionization_enabled) &
        ionfrac = max(zero,min(one,(front_pc**3-rlo**3)/(rhi**3-rlo**3)))
      rho = ps(igrid)%w(i,rho_)
      mom1 = ps(igrid)%w(i,mom(1))
      kinetic = half*mom1**2/rho
      pold = (ps(igrid)%w(i,e_)-kinetic)*(hd_gamma-one)
      ambient_rho = profile_nh(ps(igrid)%x(i,1))*mass_per_h
      pfloor = rho*max(support_code()**2, &
        pressure_code(ps(igrid)%x(i,1))*unit_density/ambient_rho)
      pfloor = max(pfloor,rho*ionfrac*temp_ion_k/unit_temperature)
      pnew = max(pold,pfloor)
      t_equiv = pold/rho*unit_temperature
      neutral_fraction = one-ionfrac
      if (neutral_fraction > zero .and. rho*unit_density > 0.1d0*ambient_rho &
          .and. t_equiv < 1.0d5) then
        nh = rho*unit_density/mass_per_h
        trec = one/(alpha_b*nh)
        decay = exp(-neutral_fraction*dt_s/trec)
        pnew = pfloor+(pnew-pfloor)*decay
      endif
      ps(igrid)%w(i,e_) = kinetic+pnew/(hd_gamma-one)
    enddo
    if (mod(iit,1000)==0) then
      write(*,'(A,I10,3ES17.8)') ' FRONT ',iit, &
        (qt+dt)*(unit_length/unit_velocity)/(1.0d6*const_years),front_pc,ionized_atoms
    endif
  end subroutine update_front_and_thermal_state

end module mod_usr
