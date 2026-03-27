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
    # === LARGE CODING MODELS (25GB+) ===
    "qwen-coder-32b": {
        "repo_id": "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        "filename": "qwen2.5-coder-32b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 32B - Complex refactoring and architecture",
        "size_gb": 35,
        "ram_gb": 40,
        "use_case": "Complex refactoring, architecture design",
        "version": "2.5"
    },
    "deepseek-coder-33b": {
        "repo_id": "bartowski/DeepSeek-Coder-33B-Instruct-GGUF",
        "filename": "DeepSeek-Coder-33B-Instruct-Q8_0.gguf",
        "description": "DeepSeek Coder 33B - Advanced code generation",
        "size_gb": 36,
        "ram_gb": 42,
        "use_case": "Complex code generation, large refactoring",
        "version": "1.0"
    },

    # === MEDIUM CODING MODELS (10-25GB) ===
    "qwen-coder-14b": {
        "repo_id": "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        "filename": "qwen2.5-coder-14b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 14B - Code review and test generation",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Code review, test generation, documentation",
        "version": "2.5"
    },
    "deepseek-coder-lite": {
        "repo_id": "bartowski/DeepSeek-Coder-V2-Lite-Instruct-GGUF",
        "filename": "DeepSeek-Coder-V2-Lite-Instruct-Q8_0.gguf",
        "description": "DeepSeek Coder V2 Lite 16B - Quick debugging assistance",
        "size_gb": 18,
        "ram_gb": 22,
        "use_case": "Quick debugging, code explanation, documentation",
        "version": "2.0"
    },
    "codellama-13b": {
        "repo_id": "TheBloke/CodeLlama-13B-Instruct-GGUF",
        "filename": "codellama-13b-instruct.Q8_0.gguf",
        "description": "CodeLlama 13B - Meta's specialized coding model",
        "size_gb": 14,
        "ram_gb": 18,
        "use_case": "Code completion, debugging, explanation",
        "version": "1.0"
    },
    "starcoder2-15b": {
        "repo_id": "bartowski/starcoder2-15b-instruct-v0.1-GGUF",
        "filename": "starcoder2-15b-instruct-v0.1-Q8_0.gguf",
        "description": "StarCoder2 15B - Multi-language code generation",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Polyglot programming, code translation",
        "version": "2.0"
    },

    # === VERY LARGE MODELS (70B+) ===
    "llama-3.1-70b": {
        "repo_id": "bartowski/Meta-Llama-3.1-70B-Instruct-GGUF",
        "filename": "Meta-Llama-3.1-70B-Instruct-Q4_K_M.gguf",
        "description": "Llama 3.1 70B - Large scale reasoning",
        "size_gb": 40,
        "ram_gb": 45,
        "use_case": "Complex reasoning, large documents",
        "version": "3.1"
    },
    "mixtral-8x7b": {
        "repo_id": "TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF",
        "filename": "mixtral-8x7b-instruct-v0.1.Q4_K_M.gguf",
        "description": "Mixtral 8x7B - MoE architecture",
        "size_gb": 26,
        "ram_gb": 30,
        "use_case": "Complex tasks, multi-domain expertise",
        "version": "0.1"
    },
    "qwen-2.5-72b": {
        "repo_id": "Qwen/Qwen2.5-72B-Instruct-GGUF",
        "filename": "qwen2.5-72b-instruct-q4_k_m.gguf",
        "description": "Qwen 2.5 72B - Powerful reasoning model",
        "size_gb": 42,
        "ram_gb": 48,
        "use_case": "Advanced reasoning, complex analysis",
        "version": "2.5"
    },

    # === SMALL CODING MODELS (<10GB) ===
    "qwen-coder-7b": {
        "repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "filename": "qwen2.5-coder-7b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 7B - Best for tool calling and structured outputs",
        "size_gb": 8,
        "ram_gb": 12,
        "use_case": "Agentic workflows, tool calling, function execution, JSON outputs",
        "version": "2.5"
    },
    "qwen-coder-3b": {
        "repo_id": "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF",
        "filename": "qwen2.5-coder-3b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 3B - Lightweight coding assistant",
        "size_gb": 3.5,
        "ram_gb": 6,
        "use_case": "Quick code completion, simple scripts",
        "version": "2.5"
    },
    "qwen-coder-1.5b": {
        "repo_id": "Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF",
        "filename": "qwen2.5-coder-1.5b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 1.5B - Ultra-lightweight",
        "size_gb": 1.8,
        "ram_gb": 4,
        "use_case": "Code completion, simple tasks, edge devices",
        "version": "2.5"
    },

    # === TINY MODELS (<2GB) ===
    "qwen-0.5b": {
        "repo_id": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "filename": "qwen2.5-0.5b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 0.5B - Extremely lightweight",
        "size_gb": 0.6,
        "ram_gb": 2,
        "use_case": "Autocomplete, very low resource environments",
        "version": "2.5"
    },
    "smollm2-1.7b": {
        "repo_id": "HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
        "filename": "smollm2-1.7b-instruct-q8_0.gguf",
        "description": "SmolLM2 1.7B - Tiny but capable instruction model",
        "size_gb": 1.8,
        "ram_gb": 3,
        "use_case": "Lightweight tasks, edge devices",
        "version": "2.0"
    },
    "tinyllama-1.1b": {
        "repo_id": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
        "filename": "tinyllama-1.1b-chat-v1.0.Q8_0.gguf",
        "description": "TinyLlama 1.1B - Smallest useful model",
        "size_gb": 1.2,
        "ram_gb": 2,
        "use_case": "Extreme low resource, testing",
        "version": "1.0"
    },
    "codellama-7b": {
        "repo_id": "TheBloke/CodeLlama-7B-Instruct-GGUF",
        "filename": "codellama-7b-instruct.Q8_0.gguf",
        "description": "CodeLlama 7B - Compact Meta coding model",
        "size_gb": 7.5,
        "ram_gb": 10,
        "use_case": "Code completion, basic debugging",
        "version": "1.0"
    },
    "starcoder2-7b": {
        "repo_id": "bartowski/starcoder2-7b-GGUF",
        "filename": "starcoder2-7b-Q8_0.gguf",
        "description": "StarCoder2 7B - Efficient multi-language coding",
        "size_gb": 8,
        "ram_gb": 11,
        "use_case": "Code completion, quick fixes",
        "version": "2.0"
    },
    "starcoder2-3b": {
        "repo_id": "bartowski/starcoder2-3b-GGUF",
        "filename": "starcoder2-3b-Q8_0.gguf",
        "description": "StarCoder2 3B - Tiny but capable",
        "size_gb": 3.5,
        "ram_gb": 6,
        "use_case": "IDE integration, autocomplete",
        "version": "2.0"
    },

    # === GENERAL PURPOSE WITH GOOD CODING ===
    "llama-3.2-3b": {
        "repo_id": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "filename": "Llama-3.2-3B-Instruct-Q8_0.gguf",
        "description": "Llama 3.2 3B - Latest compact Llama",
        "size_gb": 3.5,
        "ram_gb": 6,
        "use_case": "General + code, chat applications",
        "version": "3.2"
    },
    "llama-3.1-8b": {
        "repo_id": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
        "filename": "Meta-Llama-3.1-8B-Instruct-Q8_0.gguf",
        "description": "Llama 3.1 8B Instruct - Strong instruction following",
        "size_gb": 9,
        "ram_gb": 13,
        "use_case": "Compliance queries, report generation, document analysis",
        "version": "3.1"
    },
    "mistral-7b": {
        "repo_id": "TheBloke/Mistral-7B-Instruct-v0.3-GGUF",
        "filename": "mistral-7b-instruct-v0.3.Q8_0.gguf",
        "description": "Mistral 7B v0.3 - Efficient and capable",
        "size_gb": 8,
        "ram_gb": 11,
        "use_case": "General tasks, coding, analysis",
        "version": "0.3"
    },

    # === GOOGLE GEMMA MODELS ===
    "gemma-2-27b": {
        "repo_id": "google/gemma-2-27b-it-GGUF",
        "filename": "gemma-2-27b-it-Q8_0.gguf",
        "description": "Gemma 2 27B - Google's powerful reasoning model",
        "size_gb": 29,
        "ram_gb": 34,
        "use_case": "Complex reasoning, analysis, research",
        "version": "2.0"
    },
    "gemma-2-27b-qat": {
        "repo_id": "google/gemma-2-27b-it-GGUF",
        "filename": "gemma-2-27b-it-qat-Q6_K.gguf",
        "description": "Gemma 2 27B QAT - Quantization-aware trained for better quality",
        "size_gb": 22,
        "ram_gb": 26,
        "use_case": "High-quality reasoning with efficient memory use",
        "version": "2.0-qat"
    },
    "gemma-2-9b": {
        "repo_id": "google/gemma-2-9b-it-GGUF",
        "filename": "gemma-2-9b-it-Q8_0.gguf",
        "description": "Gemma 2 9B - Google's balanced model",
        "size_gb": 9.5,
        "ram_gb": 13,
        "use_case": "General tasks, coding, reasoning",
        "version": "2.0"
    },
    "gemma-2-9b-qat": {
        "repo_id": "google/gemma-2-9b-it-GGUF",
        "filename": "gemma-2-9b-it-qat-Q6_K.gguf",
        "description": "Gemma 2 9B QAT - Higher quality quantization",
        "size_gb": 7,
        "ram_gb": 10,
        "use_case": "Efficient reasoning with quality preservation",
        "version": "2.0-qat"
    },
    "gemma-2-2b": {
        "repo_id": "google/gemma-2-2b-it-GGUF",
        "filename": "gemma-2-2b-it-Q8_0.gguf",
        "description": "Gemma 2 2B - Google's tiny efficient model",
        "size_gb": 2.3,
        "ram_gb": 4,
        "use_case": "Lightweight tasks, low resource environments",
        "version": "2.0"
    },

    # === AGENTIC & TOOL-CALLING MODELS ===
    "hermes-3-llama-8b": {
        "repo_id": "NousResearch/Hermes-3-Llama-3.1-8B-GGUF",
        "filename": "Hermes-3-Llama-3.1-8B.Q8_0.gguf",
        "description": "Hermes 3 Llama 3.1 8B - Specifically trained for agentic use",
        "size_gb": 9,
        "ram_gb": 13,
        "use_case": "Multi-agent systems, autonomous workflows, tool orchestration",
        "version": "3.0"
    },
    "functionary-7b": {
        "repo_id": "meetkai/functionary-small-v3.2-GGUF",
        "filename": "functionary-small-v3.2.Q8_0.gguf",
        "description": "Functionary 7B - Specialized for function calling",
        "size_gb": 8,
        "ram_gb": 11,
        "use_case": "Function calling, tool use, API integration",
        "version": "3.2"
    },

    # === REASONING & ANALYSIS MODELS ===
    "qwen-2.5-14b": {
        "repo_id": "Qwen/Qwen2.5-14B-Instruct-GGUF",
        "filename": "qwen2.5-14b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 14B Instruct - Balanced reasoning and speed",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Document analysis, evidence mapping, complex queries",
        "version": "2.5"
    },
    "qwen-2.5-7b": {
        "repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "filename": "qwen2.5-7b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 7B - General purpose reasoning",
        "size_gb": 8,
        "ram_gb": 11,
        "use_case": "Analysis, chat, reasoning tasks",
        "version": "2.5"
    },
    "phi-3-medium": {
        "repo_id": "microsoft/Phi-3-medium-128k-instruct-gguf",
        "filename": "Phi-3-medium-128k-instruct-Q8_0.gguf",
        "description": "Phi-3 Medium - Microsoft's efficient model",
        "size_gb": 14,
        "ram_gb": 18,
        "use_case": "Long context tasks, document analysis",
        "version": "3.0"
    },
    "phi-3-mini": {
        "repo_id": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "filename": "Phi-3-mini-4k-instruct-q4.gguf",
        "description": "Phi-3 Mini - Tiny but capable",
        "size_gb": 2.5,
        "ram_gb": 4,
        "use_case": "Edge devices, quick tasks",
        "version": "3.0"
    },

    # === SPECIALIZED MODELS ===
    "nomic-embed": {
        "repo_id": "nomic-ai/nomic-embed-text-v1.5-GGUF",
        "filename": "nomic-embed-text-v1.5.Q8_0.gguf",
        "description": "Nomic Embed - Text embeddings model",
        "size_gb": 0.5,
        "ram_gb": 2,
        "use_case": "Semantic search, RAG applications",
        "version": "1.5"
    },
    "bge-reranker": {
        "repo_id": "BAAI/bge-reranker-v2-m3-GGUF",
        "filename": "bge-reranker-v2-m3.Q8_0.gguf",
        "description": "BGE Reranker - Document reranking",
        "size_gb": 1.5,
        "ram_gb": 3,
        "use_case": "Search result reranking, RAG improvement",
        "version": "2.0"
    }
}

# MLX models optimized for Apple Silicon (M1/M2/M3/M4)
MLX_MODELS = {
    # === LARGE MLX CODING MODELS ===
    "mlx-qwen-coder-32b": {
        "repo_id": "mlx-community/Qwen2.5-Coder-32B-Instruct-4bit",
        "filename": None,  # MLX uses directory structure
        "description": "Qwen 2.5 Coder 32B (MLX 4-bit) - Optimized for Apple Silicon",
        "size_gb": 18,
        "ram_gb": 22,
        "use_case": "Complex refactoring on Apple Silicon",
        "version": "2.5",
        "format": "mlx",
        "requires": "Apple Silicon (M1/M2/M3/M4)"
    },
    "mlx-deepseek-coder-33b": {
        "repo_id": "mlx-community/DeepSeek-Coder-V2-Lite-Instruct-4bit-mlx",
        "filename": None,
        "description": "DeepSeek Coder 33B (MLX 4-bit) - Fast on Apple Silicon",
        "size_gb": 19,
        "ram_gb": 24,
        "use_case": "Advanced code generation on Mac",
        "version": "2.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === MEDIUM MLX CODING MODELS ===
    "mlx-qwen-coder-14b": {
        "repo_id": "mlx-community/Qwen2.5-Coder-14B-Instruct-4bit",
        "filename": None,
        "description": "Qwen 2.5 Coder 14B (MLX 4-bit) - Efficient on Apple Silicon",
        "size_gb": 8,
        "ram_gb": 12,
        "use_case": "Code review, test generation on Mac",
        "version": "2.5",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-codellama-13b": {
        "repo_id": "mlx-community/CodeLlama-13b-Instruct-hf-4bit-mlx",
        "filename": None,
        "description": "CodeLlama 13B (MLX 4-bit) - Meta's coding model for Mac",
        "size_gb": 7.5,
        "ram_gb": 10,
        "use_case": "Code completion on Apple Silicon",
        "version": "1.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === SMALL MLX CODING MODELS ===
    "mlx-qwen-coder-7b": {
        "repo_id": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
        "filename": None,
        "description": "Qwen 2.5 Coder 7B (MLX 4-bit) - Lightweight for Mac",
        "size_gb": 4,
        "ram_gb": 6,
        "use_case": "Agentic workflows on Apple Silicon",
        "version": "2.5",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-qwen-coder-3b": {
        "repo_id": "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit",
        "filename": None,
        "description": "Qwen 2.5 Coder 3B (MLX 4-bit) - Ultra-efficient",
        "size_gb": 2,
        "ram_gb": 4,
        "use_case": "Quick tasks on MacBook Air/lower RAM",
        "version": "2.5",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-codellama-7b": {
        "repo_id": "mlx-community/CodeLlama-7b-Instruct-hf-4bit-mlx",
        "filename": None,
        "description": "CodeLlama 7B (MLX 4-bit) - Compact for Mac",
        "size_gb": 4,
        "ram_gb": 6,
        "use_case": "Code completion on Apple Silicon",
        "version": "1.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === GENERAL PURPOSE MLX MODELS ===
    "mlx-llama-3.1-8b": {
        "repo_id": "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit",
        "filename": None,
        "description": "Llama 3.1 8B (MLX 4-bit) - Fast on Apple Silicon",
        "size_gb": 4.5,
        "ram_gb": 7,
        "use_case": "General tasks optimized for Mac",
        "version": "3.1",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-mistral-7b": {
        "repo_id": "mlx-community/Mistral-7B-Instruct-v0.3-4bit",
        "filename": None,
        "description": "Mistral 7B v0.3 (MLX 4-bit) - Efficient on Mac",
        "size_gb": 4,
        "ram_gb": 6,
        "use_case": "General tasks on Apple Silicon",
        "version": "0.3",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-phi-3-mini": {
        "repo_id": "mlx-community/Phi-3-mini-4k-instruct-4bit",
        "filename": None,
        "description": "Phi-3 Mini (MLX 4-bit) - Microsoft's tiny model",
        "size_gb": 1.5,
        "ram_gb": 3,
        "use_case": "Edge devices, MacBook Air",
        "version": "3.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === AGENTIC MLX MODELS ===
    "mlx-hermes-3-llama-8b": {
        "repo_id": "mlx-community/Hermes-3-Llama-3.1-8B-4bit",
        "filename": None,
        "description": "Hermes 3 Llama 8B (MLX 4-bit) - Agentic workflows on Mac",
        "size_gb": 4.5,
        "ram_gb": 7,
        "use_case": "Multi-agent systems on Apple Silicon",
        "version": "3.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === TINY MLX MODELS (<2GB) ===
    "mlx-qwen-0.5b": {
        "repo_id": "mlx-community/Qwen2.5-0.5B-Instruct-4bit",
        "filename": None,
        "description": "Qwen 0.5B (MLX 4-bit) - Ultra-tiny for Mac",
        "size_gb": 0.3,
        "ram_gb": 1,
        "use_case": "Autocomplete, extreme low resource",
        "version": "2.5",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-smollm2-1.7b": {
        "repo_id": "mlx-community/SmolLM2-1.7B-Instruct-4bit",
        "filename": None,
        "description": "SmolLM2 1.7B (MLX 4-bit) - Tiny instruction model",
        "size_gb": 1.0,
        "ram_gb": 2,
        "use_case": "Lightweight tasks on Mac",
        "version": "2.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === GOOGLE GEMMA MLX MODELS ===
    "mlx-gemma-2-27b": {
        "repo_id": "mlx-community/gemma-2-27b-it-4bit",
        "filename": None,
        "description": "Gemma 2 27B (MLX 4-bit) - Google's reasoning model for Mac",
        "size_gb": 15,
        "ram_gb": 20,
        "use_case": "Complex reasoning on Apple Silicon",
        "version": "2.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-gemma-2-9b": {
        "repo_id": "mlx-community/gemma-2-9b-it-4bit",
        "filename": None,
        "description": "Gemma 2 9B (MLX 4-bit) - Google's balanced model for Mac",
        "size_gb": 5,
        "ram_gb": 8,
        "use_case": "General tasks on Apple Silicon",
        "version": "2.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-gemma-2-2b": {
        "repo_id": "mlx-community/gemma-2-2b-it-4bit",
        "filename": None,
        "description": "Gemma 2 2B (MLX 4-bit) - Google's tiny model for Mac",
        "size_gb": 1.2,
        "ram_gb": 3,
        "use_case": "Lightweight tasks on Apple Silicon",
        "version": "2.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === LARGE MLX MODELS (70B+) ===
    "mlx-llama-3.1-70b": {
        "repo_id": "mlx-community/Meta-Llama-3.1-70B-Instruct-4bit",
        "filename": None,
        "description": "Llama 3.1 70B (MLX 4-bit) - Large scale on Mac",
        "size_gb": 38,
        "ram_gb": 42,
        "use_case": "Complex reasoning on Apple Silicon",
        "version": "3.1",
        "format": "mlx",
        "requires": "Apple Silicon (64GB+ RAM recommended)"
    },
    "mlx-qwen-2.5-72b": {
        "repo_id": "mlx-community/Qwen2.5-72B-Instruct-4bit",
        "filename": None,
        "description": "Qwen 2.5 72B (MLX 4-bit) - Powerful on Mac",
        "size_gb": 39,
        "ram_gb": 44,
        "use_case": "Advanced reasoning on Apple Silicon",
        "version": "2.5",
        "format": "mlx",
        "requires": "Apple Silicon (64GB+ RAM recommended)"
    }
}


def get_coding_model_info(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Get pre-configured info for a coding model (GGUF or MLX).

    Args:
        model_name: Name like "qwen-coder-32b" or "mlx-qwen-coder-7b"

    Returns:
        Model info dict or None if not found

    Example:
        info = get_coding_model_info("qwen-coder-32b")
        print(f"Description: {info['description']}")
        print(f"Size: {info['size_gb']} GB")
    """
    # Check GGUF models first, then MLX
    return CODING_MODELS.get(model_name) or MLX_MODELS.get(model_name)


def list_available_coding_models(format_filter: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    List all available pre-configured coding models.

    Args:
        format_filter: Filter by format ("gguf", "mlx", or None for all)

    Returns:
        Dictionary of model names to info

    Example:
        # All models
        models = list_available_coding_models()

        # Only GGUF models (for llama.cpp)
        gguf_models = list_available_coding_models(format_filter="gguf")

        # Only MLX models (for Apple Silicon)
        mlx_models = list_available_coding_models(format_filter="mlx")
    """
    all_models = {}

    # Add GGUF models (for llama.cpp)
    if format_filter is None or format_filter == "gguf":
        for name, info in CODING_MODELS.items():
            all_models[name] = {**info, "format": "gguf"}

    # Add MLX models (for Apple Silicon)
    if format_filter is None or format_filter == "mlx":
        all_models.update(MLX_MODELS)

    return all_models


def check_model_updates(downloader: Optional['ModelDownloader'] = None) -> Dict[str, Dict[str, Any]]:
    """
    Check for newer versions of downloaded models.

    Returns:
        Dictionary of models with available updates

    Example:
        updates = check_model_updates()
        for model, info in updates.items():
            print(f"{model}: v{info['current']} -> v{info['available']}")
    """
    if downloader is None:
        downloader = ModelDownloader()

    updates = {}
    downloaded = downloader.list_downloaded_models()

    for model_name in downloaded:
        if model_name in CODING_MODELS:
            model_info = CODING_MODELS[model_name]
            # In reality, we'd check Hugging Face for latest version
            # For now, we'll just compare with our registry
            if "version" in model_info:
                current_version = downloaded[model_name].get("version", "1.0")
                available_version = model_info["version"]

                # Simple version comparison
                if current_version != available_version:
                    updates[model_name] = {
                        "current": current_version,
                        "available": available_version,
                        "repo_id": model_info["repo_id"],
                        "filename": model_info["filename"],
                        "size_gb": model_info["size_gb"]
                    }

    return updates
