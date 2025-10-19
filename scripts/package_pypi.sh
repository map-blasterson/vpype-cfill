#!/bin/bash

# Simple packaging script for vpype-cfill
# Builds wheels for PyPI distribution

set -e

PROJECT_NAME="vpype-cfill"
PYTHON_VERSIONS=("3.9" "3.10" "3.11" "3.12" "3.13" "3.14")

echo "🚀 Packaging ${PROJECT_NAME} for PyPI"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check requirements
echo "Checking requirements..."

if ! command -v cargo &> /dev/null; then
    print_error "Rust/Cargo not found. Install from https://rustup.rs/"
    exit 1
fi
print_status "Rust/Cargo found: $(cargo --version)"

if ! command -v maturin &> /dev/null; then
    echo "Installing maturin..."
    pip install "maturin[patchelf]"
fi
print_status "Maturin found: $(maturin --version)"

# Clean previous builds
echo ""
echo "Cleaning previous builds..."
rm -rf dist/ target/wheels/ build/ *.egg-info/
print_status "Build artifacts cleaned"

# Add targets
echo "Adding all cross-platform targets..."
rustup target add x86_64-unknown-linux-gnu 2>/dev/null || true
rustup target add x86_64-apple-darwin 2>/dev/null || true
rustup target add aarch64-apple-darwin 2>/dev/null || true
rustup target add x86_64-pc-windows-msvc 2>/dev/null || true
rustup target add aarch64-pc-windows-msvc 2>/dev/null || true

# Create dist directory
mkdir -p dist

# Build source distribution
echo ""
echo "Building source distribution..."
if maturin sdist; then
    print_status "Source distribution built"
else
    print_warning "Source distribution build failed, continuing with wheels only"
fi

# Build wheels for available Python versions
echo ""
echo "Building wheels..."

# Try to find and build for specific Python versions
for version in "${PYTHON_VERSIONS[@]}"; do
    python_cmd="python${version}"
    echo ""
    echo "Building wheel for Python $version ($python_cmd)..."

    # Build for all platforms
    echo "Building for Linux targets..."
    maturin build --release --target x86_64-unknown-linux-gnu --interpreter "$python_cmd"

    echo "Building for macOS targets..."
    maturin build --release --target x86_64-apple-darwin --interpreter "$python_cmd" --zig
    maturin build --release --target aarch64-apple-darwin --interpreter "$python_cmd" --zig

    echo "Building for Windows targets..."
    maturin build --release --target x86_64-pc-windows-msvc --interpreter "$python_cmd"
    maturin build --release --target aarch64-pc-windows-msvc --interpreter "$python_cmd"
done

# Validate built packages
echo ""
echo "Validating built packages..."

WHEELS=(dist/*.whl)
SDISTS=(dist/*.tar.gz)

if [ ${#WHEELS[@]} -eq 0 ] && [ ${#SDISTS[@]} -eq 0 ]; then
    print_error "No packages found in dist/"
    exit 1
fi

echo "Built packages:"
for file in dist/*; do
    if [ -f "$file" ]; then
        echo "  - $(basename "$file")"
    fi
done

print_status "Found $(ls target/wheels/*.whl 2>/dev/null | wc -l) wheels and $(ls target/wheels/*.tar.gz 2>/dev/null | wc -l) source distributions"

# Upload options
echo ""
echo "Upload options:"
echo "1. Upload to Test PyPI (recommended first)"
echo "2. Upload to production PyPI"
echo "3. Skip upload"
read -p "Choose option (1/2/3): " -n 1 -r
echo

case $REPLY in
    1)
        echo "Uploading to Test PyPI..."
        if ! command -v twine &> /dev/null; then
            pip install twine
        fi

        echo "Make sure you have Test PyPI credentials configured:"
        echo "  python -m twine configure --repository testpypi"
        echo ""
        read -p "Press Enter to continue or Ctrl+C to cancel..."

        if twine upload --repository testpypi dist/*; then
            print_status "Successfully uploaded to Test PyPI"
            echo ""
            echo "Test installation with:"
            echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ $PROJECT_NAME"
        else
            print_error "Upload to Test PyPI failed"
        fi
        ;;
    2)
        echo "Uploading to production PyPI..."
        if ! command -v twine &> /dev/null; then
            pip install twine
        fi

        echo "⚠️  WARNING: This will upload to production PyPI!"
        echo "Make sure you have PyPI credentials configured:"
        echo "  python -m twine configure"
        echo ""
        read -p "Are you sure? Type 'yes' to continue: " -r

        if [[ $REPLY == "yes" ]]; then
            if twine upload dist/*; then
                print_status "Successfully uploaded to PyPI"
                echo ""
                echo "Install with:"
                echo "  pip install $PROJECT_NAME"
            else
                print_error "Upload to PyPI failed"
            fi
        else
            echo "Upload cancelled"
        fi
        ;;
    3)
        echo "Skipping upload"
        ;;
    *)
        echo "Invalid option, skipping upload"
        ;;
esac
