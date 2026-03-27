#!/usr/bin/env python3
"""
Setup script for llamaCPP Manager CLI distribution
Provides additional setuptools configuration for advanced packaging
"""

from setuptools import setup, find_packages
import sys
from pathlib import Path

# Read long description from README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read version from package
def get_version():
    version_file = Path(__file__).parent / "src" / "llamacpp_manager" / "__init__.py"
    if version_file.exists():
        content = version_file.read_text()
        for line in content.splitlines():
            if line.startswith("__version__"):
                return line.split('"')[1]
    return "0.1.0"

# Platform-specific dependencies
install_requires = [
    "PyYAML>=6.0",
    "mcp>=1.0.0",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "jinja2>=3.1.0",
    "huggingface_hub>=0.20.0",  # For model downloading
    "psutil>=5.9.0",  # For system memory detection (MLX safety)
]

# Optional dependencies for container/k8s features
extras_require = {
    "container": ["docker>=6.1.0"],
    "kubernetes": ["kubernetes>=28.1.0"],
    "dev": [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "black>=23.0.0",
        "ruff>=0.0.270",
        "mypy>=1.0.0",
    ],
    "all": ["docker>=6.1.0", "kubernetes>=28.1.0"],
}

setup(
    name="llamacpp-manager",
    version=get_version(),
    author="llamaCPP Manager Team",
    author_email="team@llamacpp-manager.dev",
    description="Toolkit for managing local llama-server instances (from llama.cpp) on macOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/llamacpp-manager",
    project_urls={
        "Bug Reports": "https://github.com/your-username/llamacpp-manager/issues",
        "Source": "https://github.com/your-username/llamacpp-manager",
        "Documentation": "https://github.com/your-username/llamacpp-manager/blob/main/docs/user-manual.md",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: MacOS :: MacOS X",
        "Environment :: Console",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.9",
    install_requires=install_requires,
    extras_require=extras_require,
    entry_points={
        "console_scripts": [
            "llamacpp-manager=llamacpp_manager.cli:main",
            "llamacpp-mcp-server=llamacpp_manager.mcp_server:main",
        ],
    },
    include_package_data=True,
    package_data={
        "llamacpp_manager": [
            "templates/**/*.j2",
            "templates/**/*.yaml",
            "templates/**/*.yml",
        ],
    },
    zip_safe=False,
    platforms=["darwin"],
    keywords=[
        "llama.cpp",
        "llama-server",
        "macos",
        "ai",
        "machine-learning",
        "local-ai",
        "model-management",
        "cli-tool",
    ],
)