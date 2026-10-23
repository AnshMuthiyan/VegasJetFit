! Purpose: Verify compiled wind values before, at, and after screenshot phase changes.
program phase_probe
  use mod_usr
  use mod_global_parameters, only: unit_time, const_years, const_msun
  implicit none
  double precision :: t(8), expected_rate(8), expected_speed(8), expected_temp(8)
  double precision :: rate,speed,temp
  integer :: k
  unit_time=3.0857d11
  call load_history()
  t=[0.d0,1.d6,4.3d6-1.d-3,4.3d6,4.5d6-1.d-3,4.5d6,4.77d6,5.d6]
  expected_rate=[1.d-6,1.d-6,1.d-6,5.d-5,5.d-5,1.d-5,1.d-5,1.d-5]
  expected_speed=[2000.d0,2000.d0,2000.d0,15.d0,15.d0,2000.d0,2000.d0,2000.d0]
  expected_temp=[10000.d0,10000.d0,10000.d0,1000.d0,1000.d0,10000.d0,10000.d0,10000.d0]
  do k=1,size(t)
    call phase_wind(t(k)*const_years/unit_time,rate,speed,temp)
    rate=rate*const_years/const_msun
    speed=speed/1.d5
    if(abs(rate/expected_rate(k)-1.d0)>1.d-12) stop 1
    if(abs(speed/expected_speed(k)-1.d0)>1.d-12) stop 2
    if(abs(temp/expected_temp(k)-1.d0)>1.d-12) stop 3
    write(*,'(A,4ES24.16)') 'PASS age[yr], Mdot[Msun/yr], v[km/s], T[K]: ',t(k),rate,speed,temp
  enddo
end program phase_probe
