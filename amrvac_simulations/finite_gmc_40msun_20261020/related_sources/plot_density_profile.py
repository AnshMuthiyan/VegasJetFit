#!/usr/bin/env python3
"""
Script to read AMRVAC VTU files and plot density vs radial distance.
For 1D spherical stellar wind simulations.

Usage:
    python plot_density_profile.py
    python plot_density_profile.py --files test0010.vtu test0020.vtu  # specific files
    python plot_density_profile.py --range 0 50 10                   # every 10th file from 0 to 50
"""

import numpy as np
import matplotlib.pyplot as plt
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import argparse
import glob
import os
import sys

def read_vtu_file(filename):
    """
    Read a VTU file and extract coordinates and density data.
    
    Returns:
        radius: 1D array of radial coordinates 
        density: 1D array of density values
        other_vars: dict of other variables (velocity, pressure, etc.)
    """
    # Read the VTU file
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(filename)
    reader.Update()
    
    # Get the data
    data = reader.GetOutput()
    
    # Extract points (coordinates)
    points = data.GetPoints()
    coords = vtk_to_numpy(points.GetData())
    
    # For 1D spherical, we want the radial coordinate (first column)
    radius = coords[:, 0]
    
    # Debug: Check both cell data and point data
    cell_data = data.GetCellData()
    point_data = data.GetPointData()
    
    print(f"=== Debug info for {filename} ===")
    print(f"Number of points: {data.GetNumberOfPoints()}")
    print(f"Number of cells: {data.GetNumberOfCells()}")
    print(f"Cell data arrays: {cell_data.GetNumberOfArrays()}")
    print(f"Point data arrays: {point_data.GetNumberOfArrays()}")
    
    # List all available arrays
    print("Cell data array names:", [cell_data.GetArrayName(i) for i in range(cell_data.GetNumberOfArrays())])
    print("Point data array names:", [point_data.GetArrayName(i) for i in range(point_data.GetNumberOfArrays())])
    
    # Try to find density data in either location
    density_array = None
    data_location = None
    
    # First try cell data
    for name in ['rho', 'density', 'Density']:
        density_array = cell_data.GetArray(name)
        if density_array is not None:
            data_location = 'cell'
            print(f"Found density '{name}' in cell data")
            break
    
    # If not found in cell data, try point data
    if density_array is None:
        for name in ['rho', 'density', 'Density']:
            density_array = point_data.GetArray(name)
            if density_array is not None:
                data_location = 'point'
                print(f"Found density '{name}' in point data")
                break
    
    if density_array is None:
        raise ValueError(f"No density array found in {filename}. Available arrays: "
                        f"Cell: {[cell_data.GetArrayName(i) for i in range(cell_data.GetNumberOfArrays())]}, "
                        f"Point: {[point_data.GetArrayName(i) for i in range(point_data.GetNumberOfArrays())]}")
    
    density = vtk_to_numpy(density_array)
    print(f"Density array shape: {density.shape}, data location: {data_location}")
    
    # Extract other variables from the same data location
    other_vars = {}
    
    # Choose the data container based on where we found density
    data_container = point_data if data_location == 'point' else cell_data
    
    # Velocity components
    for vel_name in ['v1', 'v2', 'v3', 'm1', 'm2', 'm3']:  # Try both velocity and momentum
        vel_array = data_container.GetArray(vel_name)
        if vel_array is not None:
            other_vars[vel_name] = vtk_to_numpy(vel_array)
            print(f"Found {vel_name} in {data_location} data")
    
    # Pressure
    for p_name in ['p', 'pressure', 'Pressure']:
        p_array = data_container.GetArray(p_name)
        if p_array is not None:
            other_vars['pressure'] = vtk_to_numpy(p_array)
            print(f"Found pressure '{p_name}' in {data_location} data")
            break
    
    # Temperature (if available as auxiliary variable)
    for temp_name in ['Te', 'T', 'temperature', 'Temperature']:
        temp_array = data_container.GetArray(temp_name)
        if temp_array is not None:
            other_vars['temperature'] = vtk_to_numpy(temp_array)
            print(f"Found temperature '{temp_name}' in {data_location} data")
            break
    
    print(f"Successfully extracted variables: {list(other_vars.keys())}")
    
    # Handle coordinate and data size mismatch
    print(f"Radius array shape: {radius.shape}")
    print(f"Density array shape: {density.shape}")
    
    # If data is on points but we have more points than data, or vice versa
    if len(density) != len(radius):
        if data_location == 'cell' and len(density) == data.GetNumberOfCells():
            # We have cell-centered data but point coordinates
            # For 1D, assume cells are centered between points
            if len(radius) > len(density):
                # Use cell centers: average adjacent points
                radius = (radius[:-1] + radius[1:]) / 2
                print(f"Adjusted radius to cell centers: {radius.shape}")
        elif data_location == 'point' and len(density) == len(radius):
            # Perfect match, no adjustment needed
            pass
        else:
            print(f"Warning: Size mismatch between coordinates ({len(radius)}) and data ({len(density)})")
            # Take minimum size to avoid errors
            min_size = min(len(radius), len(density))
            radius = radius[:min_size]
            density = density[:min_size]
            for key in other_vars:
                other_vars[key] = other_vars[key][:min_size]
            print(f"Truncated to size {min_size}")
    
    # Sort by radius for proper plotting
    sort_indices = np.argsort(radius)
    radius = radius[sort_indices]
    density = density[sort_indices]
    
    for key in other_vars:
        other_vars[key] = other_vars[key][sort_indices]
    
    print(f"Final data shape - radius: {radius.shape}, density: {density.shape}")
    print("=== End debug info ===\n")
    
    return radius, density, other_vars

def convert_units(radius, density, other_vars):
    """
    Data is already in physical units, so just return as-is.
    Optionally add unit labels for plotting.
    """
    # No conversion needed - data already in physical units
    radius_pc = radius  # Already in parsecs
    density_cgs = density  # Already in g/cm³
    
    converted_vars = {}
    if 'v1' in other_vars:
        converted_vars['velocity_km_s'] = other_vars['v1']  # Already in km/s
    
    if 'm1' in other_vars:
        # If we have momentum instead of velocity, assume it needs conversion
        # momentum / density = velocity
        converted_vars['velocity_km_s'] = other_vars['m1'] / density
    
    if 'pressure' in other_vars:
        converted_vars['pressure_cgs'] = other_vars['pressure']  # Already in dyne/cm²
    
    if 'temperature' in other_vars:
        converted_vars['temperature_K'] = other_vars['temperature']  # Already in K
    
    return radius_pc, density_cgs, converted_vars

def plot_density_profiles(files, output_dir='plots'):
    """
    Plot density profiles for multiple VTU files with 4 separate graphs.
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a figure with 2x2 subplot layout
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(files)))
    
    all_data = []  # Store data for all plots
    
    for i, filename in enumerate(files):
        try:
            print(f"Reading {filename}...")
            radius, density, other_vars = read_vtu_file(filename)
            
            # Convert to physical units
            radius_pc, density_cgs, converted_vars = convert_units(radius, density, other_vars)
            
            # Extract time step number from filename for legend
            basename = os.path.basename(filename)
            timestep = basename.split('test')[-1].split('.vtu')[0]
            
            # Store data for all plots
            all_data.append({
                'radius': radius_pc,
                'density': density_cgs,
                'velocity': converted_vars.get('velocity_km_s', None),
                'timestep': timestep,
                'color': colors[i]
            })
            
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            continue
    
    # Plot 1: Log-log density profile
    for data in all_data:
        ax1.loglog(data['radius'], data['density'], color=data['color'], 
                  label=f"t={data['timestep']}", linewidth=2)
    
    ax1.set_xlabel('Radius (pc)', fontsize=12)
    ax1.set_ylabel('Density (g/cm³)', fontsize=12)
    ax1.set_title('Density Profile (Log-Log)', fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Regular (linear) density profile
    for data in all_data:
        ax2.plot(data['radius'], data['density'], color=data['color'], 
                label=f"t={data['timestep']}", linewidth=2)
    
    ax2.set_xlabel('Radius (pc)', fontsize=12)
    ax2.set_ylabel('Density (g/cm³)', fontsize=12)
    ax2.set_title('Density Profile (Linear)', fontsize=14)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Power law index (derivative of log-log plot)
    for data in all_data:
        radius = data['radius']
        density = data['density']
        
        # Convert to log space and calculate derivative
        log_radius = np.log10(radius)
        log_density = np.log10(density)
        d_log_density = np.gradient(log_density, log_radius)
        
        ax3.semilogx(radius, d_log_density, color=data['color'], 
                    label=f"t={data['timestep']}", linewidth=2)
    
    ax3.set_xlabel('Radius (pc)', fontsize=12)
    ax3.set_ylabel('d(log ρ)/d(log r)', fontsize=12)
    ax3.set_title('Power Law Index', fontsize=14)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=-2, color='red', linestyle='--', alpha=0.7, label='ρ ∝ r⁻²')
    ax3.set_ylim(-10, 10)  # Limit power law index range
    
    # Plot 4: Velocity vs distance
    for data in all_data:
        if data['velocity'] is not None:
            ax4.semilogx(data['radius'], data['velocity'], color=data['color'], 
                        label=f"t={data['timestep']}", linewidth=2)
    
    ax4.set_xlabel('Radius (pc)', fontsize=12)
    ax4.set_ylabel('Velocity (km/s)', fontsize=12)
    ax4.set_title('Velocity vs Distance', fontsize=14)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save plot
    # Use the first file's basename for the output filename
    first_file = os.path.basename(files[0]).replace('.vtu', '') if files else 'analysis'
    output_file = os.path.join(output_dir, f'{first_file}_four_panel_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Four-panel analysis plot saved to: {output_file}")
    
    # Also show the plot
    plt.show()
    
    return output_file

def plot_single_snapshot(filename, output_dir='plots'):
    """
    Create 4-panel analysis for a single snapshot.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    radius, density, other_vars = read_vtu_file(filename)
    radius_pc, density_cgs, converted_vars = convert_units(radius, density, other_vars)
    
    # Create 2x2 subplot figure
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'Stellar Wind Analysis - {os.path.basename(filename)}', fontsize=16)
    
    # Plot 1: Log-log density profile
    ax1.loglog(radius_pc, density_cgs, 'b-', linewidth=2)
    ax1.set_xlabel('Radius (pc)')
    ax1.set_ylabel('Density (g/cm³)')
    ax1.set_title('Density Profile (Log-Log)')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Regular (linear) density profile
    ax2.plot(radius_pc, density_cgs, 'b-', linewidth=2)
    ax2.set_xlabel('Radius (pc)')
    ax2.set_ylabel('Density (g/cm³)')
    ax2.set_title('Density Profile (Linear)')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Power law index (derivative of log-log plot)
    log_radius = np.log10(radius_pc)
    log_density = np.log10(density_cgs)
    d_log_density = np.gradient(log_density, log_radius)
    
    ax3.semilogx(radius_pc, d_log_density, 'g-', linewidth=2)
    ax3.set_xlabel('Radius (pc)')
    ax3.set_ylabel('d(log ρ)/d(log r)')
    ax3.set_title('Power Law Index')
    ax3.grid(True, alpha=0.3)
    ax3.axhline(y=-2, color='red', linestyle='--', alpha=0.7, label='ρ ∝ r⁻²')
    ax3.axhline(y=-3, color='orange', linestyle='--', alpha=0.7, label='ρ ∝ r⁻³')
    ax3.set_ylim(-10, 10)  # Limit power law index range
    ax3.legend()
    
    # Plot 4: Velocity vs distance
    if 'velocity_km_s' in converted_vars:
        ax4.plot(radius_pc, converted_vars['velocity_km_s'], 'r-', linewidth=2)
        ax4.set_xlabel('Radius (pc)')
        ax4.set_ylabel('Velocity (km/s)')
        ax4.set_title('Velocity vs Distance')
        ax4.grid(True, alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'Velocity data\nnot available', 
                ha='center', va='center', transform=ax4.transAxes, fontsize=14)
        ax4.set_title('Velocity vs Distance')
    
    plt.tight_layout()
    
    # Save plot
    basename = os.path.basename(filename).replace('.vtu', '')
    output_file = os.path.join(output_dir, f'four_panel_analysis_{basename}.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"Four-panel analysis plot saved to: {output_file}")
    
    # Also show the plot
    plt.show()
    
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Plot density profiles from AMRVAC VTU files')
    parser.add_argument('--files', nargs='+', help='Specific VTU files to plot')
    parser.add_argument('--range', nargs=3, type=int, metavar=('START', 'END', 'STEP'),
                       help='Plot files in range: start end step (e.g., 0 50 10)')
    parser.add_argument('--single', help='Create detailed plots for a single file')
    parser.add_argument('--output', default='plots', help='Output directory for plots')
    parser.add_argument('--pattern', default='steady*.vtu', help='File pattern to search for')
    parser.add_argument('--directory', help='Directory to search for VTU files (overrides pattern search)')
    
    args = parser.parse_args()
    
    # Determine which files to process
    if args.single:
        if not os.path.exists(args.single):
            print(f"Error: File {args.single} not found")
            sys.exit(1)
        plot_single_snapshot(args.single, args.output)
        
    elif args.files:
        # Use specified files
        files = args.files
        for f in files:
            if not os.path.exists(f):
                print(f"Warning: File {f} not found")
        files = [f for f in files if os.path.exists(f)]
        if files:
            plot_density_profiles(files, args.output)
        else:
            print("No valid files found")
            
    elif args.range:
        # Use range of files
        start, end, step = args.range
        files = []
        for i in range(start, end + 1, step):
            filename = f"test{i:04d}.vtu"  # Assumes format like test0000.vtu
            if os.path.exists(filename):
                files.append(filename)
        
        if files:
            plot_density_profiles(files, args.output)
        else:
            print(f"No files found in range {start}-{end} with step {step}")
            
    else:
        # Use all available VTU files
        if args.directory:
            # Search in specified directory
            search_pattern = os.path.join(args.directory, args.pattern)
            files = sorted(glob.glob(search_pattern))
            print(f"Searching in directory: {args.directory}")
            print(f"Using pattern: {search_pattern}")
            print(f"Found {len(files)} files")
        else:
            # Search in current directory first
            files = sorted(glob.glob(args.pattern))
            print(f"Searching for pattern: {args.pattern}")
            print(f"Found {len(files)} files in current directory")
        
        if not files and not args.directory:
            # Try looking in multiple output directories
            search_paths = [
                os.path.join('output', 'Steadywind', args.pattern),
                os.path.join('output', 'Ostar_1D', args.pattern),
                os.path.join('output', args.pattern),
                os.path.join('..', '..', 'output', args.pattern),
                args.pattern  # Also try current directory again
            ]
            
            for search_path in search_paths:
                files = sorted(glob.glob(search_path))
                if files:
                    print(f"Found {len(files)} files using pattern: {search_path}")
                    break
                else:
                    print(f"No files found with pattern: {search_path}")
        
        if files:
                print(f"VTU files found:")
                for i, f in enumerate(files[:5]):  # Show first 5 files
                    print(f"  {i+1}: {f}")
                if len(files) > 5:
                    print(f"  ... and {len(files) - 5} more files")
                # Always plot only 5 files (first, last, and 3 random)
                import random
                if len(files) > 5:
                    first = files[0]
                    last = files[-1]
                    middle_files = files[1:-1]
                    if len(middle_files) >= 3:
                        random_files = random.sample(middle_files, 3)
                    else:
                        random_files = middle_files
                    files_to_plot = [first] + random_files + [last]
                    print("Plotting these 5 files (first, last, 3 random):")
                    for f in files_to_plot:
                        print(f"  {f}")
                    plot_density_profiles(files_to_plot, args.output)
                else:
                    plot_density_profiles(files, args.output)
        else:
            print("No VTU files found. Make sure you're in the right directory.")
            print("Current directory contents:")
            print(os.listdir('.'))

if __name__ == "__main__":
    main()
