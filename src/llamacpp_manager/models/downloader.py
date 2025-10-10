# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/models/downloader.py
# Description: Download and manage LLM model files from Hugging Face
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-07

"""
Model download and management utilities.

Business Purpose: Automate downloading large coding models from Hugging Face
with progress tracking and automatic file organization.
"""

from typing import Optional, Callable, Dict, Any
from pathlib import Path
import os
import sys


class ModelDownloader:
    """
    Download models from Hugging Face with progress tracking.

    Handles large GGUF file downloads with resumable downloads
    and progress callbacks for UI integration.

    Business Purpose: Simplifies acquiring large coding models
    by automating download from Hugging Face Hub with proper
    file organization and progress feedback.
    """

    def __init__(self, models_dir: Optional[Path] = None):
        """
        Initialize model downloader.

        Args:
            models_dir: Directory to store downloaded models
                       (defaults to ~/llms/)
        """
        if models_dir is None:
            models_dir = Path.home() / "llms"
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def download_gguf(
        self,
        repo_id: str,
        filename: str,
        local_name: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Path:
        """
        Download a GGUF model file from Hugging Face.

        Args:
            repo_id: Hugging Face repo ID (e.g., "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF")
            filename: Filename in the repo (e.g., "qwen2.5-coder-32b-instruct-q8_0.gguf")
            local_name: Local model name for directory (e.g., "qwen-coder-32b")
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            Path to downloaded model file

        Example:
            downloader = ModelDownloader()
            model_path = downloader.download_gguf(
                "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
                "qwen2.5-coder-32b-instruct-q8_0.gguf",
                "qwen-coder-32b"
            )
            print(f"Downloaded to: {model_path}")
        """
        try:
            from huggingface_hub import hf_hub_download
        except ImportError:
            raise ImportError(
                "huggingface_hub is required for downloading models. "
                "Install with: pip install huggingface_hub"
            )

        # Create directory for this model
        model_dir = self.models_dir / local_name
        model_dir.mkdir(parents=True, exist_ok=True)

        # Download file with progress tracking
        print(f"📦 Downloading {filename} from {repo_id}...")
        print(f"📁 Saving to: {model_dir}")

        try:
            # Use huggingface_hub's download with progress
            local_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=model_dir,
                local_dir_use_symlinks=False,
                resume_download=True
            )

            downloaded_path = Path(local_path)
            print(f"✓ Downloaded successfully: {downloaded_path}")
            print(f"📊 File size: {downloaded_path.stat().st_size / (1024**3):.2f} GB")

            return downloaded_path

        except Exception as e:
            raise RuntimeError(f"Failed to download model: {e}")

    def list_downloaded_models(self) -> Dict[str, Dict[str, Any]]:
        """
        List all downloaded models.

        Returns:
            Dictionary mapping model name to info (path, size, etc.)

        Example:
            downloader = ModelDownloader()
            models = downloader.list_downloaded_models()
            for name, info in models.items():
                print(f"{name}: {info['size_gb']:.2f} GB")
        """
        models = {}

        for model_dir in self.models_dir.iterdir():
            if not model_dir.is_dir():
                continue

            # Find GGUF files in this directory
            gguf_files = list(model_dir.glob("*.gguf"))
            if not gguf_files:
                continue

            # Get the largest GGUF file (main model)
            main_file = max(gguf_files, key=lambda p: p.stat().st_size)
            size_bytes = main_file.stat().st_size

            models[model_dir.name] = {
                "path": str(main_file),
                "directory": str(model_dir),
                "size_bytes": size_bytes,
                "size_gb": size_bytes / (1024**3),
                "filename": main_file.name
            }

        return models

    def get_model_info(self, local_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a downloaded model.

        Args:
            local_name: Local model name

        Returns:
            Model info dict or None if not found

        Example:
            downloader = ModelDownloader()
            info = downloader.get_model_info("qwen-coder-32b")
            if info:
                print(f"Path: {info['path']}")
                print(f"Size: {info['size_gb']:.2f} GB")
        """
        models = self.list_downloaded_models()
        return models.get(local_name)


# Pre-configured model definitions for easy downloading
CODING_MODELS = {
    # Large coding models
    "qwen-coder-32b": {
        "repo_id": "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        "filename": "qwen2.5-coder-32b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 32B - Complex refactoring and architecture",
        "size_gb": 35,
        "ram_gb": 40,
        "use_case": "Complex refactoring, architecture design"
    },
    "qwen-coder-14b": {
        "repo_id": "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        "filename": "qwen2.5-coder-14b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 14B - Code review and test generation",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Code review, test generation, documentation"
    },
    "deepseek-coder-lite": {
        "repo_id": "bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
        "filename": "DeepSeek-Coder-V2-Lite-Instruct-Q8_0.gguf",
        "description": "DeepSeek Coder V2 Lite 16B - Quick debugging assistance",
        "size_gb": 18,
        "ram_gb": 22,
        "use_case": "Quick debugging, code explanation, documentation"
    },

    # Agentic & Tool-Calling Models
    "qwen-coder-7b": {
        "repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "filename": "qwen2.5-coder-7b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 7B - Best for tool calling and structured outputs",
        "size_gb": 8,
        "ram_gb": 12,
        "use_case": "Agentic workflows, tool calling, function execution, JSON outputs"
    },
    "hermes-3-llama-8b": {
        "repo_id": "NousResearch/Hermes-3-Llama-3.1-8B-GGUF",
        "filename": "Hermes-3-Llama-3.1-8B.Q8_0.gguf",
        "description": "Hermes 3 Llama 3.1 8B - Specifically trained for agentic use",
        "size_gb": 9,
        "ram_gb": 13,
        "use_case": "Multi-agent systems, autonomous workflows, tool orchestration"
    },
    "llama-3.1-8b": {
        "repo_id": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "filename": "Meta-Llama-3.1-8B-Instruct-Q8_0.gguf",
        "description": "Llama 3.1 8B Instruct - Strong instruction following",
        "size_gb": 9,
        "ram_gb": 13,
        "use_case": "Compliance queries, report generation, document analysis"
    },

    # Reasoning & Analysis Models
    "qwen-2.5-14b": {
        "repo_id": "Qwen/Qwen2.5-14B-Instruct-GGUF",
        "filename": "qwen2.5-14b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 14B Instruct - Balanced reasoning and speed",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Document analysis, evidence mapping, complex queries"
    }
}


def get_coding_model_info(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get pre-configured info for a coding model.

    Args:
        model_name: Name like "qwen-coder-32b"

    Returns:
        Model info dict or None if not found

    Example:
        info = get_coding_model_info("qwen-coder-32b")
        print(f"Description: {info['description']}")
        print(f"Size: {info['size_gb']} GB")
    """
    return CODING_MODELS.get(model_name)


def list_available_coding_models() -> Dict[str, Dict[str, Any]]:
    """
    List all available pre-configured coding models.

    Returns:
        Dictionary of model names to info

    Example:
        models = list_available_coding_models()
        for name, info in models.items():
            print(f"{name}: {info['description']}")
    """
    return CODING_MODELS.copy()
