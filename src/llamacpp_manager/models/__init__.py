# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/models/__init__.py
# Description: Models package for downloading and managing LLM model files
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-07

"""
Model management utilities.

Business Purpose: Provides tools for downloading large language models
from Hugging Face and managing model files locally.
"""

from .downloader import ModelDownloader

__all__ = ["ModelDownloader"]
