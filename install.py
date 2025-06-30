#!/usr/bin/env python3
"""
WebData CLI Installer
Installs webdata command globally for system-wide access
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def install_with_pip():
    """Install using pip in development mode"""
    print("Installing WebData CLI with pip...")
    try:
        # Install in development mode
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
        print("WebData CLI installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Pip installation failed: {e}")
        return False

def create_standalone_executable():
    """Create standalone executable script"""
    print("Creating standalone executable...")
    
    try:
        # Get current directory
        current_dir = Path(__file__).parent.absolute()
        
        # Create executable content
        executable_content = f'''#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, "{current_dir}")
from webdata import main

if __name__ == "__main__":
    main()
'''
        
        # Determine installation paths
        if sys.platform == "win32":
            # Windows
            install_dir = Path.home() / "AppData" / "Local" / "Programs" / "webdata-cli"
            bin_dir = install_dir / "bin"
            executable_name = "webdata.py"
            batch_content = f'''@echo off
python "{bin_dir / executable_name}" %*
'''
        else:
            # Unix-like systems
            bin_dir = Path.home() / ".local" / "bin"
            executable_name = "webdata"
        
        # Create directories
        bin_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy source files to installation directory if Windows
        if sys.platform == "win32":
            install_dir.mkdir(parents=True, exist_ok=True)
            for file in ["webdata.py", "requirements.txt"]:
                if Path(file).exists():
                    shutil.copy2(file, install_dir / file)
            
            # Create batch file
            batch_file = bin_dir / "webdata.bat"
            with open(batch_file, "w") as f:
                f.write(batch_content)
        
        # Create executable
        executable_path = bin_dir / executable_name
        with open(executable_path, "w") as f:
            f.write(executable_content)
        
        # Make executable on Unix
        if sys.platform != "win32":
            os.chmod(executable_path, 0o755)
        
        print(f"Executable created: {executable_path}")
        
        # Check if bin directory is in PATH
        path_env = os.environ.get("PATH", "")
        if str(bin_dir) not in path_env:
            print(f"\nIMPORTANT: Add to your PATH:")
            if sys.platform == "win32":
                print(f"Add this directory to your PATH: {bin_dir}")
            else:
                print(f"export PATH=$PATH:{bin_dir}")
                print("Add this line to your ~/.bashrc or ~/.zshrc")
        
        return True
        
    except Exception as e:
        print(f"Standalone installation failed: {e}")
        return False

def install_requirements():
    """Install Python requirements"""
    print("Installing Python requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Requirements installation failed: {e}")
        return False

def test_installation():
    """Test if webdata command works"""
    print("Testing installation...")
    try:
        # Try to run webdata --version
        result = subprocess.run(["webdata", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Installation test passed")
            return True
        else:
            print("Installation test failed - command not found")
            return False
    except FileNotFoundError:
        print("Installation test failed - webdata command not found in PATH")
        return False

def main():
    """Main installation function"""
    print("WebData CLI Installation")
    print("=" * 40)
    
    # Install requirements first
    if not install_requirements():
        print("Failed to install requirements")
        return False
    
    # Try pip installation first
    if install_with_pip():
        print("Pip installation successful")
        if test_installation():
            print("\nInstallation completed successfully!")
            print("You can now use: webdata --help")
            return True
    
    # Fallback to standalone installation
    print("\nTrying standalone installation...")
    if create_standalone_executable():
        print("\nStandalone installation completed!")
        print("You may need to add the bin directory to your PATH")
        print("Then you can use: webdata --help")
        return True
    
    print("\nInstallation failed. Please check errors above.")
    return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
