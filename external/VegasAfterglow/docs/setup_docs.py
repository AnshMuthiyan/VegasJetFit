#!/usr/bin/env python3
"""
Script to set up and verify documentation tools for VegasAfterglow.
Run this from the root directory to ensure all tools are installed.
"""

import os
import subprocess
import sys
from pathlib import Path

def check_command(command, package=None):
    """Check if a command is available on the system."""
    try:
        subprocess.run([command, '--version'],
                      stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE,
                      check=False)
        return True
    except FileNotFoundError:
        if package:
            print(f"Command '{command}' not found. Please install {package}.")
        else:
            print(f"Command '{command}' not found.")
        return False

def install_python_deps():
    """Install the Python dependencies for documentation."""
    print("Installing Python documentation dependencies...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'sphinx', 'sphinx_rtd_theme', 'breathe'],
                  check=True)
    print("Python dependencies installed successfully.")

def check_doxygen():
    """Check if Doxygen is installed and suggest installation command."""
    if not check_command('doxygen', 'Doxygen'):
        if sys.platform == 'darwin':  # macOS
            print("To install Doxygen on macOS, run: brew install doxygen")
        elif sys.platform.startswith('linux'):
            print("To install Doxygen on Linux, run: sudo apt-get install doxygen")
        elif sys.platform == 'win32':
            print("To install Doxygen on Windows, download from http://www.doxygen.nl/download.html")
        return False
    return True

def check_graphviz():
    """Check if Graphviz is installed and suggest installation command."""
    if not check_command('dot', 'Graphviz'):
        if sys.platform == 'darwin':  # macOS
            print("To install Graphviz on macOS, run: brew install graphviz")
        elif sys.platform.startswith('linux'):
            print("To install Graphviz on Linux, run: sudo apt-get install graphviz")
        elif sys.platform == 'win32':
            print("To install Graphviz on Windows, download from https://graphviz.org/download/")
        return False
    return True

def check_sphinx():
    """Check if Sphinx is installed."""
    try:
        import sphinx
        print(f"Sphinx is installed (version {sphinx.__version__}).")
        return True
    except ImportError:
        print("Sphinx is not installed.")
        return False

def check_breathe():
    """Check if Breathe is installed."""
    try:
        import breathe
        print(f"Breathe is installed (version {breathe.__version__}).")
        return True
    except ImportError:
        print("Breathe is not installed.")
        return False

def create_directories():
    """Create necessary directories if they don't exist."""
    docs_dir = Path('docs')
    dirs = [
        docs_dir / 'source' / '_static',
        docs_dir / 'source' / '_templates',
        docs_dir / 'build',
        docs_dir / 'doxygen'
    ]

    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")

def main():
    print("Setting up documentation tools for VegasAfterglow...")

    # Install Python dependencies
    install_python_deps()

    # Check external tools
    doxygen_installed = check_doxygen()
    graphviz_installed = check_graphviz()
    sphinx_installed = check_sphinx()
    breathe_installed = check_breathe()

    # Create necessary directories
    create_directories()

    # Summary
    print("\nSetup Summary:")
    print(f"Doxygen: {'Installed' if doxygen_installed else 'Not installed'}")
    print(f"Graphviz: {'Installed' if graphviz_installed else 'Not installed'}")
    print(f"Sphinx: {'Installed' if sphinx_installed else 'Not installed'}")
    print(f"Breathe: {'Installed' if breathe_installed else 'Not installed'}")

    if all([doxygen_installed, graphviz_installed, sphinx_installed, breathe_installed]):
        print("\nAll documentation tools are installed!")
        print("You can now build the documentation with:")
        print("  cd docs")
        print("  make all")
    else:
        print("\nSome documentation tools are missing. Please install them before building the documentation.")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
