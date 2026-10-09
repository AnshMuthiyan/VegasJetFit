module mod_usr
  use mod_hd

  implicit none

  double precision :: Mdot,vwind,Twind,rhoISM,vISM,TISM,Rstar,Rwind,Rtshock,&
     Tscale,Lscale, Mstar, Lstar
  double precision :: vwind_prev = -1.0d0 !Track previous wind velocity for change detection
  integer :: icase
  character(len=100) :: stellar_param_file = 'stellar_evolution.dat'
  logical :: use_stellar_evolution = .false.
  ! Optional .par override; -1 retains the selected case's ambient density.
  double precision :: rho_ism_cgs = -1.0d0
  double precision :: ism_temperature_k = -1.0d0
  ! Optional cooling cutoff in kelvin; -1 follows the ambient temperature.
  double precision :: cooling_temperature_k = -1.0d0
  double precision, allocatable :: wind_age(:), wind_mdot(:), wind_speed(:),&
      wind_temp(:)
  integer :: wind_entries = 0

contains

  !> Read this module's parameters from a file
  subroutine usr_params_read(files)
    character(len=*), intent(in) :: files(:)
    integer                      :: n

    namelist /usr_list/ icase, stellar_param_file, use_stellar_evolution,&
        rho_ism_cgs, ism_temperature_k, cooling_temperature_k

    do n = 1, size(files)
       open(unitpar, file=trim(files(n)), status="old")
       read(unitpar, usr_list, end=111)
111    close(unitpar)
    end do

  end subroutine usr_params_read

  !> Cache the stellar history once per MPI rank, not once per boundary call.
  subroutine load_stellar_history()
    use mod_global_parameters
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    integer :: iu, ios, count, row
    double precision :: age, log_mdot, speed, temp
    character(len=1024) :: line

    if (allocated(wind_age)) return
    open(newunit=iu, file=trim(stellar_param_file), status='old',&
        action='read', iostat=ios)
    if (ios /= 0) call mpistop('Cannot open stellar_param_file')
    count = 0
    do
      read(iu,'(A)',iostat=ios) line
      if (ios < 0) exit
      if (ios /= 0) call mpistop('Error reading stellar_param_file')
      line = adjustl(line)
      if (len_trim(line) == 0) cycle
      if (line(1:1) == '#' .or. line(1:1) == '!') cycle
      count = count + 1
    enddo
    if (count == 0) call mpistop('Empty stellar evolution table')
    allocate(wind_age(count), wind_mdot(count), wind_speed(count),&
        wind_temp(count))
    rewind(iu)
    row = 0
    do
      read(iu,'(A)',iostat=ios) line
      if (ios < 0) exit
      if (ios /= 0) call mpistop('Error reading stellar_param_file')
      line = adjustl(line)
      if (len_trim(line) == 0) cycle
      if (line(1:1) == '#' .or. line(1:1) == '!') cycle
      read(line,*,iostat=ios) age, log_mdot, speed, temp
      if (ios /= 0) call mpistop('Malformed stellar evolution row')
      if (.not.all(ieee_is_finite([age,log_mdot,speed,&
         temp]))) call mpistop('Nonfinite stellar evolution row')
      if (age < zero .or. speed <= zero .or. temp <= zero) call &
         mpistop('Invalid stellar age, wind speed or temperature')
      if (log_mdot <= log10(tiny(one)) .or. log_mdot >= &
         log10(huge(one)/const_msun*const_years)) call &
         mpistop('Stellar mass loss outside representable range')
      if (row > 0) then
        if (age < wind_age(row)) call mpistop(&
           'Stellar ages must be nondecreasing')
        ! Rounded duplicate ages: the last row at that age wins.
        if (age > wind_age(row)) row = row + 1
      else
        row = 1
      endif
      wind_age(row) = age
      wind_mdot(row) = 10.0d0**log_mdot * const_msun / const_years
      wind_speed(row) = speed * 1.0d5
      wind_temp(row) = temp
    enddo
    close(iu)
    wind_entries = row
    if (mype == 0) then
      write(*,*) 'Loaded stellar history: ', trim(stellar_param_file)
      write(*,*) 'Unique ages: ', wind_entries, ' range [yr]: ', wind_age(1),&
          wind_age(wind_entries)
    endif
  end subroutine load_stellar_history

  !> Interpolate linear mass-loss rate, speed and temperature at stellar age.
  subroutine read_stellar_parameters(current_time, found_params)
    use mod_global_parameters
    double precision, intent(in) :: current_time
    logical, intent(out) :: found_params
    double precision :: current_age_years, fraction
    integer :: lo, hi, mid

    call load_stellar_history()
    current_age_years = current_time * time_convert_factor / const_years
    if (current_age_years <= wind_age(1)) then
      lo = 1
      hi = 1
    else if (current_age_years >= wind_age(wind_entries)) then
      lo = wind_entries
      hi = lo
    else
      lo = 1
      hi = wind_entries
      do while (hi-lo > 1)
        mid = (lo+hi)/2
        if (wind_age(mid) <= current_age_years) then
          lo = mid
        else
          hi = mid
        endif
      enddo
    endif
    fraction = zero
    if (hi /= lo) fraction = (current_age_years-wind_age(lo))/(wind_age(hi)-&
       wind_age(lo))
    Mdot = wind_mdot(lo) + fraction*(wind_mdot(hi)-wind_mdot(lo))
    vwind = wind_speed(lo) + fraction*(wind_speed(hi)-wind_speed(lo))
    Twind = wind_temp(lo) + fraction*(wind_temp(hi)-wind_temp(lo))
    found_params = .true.
    ! Ambient conditions are initialized once in initglobaldata_usr.
    ! Retarded wind updates must not change the outer-boundary environment.
  end subroutine read_stellar_parameters

  !> Update wind parameters at retarded time for material reaching radius r.
  !! Solve t_ret = t - r / vwind(t_ret) by a few fixed-point iterations.
  subroutine read_retarded_stellar_parameters(current_time, radius_code,&
      found_params)
    use mod_global_parameters
    double precision, intent(in) :: current_time, radius_code
    logical, intent(out) :: found_params

    double precision :: retarded_time, propagation_time
    integer :: iter

    retarded_time = current_time
    found_params = .false.

    do iter = 1, 3
      call read_stellar_parameters(retarded_time, found_params)
      if (.not. found_params) return
      propagation_time = radius_code * length_convert_factor / max(vwind,&
          1.0d-99) / time_convert_factor
      retarded_time = max(zero, current_time - propagation_time)
    enddo

    call read_stellar_parameters(retarded_time, found_params)
  end subroutine read_retarded_stellar_parameters

  subroutine usr_init()
    use mod_global_parameters

    call usr_params_read(par_files)

    unit_length        = 3.0857D18
    unit_density       = 1.0d-25
    unit_velocity      = 1.0d7
    ! hd_activate derives consistent pressure, temperature, number-density
    ! and time units, including the configured composition.

    usr_set_parameters  => initglobaldata_usr
    usr_init_one_grid   => wind_init_one_grid
    usr_special_bc      => specialbound_usr
    usr_get_dt          => wind_boundary_dt
    usr_refine_grid     => specialrefine_grid
    ! The wind is injected only through the inner boundary. The legacy
    ! internal-source injector targets Rwind, which lies outside this tight
    ! termination-shock domain and would also overwrite retarded wind updates.
    usr_aux_output      => specialvar_output
    usr_add_aux_names   => specialvarnames_output
    usr_var_for_errest  => myvar_for_errest
    usr_print_log       => custom_print_log

    call set_coordinate_system("spherical")
    call hd_activate()


  end subroutine usr_init

  subroutine initglobaldata_usr()
    use mod_global_parameters
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    logical :: found

    hd_gamma=5.0d0/3.0d0

    ! Initialize conversions before evaluating the stellar history.
    ! Cooling and hydrodynamics must use the same physical units.
    length_convert_factor   = unit_length
    time_convert_factor     = unit_time
    w_convert_factor(rho_)  = unit_density
    w_convert_factor(mom(1))= unit_velocity
    w_convert_factor(p_)    = unit_pressure
    Tscale = 1.0d0 / unit_temperature
    Lscale = w_convert_factor(rho_)*time_convert_factor / &
       (mp_cgs*w_convert_factor(mom(1)))**2

    ! Set default parameters or read from file if enabled
    if (use_stellar_evolution) then
      ! Try to read initial parameters from file
      call read_stellar_parameters(zero, found)
      if (.not. found) then
        call mpistop('Failed to initialize wind from stellar evolution file')
      endif
    endif
    
    ! Set parameters based on case if not using evolution file
    if (.not. use_stellar_evolution) then
      select case( icase )
       case(1) ! Constant 2000 km/s, 1e-5 Msun/yr dense-cooling wind
         Mdot  = 1.0d-5*const_msun/const_years
         vwind = 2.0d8
         Twind = 1.0d4
         rhoISM= 1.6726d-20
         vISM  = 0.0d0
         TISM  = 5.0d1
         Rstar = 5.0d13
         ! this last one is dimensionless
         Rwind = 2.0d-1
         Rtshock = 1.0d0
       case(2)  ! RSG in cold medium
         Mdot  = 1.0d-4*const_msun/const_years
         vwind = 2.0d6
         Twind = 1.0d3
         rhoISM= (10.0d0)**(-23)
         vISM  = 5.0d6
         TISM  = 1.0d2
         Rstar = 5.0d13
         ! this last one is dimensionless
         Rwind = 2.0d-1
         Rtshock = 1.0d0
       case(3)  ! WR in cold medium
         Mdot  = 1.0d-5*const_msun/const_years
         vwind = 2.5d8
         Twind = 2.0d4
         rhoISM= (10.0d0)**(-23)
         vISM  = 5.0d6
         TISM  = 1.0d2
         Rstar = 5.0d13
         ! this last one is dimensionless
         Rwind = 2.0d-1
         Rtshock = 1.0d0
       case default
           call mpistop("This problem has not been defined")
      end select
    else
      ! ISM parameters for stellar evolution runs
      rhoISM= 1.6726d-20
      vISM  = 0.0d0
      TISM  = 5.0d1
      Rstar = 5.0d13
      Rwind = 2.0d-1
      Rtshock = 1.0d0
    endif


    ! Apply the .par ambient density after all case/evolution defaults.
    ! This shared value controls both initial ISM cells and the outer boundary.
    if (rho_ism_cgs /= -1.0d0) then
      if (.not.ieee_is_finite(rho_ism_cgs) .or. rho_ism_cgs <= zero) call &
         mpistop('rho_ism_cgs must be finite and positive (g cm^-3)')
      rhoISM = rho_ism_cgs
    endif
    if (ism_temperature_k /= -1.0d0) then
      if (.not.ieee_is_finite(ism_temperature_k) .or. ism_temperature_k <= &
         zero) call mpistop&
         ('ism_temperature_k must be finite and positive (K)')
      TISM = ism_temperature_k
    endif
    if (allocated(rc_fl)) then
      rc_fl%tlow = TISM / unit_temperature
      if (cooling_temperature_k /= -1.0d0) then
        if (.not.ieee_is_finite(cooling_temperature_k) .or. &
           cooling_temperature_k <= zero) call &
           mpistop('cooling_temperature_k must be finite and positive (K)')
        rc_fl%tlow = cooling_temperature_k / unit_temperature
      endif
      ! Honor Tfix from &rc_list instead of overriding it here.
    endif

    if(mype == 0) then
       write(*,'(A,ES24.16)') 'Ambient density [g cm^-3]: ', rhoISM
       write(*,'(A,ES24.16)') 'Ambient density [code]:   ',&
           rhoISM/unit_density
       write(*,'(A,ES24.16)') 'Ambient temperature [K]: ', TISM
       if (allocated(rc_fl)) write(*,'(A,ES24.16)') 'Cooling cutoff [K]: ',&
           rc_fl%tlow*unit_temperature
       if (allocated(rc_fl)) write(*,'(A,L1)') 'Cooling Tfix enabled: ',&
           rc_fl%Tfix
       write(*,1004) 'time_convert_factor:     ', time_convert_factor
       write(*,1004) 'length_convert_factor:   ', length_convert_factor
       write(*,1004) 'w_convert_factor(mom(1)):', w_convert_factor(mom(1))
       write(*,1004) 'w_convert_factor(rho_):  ', w_convert_factor(rho_)
       write(*,1004) 'w_convert_factor(p_):    ', w_convert_factor(p_)
       write(*,*)
       write(*,1004) 'accel                    ',&
            w_convert_factor(mom(1))*w_convert_factor(mom(&
          1))/length_convert_factor
       write(*,*)
       write(*,1002) 1.0d0/Tscale
       write(*,1003) Lscale
       write(*,*)
       write(*,*) 'Using stellar evolution file: ', use_stellar_evolution
       if (use_stellar_evolution) then
         write(*,*) 'Stellar parameter file: ', trim(stellar_param_file)
       endif
       write(*,'(A,3ES24.16)') 'Initial wind [Msun/yr, km/s, K]: ',&
           Mdot*const_years/const_msun, vwind/1.0d5, Twind
       write(*,*)
    endif

Rstar = Rstar / length_convert_factor

  if(mype==0) then
      print *, 'unit_density = ', unit_density
      print *, 'unit_pressure = ', unit_pressure
      print *, 'unit_velocity = ', unit_velocity
      print *, 'unit_time = ', unit_time
  end if

!   1002 format('Temperature unit: ', 1x1pe12.5)
1002 format('Temperature unit: ', 1x,1pe12.5)
1003 format('Luminosity scale: ', 1x,1pe12.5)
1004 format(a25,1x,1pe12.5)
  end subroutine initglobaldata_usr

  ! Initialize one grid
  subroutine wind_init_one_grid(ixGmin1,ixGmax1,ixmin1,ixmax1,w,x)
    use mod_global_parameters
    integer, intent(in) :: ixGmin1,ixGmax1, ixmin1,ixmax1
    double precision, intent(in) :: x(ixGmin1:ixGmax1,1:ndim)
    double precision, intent(inout) :: w(ixGmin1:ixGmax1,1:nw)
    
    ! Begin with undisturbed ISM everywhere in the computational domain.
    ! The stellar wind enters only through specialbound_usr at the inner face.
    ! No cavity, termination shock, or swept-up wall is imposed initially.
    w(ixmin1:ixmax1,rho_) = rhoISM/w_convert_factor(rho_)
    w(ixmin1:ixmax1,mom(1)) = zero
    w(ixmin1:ixmax1,p_) = w(ixmin1:ixmax1,rho_)*TISM*Tscale

    call check_injected_primitive(ixGmin1,ixGmax1,ixmin1,ixmax1,w)
    call hd_to_conserved(ixGmin1,ixGmax1,ixmin1,ixmax1,w,x)

  end subroutine wind_init_one_grid

  subroutine wind_boundary_dt(w,ixImin1,ixImax1,ixOmin1,ixOmax1,dtnew,dx1,x)
    use mod_global_parameters
    integer, intent(in) :: ixImin1,ixImax1, ixOmin1,ixOmax1
    double precision, intent(in) :: w(ixImin1:ixImax1,1:nw), dx1,&
        x(ixImin1:ixImax1,1:ndim)
    double precision, intent(inout) :: dtnew
    double precision :: wind_signal

    dtnew = bigdouble
    ! The stock CFL estimate excludes ghost cells. Initially all interior
    ! cells are cold ISM, but the inner ghost cells already contain fast wind.
    ! Include that injected wind's signal speed on the boundary-adjacent block.
    if (minval(x(ixOmin1:ixOmax1,1)) <= xprobmin1 + 0.51d0*dx1) then
      wind_signal = abs(vwind)/unit_velocity + &
         sqrt(hd_gamma*Twind/unit_temperature)
      dtnew = courantpar*dx1/wind_signal
    endif
  end subroutine wind_boundary_dt

  subroutine specialrefine_grid(igrid,level,ixGmin1,ixGmax1,ixmin1,ixmax1,qt,w,&
     x,refine,coarsen)
    ! Enforce additional refinement or coarsening
    ! One can use the coordinate info in x and/or time qt=t_n and w(t_n) values w.
    ! you must set consistent values for integers refine/coarsen:
    ! refine = -1 enforce to not refine
    ! refine =  0 doesn't enforce anything
    ! refine =  1 enforce refinement
    ! coarsen = -1 enforce to not coarsen
    ! coarsen =  0 doesn't enforce anything
    ! coarsen =  1 enforce coarsen
    integer, intent(in) :: igrid, level, ixGmin1,ixGmax1, ixmin1,ixmax1
    double precision, intent(in) :: qt, w(ixGmin1:ixGmax1,1:nw),&
        x(ixGmin1:ixGmax1,1:ndim)
    integer, intent(inout) :: refine, coarsen

    ! Let AMRVAC's automatic error estimator refine shocks/gradients. The old
    ! forced-refinement target was Rwind, which is now outside this tight domain.

  end subroutine specialrefine_grid

  subroutine specialbound_usr(qt,ixGmin1,ixGmax1,ixOmin1,ixOmax1,iB,w,x)
    use mod_global_parameters
    integer, intent(in) :: ixGmin1,ixGmax1, ixOmin1,ixOmax1, iB
    double precision, intent(in) :: qt, x(ixGmin1:ixGmax1,1:ndim)
    double precision, intent(inout) :: w(ixGmin1:ixGmax1,1:nw)
    logical :: found_params
    double precision :: boundary_radius

    select case(iB)
    case(1) !Inner radial boundary: stellar wind outflow entering the domain.
      if (use_stellar_evolution) then
        boundary_radius = max(minval(x(ixOmin1:ixOmax1,1)), tiny(1.0d0))
        call read_retarded_stellar_parameters(qt, boundary_radius,&
            found_params)
        if (.not. found_params .and. mype == 0) then
          write(*,*)&
              'Warning: Could not read retarded stellar parameters at time ',&
              qt
        endif
      endif
      w(ixOmin1:ixOmax1,rho_)   = Mdot/(4.0D0*dpi*vwind * (x(ixOmin1:ixOmax1,&
         1)*length_convert_factor)**2 ) / w_convert_factor(rho_)
      w(ixOmin1:ixOmax1,mom(1)) = vwind / w_convert_factor(mom(1))
      w(ixOmin1:ixOmax1,p_)     = w(ixOmin1:ixOmax1,rho_)*Twind*Tscale
      call check_injected_primitive(ixGmin1,ixGmax1,ixOmin1,ixOmax1,w)
      call hd_to_conserved(ixGmin1,ixGmax1,ixOmin1,ixOmax1,w,x)
    case(2)  ! Outer spherical boundary: undisturbed ambient gas.
      w(ixOmin1:ixOmax1,rho_)   = rhoISM/w_convert_factor(rho_)
      w(ixOmin1:ixOmax1,mom(1)) = zero  ! No velocity in ISM
      w(ixOmin1:ixOmax1,p_)     = w(ixOmin1:ixOmax1,rho_)*TISM*Tscale
      call check_injected_primitive(ixGmin1,ixGmax1,ixOmin1,ixOmax1,w)
      call hd_to_conserved(ixGmin1,ixGmax1,ixOmin1,ixOmax1,w,x)
    case default
      call mpistop("This boundary is not supposed to be special")
    end select

  end subroutine specialbound_usr

  subroutine check_injected_primitive(ixImin1,ixImax1,ixOmin1,ixOmax1,w)
    use mod_global_parameters
    use, intrinsic :: ieee_arithmetic, only: ieee_is_finite
    integer, intent(in) :: ixImin1,ixImax1, ixOmin1,ixOmax1
    double precision, intent(in) :: w(ixImin1:ixImax1,1:nw)

    ! hd_to_conserved does not validate primitives in the installed v3.1.
    ! Reject invalid injection states without adding mass or thermal energy.
    if (any(.not.ieee_is_finite(w(ixOmin1:ixOmax1,&
       1:nw)))) call mpistop('Nonfinite initial/boundary primitive state')
    if (any(w(ixOmin1:ixOmax1,rho_) < small_density)) call &
       mpistop('Initial/boundary density below numerical floor')
    if (any(w(ixOmin1:ixOmax1,p_) < small_pressure)) call &
       mpistop('Initial/boundary pressure below numerical floor')
  end subroutine check_injected_primitive

  subroutine special_source(qdt,ixImin1,ixImax1,ixOmin1,ixOmax1,iwmin,iwmax,&
     qtC,wCT,qt,w,x)
    use mod_global_parameters
    integer, intent(in) :: ixImin1,ixImax1, ixOmin1,ixOmax1, iwmin,iwmax
    double precision, intent(in) :: qdt, qtC, qt
    double precision, intent(in) :: x(ixImin1:ixImax1,1:ndim),&
        wCT(ixImin1:ixImax1,1:nw)
    double precision, intent(inout) :: w(ixImin1:ixImax1,1:nw)

    double precision :: rad(ixImin1:ixImax1)
    logical :: found_params

    ! Update stellar parameters from file if enabled
    if (use_stellar_evolution) then
      call read_stellar_parameters(qt, found_params)
      if (.not. found_params .and. mype == 0) then
        write(*,*) 'Warning: Could not read stellar parameters at time ', qt
      !else if (found_params .and. mype == 0) then
        ! Print current wind parameters every time they're updated
      !  write(*,'(A,F10.3,A,ES12.5,A,F8.1,A)') &
      !    'Wind injection at t=', qt, ' yr:', qt*time_convert_factor/const_years, ' Mdot=',
      !    Mdot*const_years/const_msun, ' Msun/yr, vwind=', vwind/1.0d5, ' km/s'
      endif
    endif

    ! use of special source as an internal boundary....

    ! In 1D Cartesian, x(ixO^S,1) is the distance coordinate
    rad(ixOmin1:ixOmax1) = x(ixOmin1:ixOmax1,1)

    where ( rad(ixOmin1:ixOmax1)< Rwind )
      w(ixOmin1:ixOmax1,rho_)  = Mdot/(4.0D0*dpi*vwind* &
         (rad(ixOmin1:ixOmax1)*length_convert_factor)**2 ) / &
         w_convert_factor(rho_)
      w(ixOmin1:ixOmax1,mom(1)) = (vwind /w_convert_factor(mom(1))) * &
         w(ixOmin1:ixOmax1,rho_) !Pure radial momentum
      w(ixOmin1:ixOmax1,e_)    = w(ixOmin1:ixOmax1,&
         rho_)*Twind*Tscale/(hd_gamma-one)+ half*(w(ixOmin1:ixOmax1,&
         mom(1))**2.0d0)/w(ixOmin1:ixOmax1,rho_)
    end where

  end subroutine special_source

  subroutine specialvar_output(ixImin1,ixImax1,ixOmin1,ixOmax1,w,x,normconv)

    integer, intent(in)                :: ixImin1,ixImax1,ixOmin1,ixOmax1
    double precision, intent(in)       :: x(ixImin1:ixImax1,1:ndim)
    double precision                   :: w(ixImin1:ixImax1,nw+nwauxio)
    double precision                   :: normconv(0:nw+nwauxio)

    double precision :: pth(ixImin1:ixImax1),wlocal(ixImin1:ixImax1,1:nw)

    wlocal(ixImin1:ixImax1,1:nw)=w(ixImin1:ixImax1,1:nw)
    call hd_get_pthermal(wlocal,x,ixImin1,ixImax1,ixOmin1,ixOmax1,pth)
    w(ixOmin1:ixOmax1,nw+1)=pth(ixOmin1:ixOmax1)/w(ixOmin1:ixOmax1,rho_)
  end subroutine specialvar_output

  subroutine specialvarnames_output(varnames)
    character(len=*) :: varnames

    varnames='Te'
  end subroutine specialvarnames_output

  subroutine myvar_for_errest(ixImin1,ixImax1,ixOmin1,ixOmax1,iflag,w,x,var)
      use mod_global_parameters
      integer, intent(in)           :: ixImin1,ixImax1,ixOmin1,ixOmax1,iflag
      double precision, intent(in)  :: w(ixImin1:ixImax1,1:nw),&
          x(ixImin1:ixImax1,1:ndim)
      double precision, intent(out) :: var(ixImin1:ixImax1)

      if (iflag /= nw+1) call mpistop('Unexpected AMR variable')
      ! The estimator receives conserved states: extract thermal pressure,
      ! rather than refining kinetic-energy or momentum gradients.
      call hd_get_pthermal(w,x,ixImin1,ixImax1,ixOmin1,ixOmax1,var)

  end subroutine myvar_for_errest

  subroutine custom_print_log()
    use mod_input_output, only: printlog_default
    use mod_global_parameters
    
    double precision :: mdot_msun_yr, vwind_km_s, current_age_years
    character(len=200) :: wind_line
    integer :: istatus(MPI_STATUS_SIZE)
    
    ! Call the default log printing first
    call printlog_default
    
    ! Add stellar wind parameters to the main log file every 5000 iterations
    if (mype == 0 .and. mod(it, 5000) == 0) then
      ! Convert to physical units for logging
      current_age_years = global_time * time_convert_factor / const_years
      mdot_msun_yr = Mdot * const_years / const_msun
      vwind_km_s = vwind / 1.0d5
      
      ! Format stellar wind parameters line for log file
      write(wind_line, '(A,I8,A,F8.1,A,ES10.3,A,F7.1,A,F8.0,A)') '# WIND[', it,&
          ']: t=', current_age_years, ' yr, Mdot=', mdot_msun_yr,&
          ' Msun/yr, v=', vwind_km_s, ' km/s, T=', Twind, ' K'
      
      ! Write to main log file
      call MPI_FILE_WRITE(log_fh, trim(wind_line) // new_line('a'),&
          len_trim(wind_line)+1, MPI_CHARACTER, istatus, ierrmpi)
    endif
  end subroutine custom_print_log

end module mod_usr
