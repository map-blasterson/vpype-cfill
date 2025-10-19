#!/bin/bash

# Build script for vpype-fill extension

set -e

echo "Building vpype-fill extension..."

# Check if Rust is installed
if ! command -v cargo &> /dev/null; then
    echo "Error: Rust is not installed. Please install Rust from https://rustup.rs/"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Install maturin is installed
if ! command -v maturin &> /dev/null; then
    echo "Installing maturin..."
    pip install maturin
fi

# Build the Rust extension
echo "Building Rust extension..."
maturin develop --release

# Install the Python package
echo "Installing Python package..."
pip install -e .

echo "Build complete!"
echo ""
echo "Test the installation with:"
echo "  vpype --help  # should show 'cfill' command in plugins section"
echo "  vpype rect 0 0 100 100 cfill --pen-width 2.0 show"
