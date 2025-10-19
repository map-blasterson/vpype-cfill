#!/usr/bin/env python3
"""
PyPI packaging script for vpype-cfill
Builds wheels for multiple Python versions and platforms
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from typing import List, Optional

# Configuration
PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12", "3.13"]
PROJECT_NAME = "vpype-cfill"
WHEEL_DIR = "dist"

class PackagingError(Exception):
    """Custom exception for packaging errors"""
    pass

def run_command(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            check=check, 
            capture_output=True, 
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if check:
            raise PackagingError(f"Command failed: {' '.join(cmd)}")
        return e

def check_requirements():
    """Check if all required tools are installed"""
    print("Checking requirements...")
    
    # Check Rust
    try:
        result = run_command(["cargo", "--version"])
        print(f"✓ Rust/Cargo found: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise PackagingError("Rust/Cargo not found. Install from https://rustup.rs/")
    
    # Check maturin
    try:
        result = run_command(["maturin", "--version"])
        print(f"✓ Maturin found: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing maturin...")
        run_command([sys.executable, "-m", "pip", "install", "maturin[patchelf]"])
    
    # Check if we can build wheels
    try:
        run_command(["maturin", "--help"])
        print("✓ Maturin is working")
    except subprocess.CalledProcessError:
        raise PackagingError("Maturin installation failed")

def clean_build_artifacts():
    """Clean previous build artifacts"""
    print("Cleaning build artifacts...")
    
    dirs_to_clean = [
        "dist",
        "target/wheels", 
        "build",
        "*.egg-info"
    ]
    
    for pattern in dirs_to_clean:
        if "*" in pattern:
            # Handle glob patterns
            import glob
            for path in glob.glob(pattern):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"Removed directory: {path}")
        else:
            if os.path.exists(pattern):
                if os.path.isdir(pattern):
                    shutil.rmtree(pattern)
                    print(f"Removed directory: {pattern}")
                else:
                    os.remove(pattern)
                    print(f"Removed file: {pattern}")

def build_source_distribution():
    """Build source distribution"""
    print("Building source distribution...")
    try:
        run_command(["maturin", "sdist"])
        print("✓ Source distribution built successfully")
    except PackagingError:
        print("⚠ Source distribution build failed, continuing with wheels only")

def build_wheels_local():
    """Build wheels for the current platform and available Python versions"""
    print("Building wheels for local platform...")
    
    # Create dist directory
    os.makedirs(WHEEL_DIR, exist_ok=True)
    
    # Try to build with maturin for available Python versions
    python_interpreters = []
    
    # Find available Python interpreters
    for version in PYTHON_VERSIONS:
        for python_cmd in [f"python{version}", f"python{version.replace('.', '')}"]:
            try:
                result = run_command([python_cmd, "--version"], check=False)
                if result.returncode == 0 and version in result.stdout:
                    python_interpreters.append(python_cmd)
                    print(f"✓ Found Python {version}: {python_cmd}")
                    break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
    
    if not python_interpreters:
        print("⚠ No specific Python versions found, building with current Python")
        python_interpreters = [sys.executable]
    
    # Build wheels
    successful_builds = 0
    for python_cmd in python_interpreters:
        try:
            print(f"\nBuilding wheel for {python_cmd}...")
            
            # Build wheel with specific Python interpreter
            cmd = ["maturin", "build", "--release", "--interpreter", python_cmd]
            run_command(cmd)
            successful_builds += 1
            
        except PackagingError as e:
            print(f"⚠ Failed to build wheel for {python_cmd}: {e}")
            continue
    
    if successful_builds == 0:
        raise PackagingError("Failed to build any wheels")
    
    print(f"✓ Successfully built {successful_builds} wheels")

def build_wheels_cross_platform():
    """Build wheels for multiple platforms (requires Docker/cross-compilation setup)"""
    print("Attempting cross-platform builds...")
    
    # This requires either:
    # 1. Running on different platforms
    # 2. Using cibuildwheel
    # 3. Using Docker with cross-compilation
    
    platforms = []
    current_platform = platform.system().lower()
    
    if current_platform == "linux":
        platforms.extend([
            "--target", "x86_64-unknown-linux-gnu",
        ])
        # Add musl target if available
        try:
            run_command(["rustup", "target", "add", "x86_64-unknown-linux-musl"], check=False)
            platforms.extend(["--target", "x86_64-unknown-linux-musl"])
        except:
            pass
            
    elif current_platform == "darwin":
        platforms.extend([
            "--target", "x86_64-apple-darwin",
            "--target", "aarch64-apple-darwin",
        ])
        # Install targets
        for target in ["x86_64-apple-darwin", "aarch64-apple-darwin"]:
            run_command(["rustup", "target", "add", target], check=False)
            
    elif current_platform == "windows":
        platforms.extend([
            "--target", "x86_64-pc-windows-msvc",
        ])
    
    # Build for each target
    for i in range(0, len(platforms), 2):
        if i + 1 < len(platforms):
            target = platforms[i + 1]
            try:
                print(f"Building for target: {target}")
                cmd = ["maturin", "build", "--release"] + platforms[i:i+2]
                run_command(cmd, check=False)
            except PackagingError:
                print(f"⚠ Cross-compilation failed for {target}")

def setup_cibuildwheel():
    """Setup cibuildwheel for comprehensive cross-platform building"""
    print("Setting up cibuildwheel for comprehensive builds...")
    
    # Install cibuildwheel
    try:
        run_command([sys.executable, "-m", "pip", "install", "cibuildwheel"])
    except PackagingError:
        print("⚠ Failed to install cibuildwheel")
        return False
    
    # Create cibuildwheel config
    cibw_config = """
# Configuration for cibuildwheel
[tool.cibuildwheel]
# Build for Python 3.9-3.13
build = "cp39-* cp310-* cp311-* cp312-* cp313-*"

# Skip 32-bit builds and PyPy
skip = "*-win32 *-manylinux_i686 pp*"

# Build settings
build-verbosity = 1

[tool.cibuildwheel.linux]
before-all = "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && source ~/.cargo/env"
environment = 'PATH="$HOME/.cargo/bin:$PATH"'

[tool.cibuildwheel.macos]
before-all = "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && source ~/.cargo/env"
environment = 'PATH="$HOME/.cargo/bin:$PATH"'

[tool.cibuildwheel.windows]
before-all = "rustup-init.exe -y"
environment = 'PATH="$UserProfile\\.cargo\\bin;$PATH"'
"""
    
    # Add to pyproject.toml if not present
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        if "[tool.cibuildwheel]" not in content:
            with open(pyproject_path, "a") as f:
                f.write(cibw_config)
            print("✓ Added cibuildwheel configuration to pyproject.toml")
    
    return True

def run_cibuildwheel():
    """Run cibuildwheel to build wheels for all platforms"""
    if not setup_cibuildwheel():
        return False
        
    try:
        print("Running cibuildwheel...")
        run_command([sys.executable, "-m", "cibuildwheel", "--output-dir", "dist"])
        print("✓ cibuildwheel completed successfully")
        return True
    except PackagingError:
        print("⚠ cibuildwheel failed")
        return False

def validate_wheels():
    """Validate built wheels"""
    print("Validating wheels...")
    
    dist_path = Path(WHEEL_DIR)
    if not dist_path.exists():
        raise PackagingError("No dist directory found")
    
    wheels = list(dist_path.glob("*.whl"))
    sdists = list(dist_path.glob("*.tar.gz"))
    
    if not wheels and not sdists:
        raise PackagingError("No wheels or source distributions found")
    
    print(f"Found {len(wheels)} wheels and {len(sdists)} source distributions:")
    for wheel in wheels:
        print(f"  - {wheel.name}")
    for sdist in sdists:
        print(f"  - {sdist.name}")
    
    # Install and test one wheel if possible
    if wheels:
        test_wheel = wheels[0]
        print(f"\nTesting wheel: {test_wheel.name}")
        try:
            # Create a temporary virtual environment for testing
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                venv_path = Path(temp_dir) / "test_env"
                run_command([sys.executable, "-m", "venv", str(venv_path)])
                
                # Activate and install
                if platform.system() == "Windows":
                    pip_cmd = str(venv_path / "Scripts" / "pip")
                    python_cmd = str(venv_path / "Scripts" / "python")
                else:
                    pip_cmd = str(venv_path / "bin" / "pip")
                    python_cmd = str(venv_path / "bin" / "python")
                
                run_command([pip_cmd, "install", str(test_wheel)])
                
                # Test import
                run_command([python_cmd, "-c", "import vpype_cfill; print('✓ Import successful')"])
                
        except PackagingError:
            print("⚠ Wheel validation failed")

def upload_to_pypi(test: bool = True):
    """Upload packages to PyPI"""
    repository = "--repository testpypi" if test else ""
    
    print(f"Uploading to {'Test ' if test else ''}PyPI...")
    
    try:
        # Install twine if not available
        run_command([sys.executable, "-m", "pip", "install", "twine"])
        
        # Upload
        cmd = [sys.executable, "-m", "twine", "upload"]
        if repository:
            cmd.extend(repository.split())
        cmd.append("dist/*")
        
        run_command(cmd)
        print("✓ Upload successful")
        
    except PackagingError:
        print("⚠ Upload failed. Make sure you have valid PyPI credentials.")
        print("Set up credentials with: python -m twine configure")

def main():
    """Main packaging workflow"""
    print(f"Packaging {PROJECT_NAME} for PyPI")
    print("=" * 50)
    
    try:
        # Change to project directory
        project_root = Path(__file__).parent
        os.chdir(project_root)
        
        # Check requirements
        check_requirements()
        
        # Clean previous builds
        clean_build_artifacts()
        
        # Build source distribution
        build_source_distribution()
        
        # Build wheels - try comprehensive approach first
        use_cibuildwheel = input("Use cibuildwheel for comprehensive cross-platform builds? (y/N): ").lower().startswith('y')
        
        if use_cibuildwheel:
            success = run_cibuildwheel()
            if not success:
                print("Falling back to local builds...")
                build_wheels_local()
        else:
            # Build local wheels
            build_wheels_local()
            
            # Try cross-platform builds
            cross_platform = input("Attempt cross-platform builds? (y/N): ").lower().startswith('y')
            if cross_platform:
                build_wheels_cross_platform()
        
        # Validate wheels
        validate_wheels()
        
        # Ask about upload
        upload = input("Upload to Test PyPI? (y/N): ").lower().startswith('y')
        if upload:
            upload_to_pypi(test=True)
            
            prod_upload = input("Upload to production PyPI? (y/N): ").lower().startswith('y')
            if prod_upload:
                upload_to_pypi(test=False)
        
        print("\n✓ Packaging complete!")
        print(f"Built packages are in: {WHEEL_DIR}/")
        
    except PackagingError as e:
        print(f"\n✗ Packaging failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠ Packaging interrupted by user")
        sys.exit(1)

if __name__ == "__main__":
    main()