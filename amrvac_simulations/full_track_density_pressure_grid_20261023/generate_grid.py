from pathlib import Path
import csv,hashlib,json,re,math
out=Path(__file__).resolve().parent
root=out.parent
if (out/'builds').exists():
 raise SystemExit('Inputs are frozen after build; use a NEW dated campaign to change the grid.')
s=(root/'van_marle_25_finite_gmc_1d/mod_usr_25_track.t').read_text()
def replace(a,b):
 global s
 assert a in s,a[:100]
 s=s.replace(a,b,1)
replace('double precision :: atmosphere_outer_pc = -1.0d0','double precision :: external_pressure_over_k = -1.0d0\n  double precision :: atmosphere_outer_pc = -1.0d0')
replace('q_ms, q_rsg, q_wr, wind_phase_age_offset_myr, atmosphere_outer_pc','q_ms, q_rsg, q_wr, wind_phase_age_offset_myr, atmosphere_outer_pc, &\n      external_pressure_over_k')
replace("if (abs(star_mass_msun-25.0d0) > 1.0d-10) &\n      call mpistop('The 25-Msun track requires star_mass_msun=25')", "if (min(abs(star_mass_msun-25.0d0),abs(star_mass_msun-40.0d0)) > 1.0d-10) &\n      call mpistop('Full wind tracks require stellar mass 25 or 40 Msun')\n    if (external_pressure_over_k <= zero) &\n      call mpistop('Specify positive external P/k_B in K cm^-3')")
replace("call mpistop('No photoionization prescription is defined for this 25-Msun track')","call mpistop('Matched full-track grid has photoionization OFF for both masses')")
replace('    atm_p(atmosphere_nodes) = p_cgs/(unit_density*unit_velocity**2)', '    ! Independent boundary pressure; k_B is exact in cgs.\n    p_cgs = external_pressure_over_k*1.380649d-16\n    atm_p(atmosphere_nodes) = p_cgs/(unit_density*unit_velocity**2)\n    write(*,\'(A,2ES18.9)\') \' EXTERNAL_PRESSURE \', &\n      external_pressure_over_k,p_cgs')
# Repair literal quoting in the injected Fortran line.
s=s.replace("' EXTERNAL_PRESSURE \\, &", "' EXTERNAL_PRESSURE ', &")
a=s.index('  subroutine wind_at_time(');b=s.index('  end subroutine wind_at_time',a)+len('  end subroutine wind_at_time')
s=s[:a]+'''  subroutine wind_at_time(qt, mdot, speed, temp)
    use mod_global_parameters
    double precision, intent(in) :: qt
    double precision, intent(out) :: mdot, speed, temp
    double precision :: age_myr
    age_myr = wind_phase_age_offset_myr + &
      qt*(unit_length/unit_velocity)/(1.0d6*const_years)
    if (star_mass_msun < 30.0d0) then
      if (age_myr < 6.5d0) then
        mdot = 2.0d-7 * const_msun / const_years
        speed = 1.5d8
        temp = 1.0d4
      else if (age_myr <= 7.0d0+1.0d-9) then
        mdot = 1.0d-5 * const_msun / const_years
        speed = 1.5d6
        temp = 1.0d3
      else
        call mpistop('25-Msun pre-SN track ends at 7 Myr; no WR phase')
      endif
    else
      if (age_myr < 4.3d0) then
        mdot = 1.0d-6 * const_msun / const_years
        speed = 2.0d8
        temp = 1.0d4
      else if (age_myr < 4.5d0) then
        mdot = 5.0d-5 * const_msun / const_years
        speed = 1.5d6
        temp = 1.0d3
      else if (age_myr <= 4.77d0+1.0d-9) then
        mdot = 1.0d-5 * const_msun / const_years
        speed = 2.0d8
        temp = 1.0d4
      else
        call mpistop('40-Msun pre-SN track ends at 4.77 Myr')
      endif
    endif
  end subroutine wind_at_time'''+s[b:]
# Boundary density normalisation uses each ghost radius, preserving mdot.
# Save-only phase diagnostics, no extra hydro source or temperature prescription.
replace('double precision :: mdot, speed, temp, signal\n    dtnew', 'double precision :: mdot, speed, temp, signal, age_myr, next_phase\n    dtnew')
replace('      dtnew = courantpar*dx1/signal\n    endif\n  end subroutine wind_boundary_dt', '''      dtnew = courantpar*dx1/signal
      age_myr = wind_phase_age_offset_myr + &
        global_time*(unit_length/unit_velocity)/(1.0d6*const_years)
      next_phase = bigdouble
      if (star_mass_msun < 30.0d0) then
        if (age_myr < 6.5d0-1.0d-10) next_phase = 6.5d0
      else
        if (age_myr < 4.3d0-1.0d-10) then
          next_phase = 4.3d0
        else if (age_myr < 4.5d0-1.0d-10) then
          next_phase = 4.5d0
        endif
      endif
      if (next_phase < bigdouble) dtnew = min(dtnew, &
        (next_phase-age_myr)*(1.0d6*const_years)/(unit_length/unit_velocity))
    endif
  end subroutine wind_boundary_dt''')
replace('double precision :: ionfrac, neutral_fraction, trec, decay, t_equiv, ambient_rho',
        'double precision :: ionfrac, neutral_fraction, trec, decay, t_equiv, ambient_rho\n    double precision :: diag_mdot, diag_speed, diag_temp')
replace("(qt+dt)*(unit_length/unit_velocity)/(1.0d6*const_years),front_pc,ionized_atoms\n    endif",
        "(qt+dt)*(unit_length/unit_velocity)/(1.0d6*const_years),front_pc,ionized_atoms\n      if (wind_enabled) then\n        call wind_at_time(qt+dt,diag_mdot,diag_speed,diag_temp)\n        write(*,'(A,I10,3ES18.9)') ' TRACK ',iit, &\n          wind_phase_age_offset_myr + &\n          (qt+dt)*(unit_length/unit_velocity)/(1.0d6*const_years), &\n          diag_mdot*const_years/const_msun,diag_speed/1.0d5\n      endif\n    endif")
replace('logical :: atmosphere_ready = .false.', 'logical :: atmosphere_ready = .false.\n  integer :: logged_phase = -1')
replace('integer :: k, igrid, i\n', 'integer :: k, igrid, i, diag_phase\n')
old_diag = """      if (wind_enabled) then
        call wind_at_time(qt+dt,diag_mdot,diag_speed,diag_temp)
        write(*,'(A,I10,3ES18.9)') ' TRACK ',iit, &
          wind_phase_age_offset_myr + &
          (qt+dt)*(unit_length/unit_velocity)/(1.0d6*const_years), &
          diag_mdot*const_years/const_msun,diag_speed/1.0d5
      endif
    endif"""
new_diag = """    endif
    if (wind_enabled) then
      call wind_at_time(qt+dt,diag_mdot,diag_speed,diag_temp)
      diag_phase = 1
      if (diag_speed < 1.0d7) diag_phase = 2
      if (diag_speed > 1.0d7 .and. diag_mdot*const_years/const_msun > 5.0d-6) &
        diag_phase = 3
      if (mod(iit,1000)==0 .or. diag_phase /= logged_phase) then
        write(*,'(A,I10,3ES18.9)') ' TRACK ',iit, &
          wind_phase_age_offset_myr + &
          (qt+dt)*(unit_length/unit_velocity)/(1.0d6*const_years), &
          diag_mdot*const_years/const_msun,diag_speed/1.0d5
        logged_phase = diag_phase
      endif
    endif"""
replace(old_diag,new_diag)
# The boundary may switch from slow RSG to fast WR within RK substeps.
# Bound the injection CFL by the fastest speed in the complete track.
replace('signal = speed/unit_velocity+sqrt(hd_gamma*temp/unit_temperature)',
        'signal = max(speed,2.0d8)/unit_velocity+sqrt(hd_gamma*temp/unit_temperature)')
# AMRVAC passes nominal dx1 on a stretched grid: use local physical spacing.
replace('double precision :: mdot, speed, temp, signal, age_myr, next_phase',
        'double precision :: mdot, speed, temp, signal, age_myr, next_phase, local_dx')
replace('dtnew = courantpar*dx1/signal',
        'local_dx = min(dx1,x(ixOmin1+1,1)-x(ixOmin1,1))\n      dtnew = courantpar*local_dx/signal')
(out/'mod_usr.t').write_text(s)
base=(root/'van_marle_25_finite_gmc_1d/input_sets/static_pilots_20261020_v2/m25_n20000b1000_c20480f31_base.par').read_text()
cells=1024;inner=.001;outer=160.;width=.0003
lo=1.+1e-10;hi=1.1
for _ in range(120):
 q=(lo+hi)/2
 if width*math.expm1(cells*math.log(q))/(q-1)>outer-inner:hi=q
 else:lo=q
q=(lo+hi)/2
for key,val in {'domain_nx1':str(cells),'xprobmin1':f'{inner}d0','xprobmax1':f'{outer}d0','qstretch_baselevel(1)':f'{q:.17g}d0','q_ms':'0.0d0','q_rsg':'0.0d0','q_wr':'0.0d0','atmosphere_outer_pc':f'{outer}d0'}.items():
 base,n=re.subn(r'(?m)^(\s*'+re.escape(key)+r'\s*=)[^\n]*',r'\g<1> '+val,base);assert n==1,key
base=base.replace('! Finite 15-pc GMC with 2-pc massive core; no cooling or conduction.','! Full-lifetime 160-pc domain; explicit external pressure; 1024-cell survey grid.')
inputs=out/'inputs';inputs.mkdir(exist_ok=True)
rows=[]
hosts=['keohane1','keohane2','keohane3','keohane4','pauley404-01','pauley404-02']
for density in (3000,10000,30000):
 for pressure in (1000000,10000000,100000000,1000000000):
  for star in (25,40):
   case=f'm{star}_n{density}_pk{pressure}'
   b=base
   for key,val in {'n_ref_cm3':f'{density}.0d0','star_mass_msun':f'{star}.0d0'}.items():
    b,n=re.subn(r'(?m)^(\s*'+key+r'\s*=)[^\n]*',r'\g<1> '+val,b);assert n==1
   b=b.rsplit('/',1)[0]+f'  external_pressure_over_k = {pressure}.0d0\n/\n'
   (inputs/f'{case}_base.par').write_text(b)
   end=7. if star==25 else 4.77
   def stage(tag,age,wind,save):
    return f'''&filelist
 base_filename = '{case}_{tag}'
 saveprim = .true.
 autoconvert = .true.
 convert_type = 'vtuBmpi'
/
&savelist
 dtsave_dat = {save*102.20121568819214:.17e}
/
&stoplist
 time_max = {age*102.20121568819214:.17e}
 final_dt_reduction = .true.
 dtmin = 1.0d-12
/
&hd_list
 hd_gravity = .true.
/
&usr_list
 wind_enabled = {'.true.' if wind else '.false.'}
 ionization_enabled = .false.
 cloud_gravity_enabled = .true.
 wind_phase_age_offset_myr = 0.0d0
/
'''
   (inputs/f'{case}_static.par').write_text(stage('static',.01,False,.01))
   (inputs/f'{case}_full.par').write_text(stage('full',end,True,.1))
   (inputs/f'{case}_smoke.par').write_text(stage('smoke',.0001,True,.0001))
   central=density*26**.9
   row={'case':case,'host':hosts[len(rows)%len(hosts)],'star_mass_msun':star,'n_ref_cm3_at_1pc':density,'central_untapered_nh_cm3':central,'external_pressure_over_k_K_cm3':pressure,'endpoint_myr':end,'expected_vtus':71 if star==25 else 49,'cells':cells,'inner_pc':inner,'outer_pc':outer,'first_width_pc':width,'base_file':f'{case}_base.par','static_file':f'{case}_static.par','full_file':f'{case}_full.par','smoke_file':f'{case}_smoke.par','guard_seconds':2592000}
   for tag in ('base','static','full','smoke'):row[f'{tag}_sha256']=hashlib.sha256((inputs/row[f'{tag}_file']).read_bytes()).hexdigest()
   rows.append(row)
with (out/'manifest.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(out/'design.json').write_text(json.dumps({'source_parent':'van_marle_25_finite_gmc_1d/mod_usr_25_track.t','source_sha256':hashlib.sha256(s.encode()).hexdigest(),'count':24,'cells':cells,'first_width_pc':width,'qstretch':q,'outer_pc':outer,'pressure_is_independent':True,'ionization':False,'cooling':False,'conduction':False,'gravity':'fixed initial star+cloud mass field; not evolving self-gravity','support_kms':.72,'n_gmc_cm3':1000,'n_ext_cm3':10,'gmc_pc':15,'r_flat_pc':.2,'cloud_pc':2,'edge_width_pc':.5},indent=2)+'\n')
print('Generated distinct 24-model grid and 96 input files; qstretch=',q)
