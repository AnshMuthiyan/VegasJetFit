import os
import glob

grb_dirs = glob.glob('jetfit/resources/grbs/*')
for grb_dir in grb_dirs:
    if not os.path.isdir(grb_dir): continue
    
    old_toml_path = os.path.join(grb_dir, 'parameters.toml')
    if not os.path.exists(old_toml_path): continue
    
    with open(old_toml_path, 'r') as f:
        lines = f.readlines()
        
    new_lines = []
    skip_mode = False
    for line in lines:
        if line.startswith('name ='):
            if 'FireballModel' in line or 'powerlaw' in line or 'Model' in line:
                new_lines.append(line.replace(line.split('=')[1].strip(), "'SpheroidShellVegasModel'"))
                continue
                
        # Skip old density parameters
        if line.startswith('name  = "n017"') or line.startswith('name  = "k"') or line.startswith('name  = "A_star"'):
            skip_mode = True
        
        # When we hit another parameter, stop skipping
        if skip_mode and line.startswith('name  = "') and not (line.startswith('name  = "n017"') or line.startswith('name  = "k"') or line.startswith('name  = "A_star"')):
            skip_mode = False
            
        if not skip_mode:
            new_lines.append(line)
            
    # Now append the new Spheroid parameters
    new_params = """
#-------------- MODEL --------------
#------------- R_pole --------------
[[model]]
name  = "R_pole"
scale = "log"

[model.prior]
    type  = "uniform"
    lower = 16.5
    upper = 19.5
    initial_guess = 18.0
    initial_sigma = 0.5

#-------------- MODEL --------------
#------------- n_ism ---------------
[[model]]
name  = "n_ism"
scale = "log"

[model.prior]
    type  = "uniform"
    lower = -5.0
    upper = 3.0
    initial_guess = 0.0
    initial_sigma = 1.0

#-------------- MODEL --------------
#--------------- eps ---------------
[[model]]
name  = "eps"
scale = "linear"

[model.prior]
    type  = "uniform"
    lower = 0.001
    upper = 0.5
    initial_guess = 0.1
    initial_sigma = 0.05

#-------------- MODEL --------------
#---------------- q ----------------
[[model]]
name  = "q"
scale = "log"

[model.prior]
    type  = "uniform"
    lower = -1.0
    upper = 1.0
    initial_guess = 0.0
    initial_sigma = 0.2

#-------------- MODEL --------------
#------------- n_cav ---------------
[[model]]
name  = "n_cav"
scale = "log"
value = -2.0
"""
    # Find insertion point: usually before CALIBRATION or Rv Milky Way
    insert_idx = len(new_lines)
    for i, l in enumerate(new_lines):
        if 'rv_milky_way' in l or 'CALIBRATION' in l or 'ebv_' in l:
            insert_idx = i - 3
            break
            
    new_lines.insert(max(0, insert_idx), new_params)
    
    new_toml_path = os.path.join(grb_dir, 'parameters_spheroid.toml')
    with open(new_toml_path, 'w') as f:
        f.writelines(new_lines)
    print(f'Created {new_toml_path}')
