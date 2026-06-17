# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/models/downloader.py
# Description: Download and manage LLM model files from Hugging Face
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-07

"""
Model download and management utilities.

Business Purpose: Automate downloading large coding models from Hugging Face
with progress tracking and automatic file organization.
"""

from typing import Optional, Callable, Dict, Any, List
from pathlib import Path
import os
import sys
import json
import time
from datetime import datetime, timedelta


# HuggingFace API catalog caching
CATALOG_CACHE_PATH = Path.home() / ".config/llamacpp-manager/hf_catalog_cache.json"
CATALOG_CACHE_TTL_SECONDS = 86400  # 24 hours

# HuggingFace namespaces to query (in priority order)
HF_NAMESPACES = [
    {"author": "bartowski", "library": "gguf", "limit": 30},
    {"author": "unsloth", "library": "gguf", "limit": 20},
    {"author": "ggml-org", "library": "gguf", "limit": 20},
    {"author": "Qwen", "library": "gguf", "limit": None},
    {"author": "google", "library": "gguf", "limit": None},
    {"author": "microsoft", "library": "gguf", "limit": None},
    {"author": "mistralai", "library": "gguf", "limit": None},
    {"author": "mlx-community", "library": "mlx", "limit": 40},
    {"author": "lmstudio-community", "library": "gguf", "limit": 15},
]


def fetch_live_catalog(force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Fetch live model catalog from HuggingFace API with TTL-based caching.

    Args:
        force_refresh: If True, ignore cache and fetch from HF API

    Returns:
        Dictionary of model name to model info

    Fetches from multiple authoritative HuggingFace namespaces and merges
    with curated static entries. Caches results for 24 hours.
    """
    # Check cache validity unless force_refresh is set
    if not force_refresh and CATALOG_CACHE_PATH.exists():
        cache_age = time.time() - CATALOG_CACHE_PATH.stat().st_mtime
        if cache_age < CATALOG_CACHE_TTL_SECONDS:
            try:
                with open(CATALOG_CACHE_PATH, 'r') as f:
                    cached = json.load(f)
                    cached['__catalog_source'] = 'cached'
                    cached['__catalog_fetched_at'] = datetime.fromtimestamp(
                        CATALOG_CACHE_PATH.stat().st_mtime
                    ).isoformat() + 'Z'
                    return cached
            except Exception as e:
                print(f"⚠️  Failed to read cache: {e}", file=sys.stderr)

    # Cache miss or force refresh - query HuggingFace API
    print("📡 Fetching latest models from HuggingFace...", file=sys.stderr)

    try:
        from huggingface_hub import api
    except ImportError:
        print("⚠️  huggingface_hub not available - using static catalog", file=sys.stderr)
        result = {k: {**v, 'format': 'gguf'} for k, v in list_available_coding_models().items()}
        # Add MLX models to the static catalog
        result.update({k: v for k, v in MLX_MODELS.items()})
        result['__catalog_source'] = 'static'
        result['__catalog_fetched_at'] = datetime.utcnow().isoformat() + 'Z'
        return result

    live_models = {}
    hf_token = os.environ.get('HUGGINGFACE_TOKEN')

    # Query each namespace
    for ns in HF_NAMESPACES:
        try:
            filter_str = f"author:{ns['author']}"
            if ns['library']:
                filter_str += f" library:{ns['library']}"

            models_iter = api.list_models(filter=filter_str, token=hf_token)
            count = 0
            for model_info in models_iter:
                if ns['limit'] and count >= ns['limit']:
                    break

                # Extract key info
                model_id = model_info.id
                repo_name = model_id.split('/')[-1]

                live_models[repo_name.lower().replace('_', '-')] = {
                    'repo_id': model_id,
                    'filename': None,
                    'description': model_info.description or repo_name,
                    'size_gb': 'TBD',
                    'ram_gb': 'TBD',
                    'use_case': 'General purpose',
                    'version': '1.0',
                    'format': ns['library'],
                    'requires': 'Apple Silicon' if ns['library'] == 'mlx' else 'llama.cpp'
                }
                count += 1
        except Exception as e:
            print(f"⚠️  Failed to query {ns['author']}: {e}", file=sys.stderr)

    # Merge with curated static models (static takes precedence for fine-tuned/local)
    result = {**live_models}
    for name, info in list_available_coding_models().items():
        if name not in result:  # Don't override live models with static
            result[name] = info

    # Write cache
    try:
        CATALOG_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CATALOG_CACHE_PATH, 'w') as f:
            cache_data = {k: v for k, v in result.items() if not k.startswith('__')}
            json.dump(cache_data, f, indent=2)
        print(f"✓ Cached {len(cache_data)} models to {CATALOG_CACHE_PATH}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Failed to write cache: {e}", file=sys.stderr)

    result['__catalog_source'] = 'live'
    result['__catalog_fetched_at'] = datetime.utcnow().isoformat() + 'Z'
    return result


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

    def download_mlx(
        self,
        repo_id: str,
        local_name: str,
    ) -> Path:
        """
        Download an MLX model (entire repo) from Hugging Face.

        MLX models consist of multiple files (config, tokenizer, sharded
        safetensors). We use snapshot_download to get the whole repo.

        Args:
            repo_id: Hugging Face repo ID (e.g., "mlx-community/gemma-4-31b-it-4bit")
            local_name: Local model name for directory

        Returns:
            Path to the downloaded model directory
        """
        try:
            from huggingface_hub import snapshot_download
        except ImportError:
            raise ImportError(
                "huggingface_hub is required for downloading models. "
                "Install with: pip install huggingface_hub"
            )

        model_dir = self.models_dir / local_name
        model_dir.mkdir(parents=True, exist_ok=True)

        print(f"📦 Downloading MLX repo {repo_id}...")
        print(f"📁 Saving to: {model_dir}")

        try:
            local_path = snapshot_download(
                repo_id=repo_id,
                local_dir=str(model_dir),
                # Only download MLX/safetensors-compatible files (skip duplicates like .gguf if present)
                allow_patterns=["*.safetensors", "*.json", "*.txt", "*.model", "*.jinja", "tokenizer*"],
            )
            downloaded_path = Path(local_path)
            print(f"✓ Downloaded MLX model: {downloaded_path}")
            return downloaded_path

        except Exception as e:
            err_type = type(e).__name__
            err_msg = str(e)

            if "401" in err_msg or "403" in err_msg or "gated" in err_msg.lower():
                hint = " (auth — set HF_TOKEN env var if gated)"
            elif "404" in err_msg or "not found" in err_msg.lower() or "RepositoryNotFound" in err_type:
                hint = f" (not found — verify repo_id='{repo_id}')"
            elif "disk" in err_msg.lower() or "no space" in err_msg.lower():
                hint = " (disk error — check space)"
            elif "timeout" in err_msg.lower() or "connection" in err_msg.lower():
                hint = " (network error)"
            else:
                hint = ""
            raise RuntimeError(f"Failed to download MLX model ({err_type}): {err_msg}{hint}") from e

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
            err_type = type(e).__name__
            err_msg = str(e)

            if "401" in err_msg or "403" in err_msg or "authentication" in err_msg.lower():
                hint = " (auth error — run `huggingface-cli login` if repo is gated)"
            elif "404" in err_msg or "not found" in err_msg.lower() or "RepositoryNotFound" in err_type or "EntryNotFound" in err_type:
                hint = f" (not found — verify repo_id='{repo_id}' and filename='{filename}')"
            elif "disk" in err_msg.lower() or "no space" in err_msg.lower() or "OSError" in err_type:
                hint = " (disk error — check available space and write permissions)"
            elif "timeout" in err_msg.lower() or "connection" in err_msg.lower():
                hint = " (network error — check connectivity)"
            else:
                hint = ""

            raise RuntimeError(f"Failed to download model ({err_type}): {err_msg}{hint}") from e

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
    "qwen-coder-32b-q8": {
        "repo_id": "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        "filename": "qwen2.5-coder-32b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 32B Q8 - Highest quality",
        "size_gb": 35,
        "ram_gb": 40,
        "use_case": "Complex refactoring, architecture design",
        "version": "2.5-q8"
    },
    "qwen-coder-32b-q6": {
        "repo_id": "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        "filename": "qwen2.5-coder-32b-instruct-q6_k.gguf",
        "description": "Qwen 2.5 Coder 32B Q6 - Good quality, smaller",
        "size_gb": 27,
        "ram_gb": 32,
        "use_case": "Balanced quality/size for complex coding",
        "version": "2.5-q6"
    },
    "qwen-coder-32b-q4": {
        "repo_id": "Qwen/Qwen2.5-Coder-32B-Instruct-GGUF",
        "filename": "qwen2.5-coder-32b-instruct-q4_k_m.gguf",
        "description": "Qwen 2.5 Coder 32B Q4 - Fast, lower RAM",
        "size_gb": 19,
        "ram_gb": 24,
        "use_case": "Fast coding assistance with lower resources",
        "version": "2.5-q4"
    },
    "deepseek-coder-33b-q8": {
        "repo_id": "TheBloke/deepseek-coder-33B-instruct-GGUF",
        "filename": "deepseek-coder-33b-instruct.Q8_0.gguf",
        "description": "DeepSeek Coder 33B Q8 - Highest quality Chinese coding model",
        "size_gb": 36,
        "ram_gb": 42,
        "use_case": "Complex code generation, large refactoring",
        "version": "1.0-q8"
    },
    "deepseek-coder-33b-q4": {
        "repo_id": "TheBloke/deepseek-coder-33B-instruct-GGUF",
        "filename": "deepseek-coder-33b-instruct.Q4_K_M.gguf",
        "description": "DeepSeek Coder 33B Q4 - Fast Chinese coding model",
        "size_gb": 19,
        "ram_gb": 24,
        "use_case": "Fast code generation with lower resources",
        "version": "1.0-q4"
    },

    # === QWEN 3 FAMILY (Latest Generation) ===
    "qwen3-32b-q8": {
        "repo_id": "Qwen/Qwen3-32B-GGUF",
        "filename": "Qwen3-32B-Q8_0.gguf",
        "description": "Qwen 3 32B Q8 - Latest generation, highest quality",
        "size_gb": 35,
        "ram_gb": 40,
        "use_case": "Complex reasoning, code generation, large documents",
        "version": "3.0-q8"
    },
    "qwen3-32b-q4": {
        "repo_id": "Qwen/Qwen3-32B-GGUF",
        "filename": "Qwen3-32B-Q4_K_M.gguf",
        "description": "Qwen 3 32B Q4 - Balanced quality/size",
        "size_gb": 19,
        "ram_gb": 24,
        "use_case": "Fast reasoning with lower resources",
        "version": "3.0-q4"
    },
    "qwen3-14b-q8": {
        "repo_id": "Qwen/Qwen3-14B-GGUF",
        "filename": "Qwen3-14B-Q8_0.gguf",
        "description": "Qwen 3 14B Q8 - Mid-range capability",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Code review, reasoning, documentation",
        "version": "3.0-q8"
    },
    "qwen3-14b-q4": {
        "repo_id": "Qwen/Qwen3-14B-GGUF",
        "filename": "Qwen3-14B-Q4_K_M.gguf",
        "description": "Qwen 3 14B Q4 - Efficient mid-range",
        "size_gb": 8.5,
        "ram_gb": 12,
        "use_case": "Fast code review with lower resources",
        "version": "3.0-q4"
    },
    "qwen3-8b-q8": {
        "repo_id": "Qwen/Qwen3-8B-GGUF",
        "filename": "Qwen3-8B-Q8_0.gguf",
        "description": "Qwen 3 8B Q8 - Capable compact model",
        "size_gb": 9.2,
        "ram_gb": 12,
        "use_case": "General coding, chat, quick reasoning",
        "version": "3.0-q8"
    },
    "qwen3-8b-q4": {
        "repo_id": "Qwen/Qwen3-8B-GGUF",
        "filename": "Qwen3-8B-Q4_K_M.gguf",
        "description": "Qwen 3 8B Q4 - Lightweight capable",
        "size_gb": 5.0,
        "ram_gb": 8,
        "use_case": "Fast tasks, edge devices",
        "version": "3.0-q4"
    },
    "qwen3-4b": {
        "repo_id": "Qwen/Qwen3-4B-GGUF",
        "filename": "Qwen3-4B-Q4_K_M.gguf",
        "description": "Qwen 3 4B - Ultra-compact",
        "size_gb": 2.5,
        "ram_gb": 4,
        "use_case": "Mobile, edge inference, IoT devices",
        "version": "3.0"
    },
    "qwen3-1.7b": {
        "repo_id": "Qwen/Qwen3-1.7B-GGUF",
        "filename": "Qwen3-1.7B-Q8_0.gguf",
        "description": "Qwen 3 1.7B - Tiny but capable",
        "size_gb": 1.83,
        "ram_gb": 3,
        "use_case": "Lightweight tasks, extreme resource constraints",
        "version": "3.0"
    },
    "qwen3-0.6b": {
        "repo_id": "Qwen/Qwen3-0.6B-GGUF",
        "filename": "Qwen3-0.6B-Q8_0.gguf",
        "description": "Qwen 3 0.6B - Minimal footprint",
        "size_gb": 0.639,
        "ram_gb": 1.5,
        "use_case": "Autocomplete, ultra-low resource devices",
        "version": "3.0"
    },
    "qwen3.5-27b": {
        "repo_id": "unsloth/Qwen3.5-27B-GGUF",
        "filename": "Qwen3.5-27B-Q8_0.gguf",
        "description": "Qwen 3.5 27B - Advanced mid-range model",
        "size_gb": 29,
        "ram_gb": 34,
        "use_case": "Complex analysis, advanced reasoning",
        "version": "3.5"
    },
    "qwen3.6-35b-moe": {
        "repo_id": "unsloth/Qwen3.6-35B-A3B-GGUF",
        "filename": "Qwen3.6-35B-A3B-UD-Q4_K_M.gguf",
        "description": "Qwen 3.6 35B MoE - Latest MoE architecture",
        "size_gb": 21,
        "ram_gb": 28,
        "use_case": "Efficient large-model inference, expert selection",
        "version": "3.6",
        "note": "Mixture of Experts (MoE) - specialized routing"
    },

    # === MEDIUM CODING MODELS (10-25GB) ===
    "qwen-coder-14b-q8": {
        "repo_id": "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        "filename": "qwen2.5-coder-14b-instruct-q8_0.gguf",
        "description": "Qwen 2.5 Coder 14B Q8 - High quality Chinese coding",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Code review, test generation, documentation",
        "version": "2.5-q8"
    },
    "qwen-coder-14b-q6": {
        "repo_id": "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        "filename": "qwen2.5-coder-14b-instruct-q6_k.gguf",
        "description": "Qwen 2.5 Coder 14B Q6 - Balanced",
        "size_gb": 12,
        "ram_gb": 16,
        "use_case": "Efficient code review, good quality",
        "version": "2.5-q6"
    },
    "qwen-coder-14b-q4": {
        "repo_id": "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        "filename": "qwen2.5-coder-14b-instruct-q4_k_m.gguf",
        "description": "Qwen 2.5 Coder 14B Q4 - Fast, lower RAM",
        "size_gb": 8.5,
        "ram_gb": 12,
        "use_case": "Fast code review with lower resources",
        "version": "2.5-q4"
    },
    "deepseek-r1-qwen-32b-q8": {
        "repo_id": "bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF",
        "filename": "DeepSeek-R1-Distill-Qwen-32B-Q8_0.gguf",
        "description": "DeepSeek R1 Qwen 32B Q8 - Latest reasoning model",
        "size_gb": 35,
        "ram_gb": 40,
        "use_case": "Advanced reasoning, chain-of-thought, Chinese/English",
        "version": "r1-q8"
    },
    "deepseek-r1-qwen-32b-q4": {
        "repo_id": "bartowski/DeepSeek-R1-Distill-Qwen-32B-GGUF",
        "filename": "DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf",
        "description": "DeepSeek R1 Qwen 32B Q4 - Accessible reasoning",
        "size_gb": 19,
        "ram_gb": 24,
        "use_case": "Fast reasoning with lower resources",
        "version": "r1-q4"
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
    "llama-3.3-70b-q8": {
        "repo_id": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q8_0/Llama-3.3-70B-Instruct-Q8_0-00001-of-00002.gguf",
        "description": "Llama 3.3 70B Q8 - Latest 70B, highest quality",
        "size_gb": 75,
        "ram_gb": 82,
        "use_case": "Maximum quality reasoning, large documents",
        "version": "3.3-q8"
    },
    "llama-3.3-70b-q6": {
        "repo_id": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q6_K/Llama-3.3-70B-Instruct-Q6_K-00001-of-00002.gguf",
        "description": "Llama 3.3 70B Q6 - Good quality, manageable size",
        "size_gb": 58,
        "ram_gb": 64,
        "use_case": "Complex reasoning with balanced resources",
        "version": "3.3-q6"
    },
    "llama-3.3-70b-q4": {
        "repo_id": "bartowski/Llama-3.3-70B-Instruct-GGUF",
        "filename": "Llama-3.3-70B-Instruct-Q4_K_M.gguf",
        "description": "Llama 3.3 70B Q4 - Most accessible 70B model",
        "size_gb": 41,
        "ram_gb": 48,
        "use_case": "Complex reasoning with lower RAM requirements",
        "version": "3.3-q4"
    },
    "qwen-2.5-72b-q8": {
        "repo_id": "Qwen/Qwen2.5-72B-Instruct-GGUF",
        "filename": "qwen2.5-72b-instruct-q8_0-00001-of-00021.gguf",
        "description": "Qwen 2.5 72B Q8 - Highest quality",
        "size_gb": 76,
        "ram_gb": 82,
        "use_case": "Maximum quality advanced reasoning",
        "version": "2.5-q8"
    },
    "qwen-2.5-72b-q6": {
        "repo_id": "Qwen/Qwen2.5-72B-Instruct-GGUF",
        "filename": "qwen2.5-72b-instruct-q6_k-00001-of-00016.gguf",
        "description": "Qwen 2.5 72B Q6 - Balanced quality/size",
        "size_gb": 59,
        "ram_gb": 64,
        "use_case": "Advanced reasoning, manageable resources",
        "version": "2.5-q6"
    },
    "qwen-2.5-72b-q4": {
        "repo_id": "Qwen/Qwen2.5-72B-Instruct-GGUF",
        "filename": "qwen2.5-72b-instruct-q4_k_m-00001-of-00012.gguf",
        "description": "Qwen 2.5 72B Q4 - Most accessible",
        "size_gb": 42,
        "ram_gb": 48,
        "use_case": "Advanced reasoning with lower RAM",
        "version": "2.5-q4"
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

    # === ULTRA-TINY MODELS (<500MB) ===
    "gemma-3-270m": {
        "repo_id": "unsloth/gemma-3-270m-it-GGUF",
        "filename": "gemma-3-270m-it-Q8_0.gguf",
        "description": "Gemma 3 270M - Ultra-lightweight for IoT and browsers",
        "size_gb": 0.292,
        "ram_gb": 1,
        "use_case": "Drafting, IoT devices, browser apps, edge computing",
        "version": "3.0"
    },

    # === TINY MODELS (<2GB) ===
    "gemma-3-1b": {
        "repo_id": "unsloth/gemma-3-1b-it-GGUF",
        "filename": "gemma-3-1b-it-Q8_0.gguf",
        "description": "Gemma 3 1B - Compact for basic tasks",
        "size_gb": 1.1,
        "ram_gb": 2,
        "use_case": "Basic chat, summarization, mobile devices",
        "version": "3.0"
    },
    "gemma-3-4b": {
        "repo_id": "ggml-org/gemma-3-4b-it-GGUF",
        "filename": "gemma-3-4b-it-Q8_0.gguf",
        "description": "Gemma 3 4B - Multimodal (text + images)",
        "size_gb": 4.5,
        "ram_gb": 7,
        "use_case": "Multimodal tasks, image + text reasoning, 128K context",
        "version": "3.0"
    },
    "gemma-3-12b": {
        "repo_id": "unsloth/gemma-3-12b-it-GGUF",
        "filename": "gemma-3-12b-it-Q8_0.gguf",
        "description": "Gemma 3 12B - Powerful multimodal model",
        "size_gb": 13,
        "ram_gb": 16,
        "use_case": "Advanced multimodal reasoning, multilingual (140+ languages)",
        "version": "3.0"
    },
    "gemma-3-27b-q8": {
        "repo_id": "bartowski/google_gemma-3-27b-it-GGUF",
        "filename": "google_gemma-3-27b-it-Q8_0.gguf",
        "description": "Gemma 3 27B Q8 - Highest quality quantization",
        "size_gb": 29,
        "ram_gb": 34,
        "use_case": "Complex multimodal analysis, 128K context, multilingual",
        "version": "3.0-q8"
    },
    "gemma-3-27b-q6": {
        "repo_id": "bartowski/google_gemma-3-27b-it-GGUF",
        "filename": "google_gemma-3-27b-it-Q6_K.gguf",
        "description": "Gemma 3 27B Q6 - Good quality, smaller size",
        "size_gb": 22,
        "ram_gb": 26,
        "use_case": "Balanced quality/size multimodal model",
        "version": "3.0-q6"
    },
    "gemma-3-27b-q4": {
        "repo_id": "bartowski/google_gemma-3-27b-it-GGUF",
        "filename": "google_gemma-3-27b-it-Q4_K_M.gguf",
        "description": "Gemma 3 27B Q4 - Smallest, still capable",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Fast inference, lower RAM requirements",
        "version": "3.0-q4"
    },
    "gemma-3-27b-fp16": {
        "repo_id": "bartowski/google_gemma-3-27b-it-GGUF",
        "filename": "google_gemma-3-27b-it-bf16/google_gemma-3-27b-it-bf16-00001-of-00002.gguf",
        "description": "Gemma 3 27B FP16 - Unquantized full precision",
        "size_gb": 54,
        "ram_gb": 60,
        "use_case": "Maximum quality, research, fine-tuning base",
        "version": "3.0-fp16"
    },
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
        "filename": "smollm2-1.7b-instruct-q4_k_m.gguf",
        "description": "SmolLM2 1.7B - Tiny but capable instruction model",
        "size_gb": 1.8,
        "ram_gb": 3,
        "use_case": "Lightweight tasks, edge devices",
        "version": "2.0"
    },
    "starcoder2-7b": {
        "repo_id": "second-state/StarCoder2-7B-GGUF",
        "filename": "starcoder2-7b-Q8_0.gguf",
        "description": "StarCoder2 7B - Efficient multi-language coding",
        "size_gb": 8,
        "ram_gb": 11,
        "use_case": "Code completion, quick fixes",
        "version": "2.0"
    },
    "starcoder2-3b": {
        "repo_id": "second-state/StarCoder2-3B-GGUF",
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

    # === GEMMA 4 FAMILY (Latest, requires recent llama.cpp) ===
    "gemma-4-31b": {
        "repo_id": "unsloth/gemma-4-31B-it-GGUF",
        "filename": "gemma-4-31B-it-Q8_0.gguf",
        "description": "Gemma 4 31B Dense - Latest Google model",
        "size_gb": 33,
        "ram_gb": 40,
        "use_case": "Advanced reasoning, multilingual analysis",
        "version": "4.0",
        "requires": "Recent llama.cpp with gemma4_unified architecture support"
    },
    "gemma-4-26b-moe": {
        "repo_id": "ggml-org/gemma-4-26B-A4B-it-GGUF",
        "filename": "gemma-4-26B-A4B-it-Q4_K_M.gguf",
        "description": "Gemma 4 26B MoE - Mixture of Experts model",
        "size_gb": 16.8,
        "ram_gb": 22,
        "use_case": "Efficient large-model inference with expert routing",
        "version": "4.0",
        "requires": "Recent llama.cpp with gemma4_unified architecture and MoE support",
        "note": "Mixture of Experts (MoE) - selective expert activation"
    },
    "gemma-4-26b-moe-q8": {
        "repo_id": "ggml-org/gemma-4-26B-A4B-it-GGUF",
        "filename": "gemma-4-26B-A4B-it-Q8_0.gguf",
        "description": "Gemma 4 26B MoE Q8 - Highest quality MoE",
        "size_gb": 26.9,
        "ram_gb": 32,
        "use_case": "Maximum quality expert model inference",
        "version": "4.0",
        "requires": "Recent llama.cpp with gemma4_unified architecture and MoE support"
    },
    "gemma-4-12b-q8": {
        "repo_id": "ggml-org/gemma-4-12B-it-GGUF",
        "filename": "gemma-4-12B-it-Q8_0.gguf",
        "description": "Gemma 4 12B Q8 - Compact Google model",
        "size_gb": 12.7,
        "ram_gb": 16,
        "use_case": "General tasks, instruction following, analysis",
        "version": "4.0",
        "requires": "Recent llama.cpp with gemma4_unified architecture support"
    },
    "gemma-4-12b-q4": {
        "repo_id": "ggml-org/gemma-4-12B-it-GGUF",
        "filename": "gemma-4-12B-it-Q4_K_M.gguf",
        "description": "Gemma 4 12B Q4 - Efficient 12B model",
        "size_gb": 7.38,
        "ram_gb": 10,
        "use_case": "Lightweight reasoning with good quality",
        "version": "4.0",
        "requires": "Recent llama.cpp with gemma4_unified architecture support"
    },
    "gemma-4-edge-4b": {
        "repo_id": "ggml-org/gemma-4-E4B-it-GGUF",
        "filename": "gemma-4-E4B-it-Q4_K_M.gguf",
        "description": "Gemma 4 Edge 4B - Ultra-compact model",
        "size_gb": 5.34,
        "ram_gb": 7,
        "use_case": "Edge devices, mobile, resource-constrained inference",
        "version": "4.0",
        "requires": "Recent llama.cpp with gemma4_unified architecture support"
    },

    # === GOOGLE GEMMA 2 MODELS ===
    "gemma-2-2b": {
        "repo_id": "google/gemma-2-2b-it-GGUF",
        "filename": "2b_it_v2.gguf",
        "description": "Gemma 2 2B - Google's tiny efficient model",
        "size_gb": 2.3,
        "ram_gb": 4,
        "use_case": "Lightweight tasks, low resource environments",
        "version": "2.0"
    },

    # === MISTRAL MODELS ===
    "mistral-small-3.2-24b": {
        "repo_id": "bartowski/mistralai_Mistral-Small-3.2-24B-Instruct-2506-GGUF",
        "filename": "mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q8_0.gguf",
        "description": "Mistral Small 3.2 24B - Multimodal, latest Mistral",
        "size_gb": 25,
        "ram_gb": 30,
        "use_case": "Multimodal tasks, image + text analysis, reasoning",
        "version": "3.2",
        "note": "Multimodal support (text + images)"
    },
    "mistral-small-3.2-24b-q4": {
        "repo_id": "bartowski/mistralai_Mistral-Small-3.2-24B-Instruct-2506-GGUF",
        "filename": "mistralai_Mistral-Small-3.2-24B-Instruct-2506-Q4_K_M.gguf",
        "description": "Mistral Small 3.2 24B Q4 - Efficient multimodal",
        "size_gb": 14.3,
        "ram_gb": 18,
        "use_case": "Fast multimodal inference with lower memory",
        "version": "3.2"
    },
    "mistral-ministral-14b": {
        "repo_id": "mistralai/Ministral-3-14B-Instruct-2512-GGUF",
        "filename": "Ministral-3-14B-Instruct-2512-Q8_0.gguf",
        "description": "Mistral Ministral 14B - Official compact model",
        "size_gb": 14,
        "ram_gb": 18,
        "use_case": "General purpose, coding, reasoning",
        "version": "3.0"
    },
    "mistral-ministral-3b": {
        "repo_id": "mistralai/Ministral-3-3B-Instruct-2512-GGUF",
        "filename": "Ministral-3-3B-Instruct-2512-Q8_0.gguf",
        "description": "Mistral Ministral 3B - Ultra-compact official",
        "size_gb": 3.5,
        "ram_gb": 5,
        "use_case": "Lightweight tasks, mobile devices",
        "version": "3.0"
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

    # === REASONING MODELS ===
    "qwen-qwq-32b": {
        "repo_id": "bartowski/Qwen_QwQ-32B-GGUF",
        "filename": "Qwen_QwQ-32B-Q8_0.gguf",
        "description": "Qwen QwQ 32B - Advanced reasoning model",
        "size_gb": 35,
        "ram_gb": 40,
        "use_case": "Complex reasoning, chain-of-thought, problem solving",
        "version": "1.0"
    },
    "qwen-qwq-32b-q4": {
        "repo_id": "bartowski/Qwen_QwQ-32B-GGUF",
        "filename": "Qwen_QwQ-32B-Q4_K_M.gguf",
        "description": "Qwen QwQ 32B Q4 - Efficient reasoning",
        "size_gb": 19,
        "ram_gb": 24,
        "use_case": "Fast reasoning with lower resources",
        "version": "1.0"
    },

    # === VERY LARGE SPECIALIZED MODELS (requires high-end hardware) ===
    "minimax-m3-moe": {
        "repo_id": "unsloth/MiniMax-M3-GGUF",
        "filename": "UD-Q4_K_M/MiniMax-M3-UD-Q4_K_M-00001-of-00007.gguf",
        "description": "MiniMax M3 428B MoE - Extremely large model",
        "size_gb": 256,
        "ram_gb": 300,
        "use_case": "Large-scale reasoning, research (EXPERIMENTAL)",
        "version": "1.0",
        "requires": "Custom llama.cpp build (PR #24523), 300GB+ RAM",
        "note": "Experimental - requires custom llama.cpp fork"
    },
    "diffusiongemma-26b-gguf-legacy": {
        # NOTE: This GGUF variant requires `llama-diffusion-cli` which is CLI-only
        # (no HTTP server mode in upstream llama.cpp as of June 2026). Kept here
        # for users who downloaded it earlier; for new installs prefer the
        # MLX-VLM variants in MLX_MODELS (mlx-diffusiongemma-26b-{4,5,6,8}bit).
        "repo_id": "unsloth/diffusiongemma-26B-A4B-it-GGUF",
        "filename": "diffusiongemma-26B-A4B-it-Q4_K_M.gguf",
        "description": "[DEPRECATED] DiffusionGemma 26B - GGUF (CLI-only, no server)",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Diffusion text generation (CLI only, no server)",
        "version": "1.0",
        "format": "diffusion",
        "engine": "llama-diffusion-cli",
        "requires": "llama-diffusion-cli binary (not standard llama-server)",
        "deprecated": True,
        "note": "Use mlx-diffusiongemma-26b-4bit instead — has server mode via mlx-vlm"
    },

    # === REASONING & ANALYSIS MODELS ===
    "qwen-2.5-14b": {
        "repo_id": "Qwen/Qwen2.5-14B-Instruct-GGUF",
        "filename": "qwen2.5-14b-instruct-q8_0-00001-of-00004.gguf",
        "description": "Qwen 2.5 14B Instruct - Balanced reasoning and speed",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Document analysis, evidence mapping, complex queries",
        "version": "2.5"
    },
    "qwen-2.5-7b": {
        "repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "filename": "qwen2.5-7b-instruct-q8_0-00001-of-00003.gguf",
        "description": "Qwen 2.5 7B - General purpose reasoning",
        "size_gb": 8,
        "ram_gb": 11,
        "use_case": "Analysis, chat, reasoning tasks",
        "version": "2.5"
    },
    "phi-4-14b": {
        "repo_id": "microsoft/phi-4-gguf",
        "filename": "phi-4-Q8_0.gguf",
        "description": "Phi-4 14B Q8 - Microsoft's latest efficient model",
        "size_gb": 15.6,
        "ram_gb": 20,
        "use_case": "High-quality reasoning, long context, edge deployment",
        "version": "4.0"
    },
    "phi-4-14b-q4": {
        "repo_id": "microsoft/phi-4-gguf",
        "filename": "phi-4-IQ4_XS.gguf",
        "description": "Phi-4 14B Q4 - Compact Phi-4 for lower resources",
        "size_gb": 9,
        "ram_gb": 12,
        "use_case": "Balanced quality/size for edge devices",
        "version": "4.0"
    },
    "phi-4-mini-3.8b": {
        "repo_id": "bartowski/microsoft_Phi-4-mini-instruct-GGUF",
        "filename": "microsoft_Phi-4-mini-instruct-Q8_0.gguf",
        "description": "Phi-4 Mini 3.8B - Ultra-efficient Phi-4",
        "size_gb": 4.0,
        "ram_gb": 6,
        "use_case": "Quick tasks, mobile devices, low-resource inference",
        "version": "4.0"
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
        "repo_id": "gpustack/bge-reranker-v2-m3-GGUF",
        "filename": "bge-reranker-v2-m3-Q8_0.gguf",
        "description": "BGE Reranker - Document reranking",
        "size_gb": 1.5,
        "ram_gb": 3,
        "use_case": "Search result reranking, RAG improvement",
        "version": "2.0"
    }
}

# MLX models optimized for Apple Silicon (M1/M2/M3/M4)
MLX_MODELS = {
    # === DIFFUSION TEXT MODELS (MLX-VLM backend - experimental) ===
    # These are served via `python -m mlx_vlm.server` instead of `mlx_lm.server`
    # because mlx-vlm is currently the only Mac path that supports diffusion
    # sampling (DiffusionGemma). vLLM has native support but is Linux+CUDA only.
    # Stock llama-server doesn't support diffusion as of June 2026 (PR #24423 open).
    "mlx-diffusiongemma-26b-4bit": {
        "repo_id": "mlx-community/diffusiongemma-26B-A4B-it-4bit",
        "filename": None,
        "description": "DiffusionGemma 26B-A4B MoE (MLX 4-bit) — fast block-diffusion text gen",
        "size_gb": 14,
        "ram_gb": 18,
        "use_case": "Fast interactive generation (block diffusion, no KV cache)",
        "version": "1.0",
        "format": "diffusion",
        "engine": "mlx-vlm",
        "deployment_type": "mlx-vlm",
        "requires": "Apple Silicon + `llamacpp-manager bootstrap mlx-vlm`",
        "experimental": True,
        "note": "Experimental — Google calls DiffusionGemma research-preview; "
                "scores lower than Gemma 4 on reasoning/math/coding."
    },
    "mlx-diffusiongemma-26b-5bit": {
        "repo_id": "mlx-community/diffusiongemma-26B-A4B-it-5bit",
        "filename": None,
        "description": "DiffusionGemma 26B-A4B MoE (MLX 5-bit) — higher quality, more RAM",
        "size_gb": 17,
        "ram_gb": 22,
        "use_case": "Diffusion text gen with better quality than 4-bit",
        "version": "1.0",
        "format": "diffusion",
        "engine": "mlx-vlm",
        "deployment_type": "mlx-vlm",
        "requires": "Apple Silicon + `llamacpp-manager bootstrap mlx-vlm`",
        "experimental": True,
    },
    "mlx-diffusiongemma-26b-6bit": {
        "repo_id": "mlx-community/diffusiongemma-26B-A4B-it-6bit",
        "filename": None,
        "description": "DiffusionGemma 26B-A4B MoE (MLX 6-bit) — near-FP16 quality",
        "size_gb": 20,
        "ram_gb": 26,
        "use_case": "Diffusion text gen, high quality on M-series with 32GB+",
        "version": "1.0",
        "format": "diffusion",
        "engine": "mlx-vlm",
        "deployment_type": "mlx-vlm",
        "requires": "Apple Silicon + `llamacpp-manager bootstrap mlx-vlm`",
        "experimental": True,
    },
    "mlx-diffusiongemma-26b-8bit": {
        "repo_id": "mlx-community/diffusiongemma-26B-A4B-it-8bit",
        "filename": None,
        "description": "DiffusionGemma 26B-A4B MoE (MLX 8-bit) — highest MLX quality",
        "size_gb": 26,
        "ram_gb": 32,
        "use_case": "Diffusion text gen, max quality (requires ≥64GB RAM)",
        "version": "1.0",
        "format": "diffusion",
        "engine": "mlx-vlm",
        "deployment_type": "mlx-vlm",
        "requires": "Apple Silicon + `llamacpp-manager bootstrap mlx-vlm`",
        "experimental": True,
    },

    # === QWEN3 MLX MODELS (Latest) ===
    "mlx-qwen3-32b": {
        "repo_id": "mlx-community/Qwen3-32B-4bit",
        "filename": None,
        "description": "Qwen 3 32B (MLX 4-bit) - Latest generation for Mac",
        "size_gb": 18,
        "ram_gb": 22,
        "use_case": "Complex reasoning on Apple Silicon",
        "version": "3.0",
        "format": "mlx",
        "requires": "Apple Silicon (M1/M2/M3/M4+)"
    },
    "mlx-qwen3.6-35b-moe": {
        "repo_id": "unsloth/Qwen3.6-35B-A3B-UD-MLX-4bit",
        "filename": None,
        "description": "Qwen 3.6 35B MoE (MLX) - Advanced MoE on Mac",
        "size_gb": 19,
        "ram_gb": 24,
        "use_case": "Efficient large-model inference on Apple Silicon",
        "version": "3.6",
        "format": "mlx",
        "requires": "Apple Silicon (M2 Pro/Max recommended)",
        "note": "Mixture of Experts with Dynamic quantization (unsloth)"
    },

    # === GEMMA 4 MLX MODELS ===
    "mlx-gemma4-31b": {
        "repo_id": "mlx-community/gemma-4-31b-it-4bit",
        "filename": None,
        "description": "Gemma 4 31B (MLX 4-bit) - Latest Google for Mac",
        "size_gb": 16,
        "ram_gb": 20,
        "use_case": "Advanced reasoning on Apple Silicon",
        "version": "4.0",
        "format": "mlx",
        "requires": "Apple Silicon (M2 Pro/Max recommended)"
    },
    "mlx-gemma4-26b-moe": {
        "repo_id": "mlx-community/gemma-4-26B-A4B-it-4bit",
        "filename": None,
        "description": "Gemma 4 26B MoE (MLX 4-bit) - Efficient MoE for Mac",
        "size_gb": 13,
        "ram_gb": 16,
        "use_case": "Expert-routed inference on Apple Silicon",
        "version": "4.0",
        "format": "mlx",
        "requires": "Apple Silicon",
        "note": "Mixture of Experts"
    },
    "mlx-gemma4-12b": {
        "repo_id": "mlx-community/gemma-4-12b-it-4bit",
        "filename": None,
        "description": "Gemma 4 12B (MLX 4-bit) - Compact latest Google",
        "size_gb": 6.5,
        "ram_gb": 8,
        "use_case": "General tasks on Apple Silicon",
        "version": "4.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === MISTRAL & PHI MLX MODELS ===
    "mlx-phi4-14b": {
        "repo_id": "mlx-community/phi-4-4bit",
        "filename": None,
        "description": "Phi-4 14B (MLX 4-bit) - Latest Microsoft for Mac",
        "size_gb": 8,
        "ram_gb": 10,
        "use_case": "Efficient reasoning on Apple Silicon",
        "version": "4.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-mistral-small-3.2-24b": {
        "repo_id": "mlx-community/Mistral-Small-3.1-24B-Instruct-2503-4bit",
        "filename": None,
        "description": "Mistral Small 3.2 24B (MLX 4-bit) - Latest Mistral",
        "size_gb": 13,
        "ram_gb": 16,
        "use_case": "Advanced tasks on Apple Silicon",
        "version": "3.2",
        "format": "mlx",
        "requires": "Apple Silicon",
        "note": "Multimodal support"
    },

    # === LLAMA 3.3 MLX MODELS ===
    "mlx-llama-3.3-70b": {
        "repo_id": "mlx-community/Llama-3.3-70B-Instruct-4bit",
        "filename": None,
        "description": "Llama 3.3 70B (MLX 4-bit) - Latest 70B for Mac",
        "size_gb": 38,
        "ram_gb": 44,
        "use_case": "Complex reasoning on Apple Silicon",
        "version": "3.3",
        "format": "mlx",
        "requires": "Apple Silicon (64GB+ RAM recommended)"
    },

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

    # === ULTRA-TINY MLX MODELS (<500MB) ===
    "mlx-gemma-3-270m": {
        "repo_id": "mlx-community/gemma-3-270m-it-4bit",
        "filename": None,
        "description": "Gemma 3 270M (MLX 4-bit) - Ultra-lightweight for Mac",
        "size_gb": 0.15,
        "ram_gb": 0.5,
        "use_case": "Drafting, IoT, browser apps, extreme edge",
        "version": "3.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },

    # === TINY MLX MODELS (<2GB) ===
    "mlx-gemma-3-1b": {
        "repo_id": "mlx-community/gemma-3-1b-it-4bit",
        "filename": None,
        "description": "Gemma 3 1B (MLX 4-bit) - Compact for basic chat",
        "size_gb": 0.6,
        "ram_gb": 1,
        "use_case": "Basic chat, summarization, mobile devices",
        "version": "3.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-gemma-3-4b": {
        "repo_id": "mlx-community/gemma-3-4b-it-4bit",
        "filename": None,
        "description": "Gemma 3 4B (MLX 4-bit) - Multimodal for Mac",
        "size_gb": 2.4,
        "ram_gb": 4,
        "use_case": "Multimodal (text + images), 128K context",
        "version": "3.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-gemma-3-12b": {
        "repo_id": "mlx-community/gemma-3-12b-it-4bit",
        "filename": None,
        "description": "Gemma 3 12B (MLX 4-bit) - Powerful multimodal for Mac",
        "size_gb": 6.5,
        "ram_gb": 10,
        "use_case": "Advanced multimodal, multilingual (140+ languages)",
        "version": "3.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
    "mlx-gemma-3-27b": {
        "repo_id": "mlx-community/gemma-3-27b-it-4bit",
        "filename": None,
        "description": "Gemma 3 27B (MLX 4-bit) - Large multimodal for Mac",
        "size_gb": 14,
        "ram_gb": 18,
        "use_case": "Complex multimodal, 128K context, multilingual",
        "version": "3.0",
        "format": "mlx",
        "requires": "Apple Silicon"
    },
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
        "repo_id": "mlx-community/SmolLM2-1.7B-Instruct",
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
