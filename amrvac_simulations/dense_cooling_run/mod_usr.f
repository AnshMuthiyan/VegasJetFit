module mod_usr
  use mod_hd

  implicit none

  double precision :: Mdot,vwind,Twind,rhoISM,vISM,TISM,Rstar,Rwind,Rtshock,&
     Tscale,Lscale, Mstar, Lstar
  double precision :: vwind_prev = -1.0d0 !Track previous wind velocity for change detection
  integer :: icase
  character(len=100) :: stellar_param_file = 'stellar_evolution.dat'
  logical :: use_stellar_evolution = .false.

contains

  !> Read this module's parameters from a file
  subroutine usr_params_read(files)
    character(len=*), intent(in) :: files(:)
    integer                      :: n

    namelist /usr_list/ icase, stellar_param_file, use_stellar_evolution

    do n = 1, size(files)
       open(unitpar, file=trim(files(n)), status="old")
       read(unitpar, usr_list, end=111)
111    close(unitpar)
    end do

  end subroutine usr_params_read

  !> Read stellar parameters from external file at given time
  subroutine read_stellar_parameters(current_time, found_params)
    use mod_global_parameters
    double precision, intent(in) :: current_time
    logical, intent(out) :: found_params
    double precision :: current_age_years

    found_params = .true.
    current_age_years = current_time * time_convert_factor / const_years

    if (current_age_years <= 3.4499d6) then
      ! Main Sequence
      Mdot = 3.51d-6 * const_msun / const_years
      vwind = 2.42d8
      Twind = 1.0d4
    else if (current_age_years <= 3.4796d6) then
      ! LBV
      Mdot = 4.71d-4 * const_msun / const_years
      vwind = 4.92d7
      Twind = 1.0d4
    else
      ! Wolf-Rayet
      Mdot = 6.41d-5 * const_msun / const_years
      vwind = 2.25d8
      Twind = 1.0d4
    endif

    ! Enforce constant ISM params in case called during init
    rhoISM= 1.6726d-20
    vISM  = 0.0d0
    TISM  = 5.0d1
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
    unit_temperature   = 1.0d7**2.0d0/ (kb_cgs/mp_cgs)
    unit_numberdensity = 10.0**(-25)/mp_cgs

    usr_set_parameters  => initglobaldata_usr
    usr_init_one_grid   => wind_init_one_grid
    usr_special_bc      => specialbound_usr
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
    logical :: found

    hd_gamma=5.0d0/3.0d0

    ! Set default parameters or read from file if enabled
    if (use_stellar_evolution) then
      ! Try to read initial parameters from file
      call read_stellar_parameters(zero, found)
      if (.not. found) then
        if (mype == 0) write(*,*) 'Warning: Using default case parameters'
        use_stellar_evolution = .false.
      endif
    endif
    
    ! Set parameters based on case if not using evolution file
    if (.not. use_stellar_evolution) then
      select case( icase )
       case(1) ! Custom 500k yr dense-cooling run
         Mdot  = 5.0d-5*const_msun/const_years
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
      rhoISM= (10.0d0)**(-23)
      vISM  = 5.0d6
      TISM  = 1.0d2
      Rstar = 5.0d13
      Rwind = 2.0d-1
      Rtshock = 1.0d0
    endif


    length_convert_factor    = unit_length
    w_convert_factor(rho_)   = 10.0**(-25)
    w_convert_factor(mom(1))  = 1.0d7
    ! In 1D, only one momentum component
    w_convert_factor(p_)      = w_convert_factor(rho_)*w_convert_factor(mom(&
       1))*w_convert_factor(mom(1))
    time_convert_factor       = length_convert_factor/w_convert_factor(mom(1))

    Tscale = (1.0D0/(w_convert_factor(mom(1))**2.0d0)) * kb_cgs/mp_cgs
    Lscale =  w_convert_factor(rho_)*time_convert_factor/((&
       mp_cgs*w_convert_factor(mom(1)))**2.0)

    if(mype == 0) then
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
    
    double precision :: rad(ixGmin1:ixGmax1)

    ! In 1D Cartesian, x(ix^S,1) is the distance coordinate
    rad(ixmin1:ixmax1) = x(ixmin1:ixmax1,1)

    where ( rad(ixmin1:ixmax1)>= Rtshock )
      w(ixmin1:ixmax1,rho_) = rhoISM/w_convert_factor(rho_)
      w(ixmin1:ixmax1,mom(1))  = zero  ! No radial velocity in ISM
      w(ixmin1:ixmax1,p_)   = w(ixmin1:ixmax1,rho_)*TISM*Tscale
    elsewhere
      w(ixmin1:ixmax1,rho_) = Mdot/(4.0D0*dpi*vwind * &
         (rad(ixmin1:ixmax1)*length_convert_factor)**2 ) / &
         w_convert_factor(rho_)
      w(ixmin1:ixmax1,mom(1))  = (vwind /w_convert_factor(mom(1))) !Pure radial velocity
      w(ixmin1:ixmax1,p_)     =  w(ixmin1:ixmax1,rho_)*Twind*Tscale
    end where

    call hd_to_conserved(ixGmin1,ixGmax1,ixmin1,ixmax1,w,x)

  end subroutine wind_init_one_grid

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
      call hd_to_conserved(ixGmin1,ixGmax1,ixOmin1,ixOmax1,w,x)
    case(2)  ! In 1D Cartesian: boundary 2 = outer (x=max): ISM inflow
      w(ixOmin1:ixOmax1,rho_)   = rhoISM/w_convert_factor(rho_)
      w(ixOmin1:ixOmax1,mom(1)) = zero  ! No velocity in ISM
      w(ixOmin1:ixOmax1,p_)     = w(ixOmin1:ixOmax1,rho_)*TISM*Tscale
      call hd_to_conserved(ixGmin1,ixGmax1,ixOmin1,ixOmax1,w,x)
    case default
      call mpistop("This boundary is not supposed to be special")
    end select

  end subroutine specialbound_usr

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

      if (iflag >nw+1)call mpistop(' iflag error')
      ! In 1D Cartesian, only one velocity component
      var(ixOmin1:ixOmax1) = abs(w(ixOmin1:ixOmax1,mom(1)))/w(ixOmin1:ixOmax1,&
         rho_)

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
