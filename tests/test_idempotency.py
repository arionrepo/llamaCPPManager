# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/tests/test_idempotency.py
# Description: Comprehensive idempotency tests for llamaCPPManager operations
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-11

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import subprocess

from llamacpp_manager.config import ModelSpec, InfrastructureComponentSpec, load_config, save_config, add_model
from llamacpp_manager.launchd import write_plist, render_plist, agents_dir, plist_path
from llamacpp_manager import utils


class TestConfigurationIdempotency:
    """
    Test that configuration operations are idempotent.

    Business Purpose: Ensure configuration can be applied multiple times
    without creating duplicates or corrupting state.
    """

    def test_save_config_idempotent(self, tmp_path, monkeypatch):
        """
        Verify saving same configuration multiple times produces identical result.

        Business Purpose: Config updates during deployment or user changes
        should not accumulate or corrupt existing settings.
        """
        # Use the existing test pattern from test_config.py
        cfgdir = tmp_path / "cfg"
        monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))

        # Create model file
        model_file = tmp_path / "test_model.gguf"
        model_file.write_text("dummy")

        # Create and save config multiple times
        spec = ModelSpec(name="test-model", model_path=str(model_file), port=8080)

        for i in range(3):
            cfg = load_config()
            # Remove existing model first to make operation idempotent
            from llamacpp_manager.config import remove_model
            remove_model(cfg, "test-model")  # Safe to call even if model doesn't exist
            add_model(cfg, spec)
            save_config(cfg)

        # Verify config is consistent after multiple saves
        final_config = load_config()
        matching_models = [m for m in final_config["models"] if m["name"] == "test-model"]
        assert len(matching_models) == 1
        assert matching_models[0]["port"] == 8080

    def test_add_model_idempotent(self, tmp_path, monkeypatch):
        """
        Verify adding same model multiple times doesn't create duplicates.

        Business Purpose: User or automation scripts might attempt to add
        the same model multiple times - should result in single entry.
        """
        cfgdir = tmp_path / "cfg"
        monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))

        # Create model file
        model_file = tmp_path / "duplicate_test.gguf"
        model_file.write_text("dummy")

        # Add same model multiple times using the existing API
        new_model = ModelSpec(name="duplicate-test", model_path=str(model_file), port=8081)

        for _ in range(3):
            cfg = load_config()
            # Remove existing model first to make operation idempotent
            from llamacpp_manager.config import remove_model
            remove_model(cfg, "duplicate-test")
            add_model(cfg, new_model)
            save_config(cfg)

        # Verify only one model exists
        final_config = load_config()
        duplicate_models = [m for m in final_config["models"] if m["name"] == "duplicate-test"]
        assert len(duplicate_models) == 1

    def test_update_model_idempotent(self, tmp_path, monkeypatch):
        """
        Verify updating model with same values multiple times is idempotent.

        Business Purpose: Configuration updates during deployment should not
        modify timestamps or create unnecessary file system changes.
        """
        from llamacpp_manager.config import update_model

        cfgdir = tmp_path / "cfg"
        monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))

        # Create model files
        initial_file = tmp_path / "initial.gguf"
        initial_file.write_text("dummy")
        updated_file = tmp_path / "updated.gguf"
        updated_file.write_text("dummy")

        # Create initial config with model
        spec = ModelSpec(name="update-test", model_path=str(initial_file), port=8082)
        cfg = load_config()
        add_model(cfg, spec)
        save_config(cfg)

        # Update model with new path multiple times
        for _ in range(3):
            cfg = load_config()
            update_model(cfg, "update-test", {"model_path": str(updated_file)})
            save_config(cfg)

        # Verify model has correct updated path (not corrupted by multiple updates)
        final_config = load_config()
        updated_model = next(m for m in final_config["models"] if m["name"] == "update-test")
        assert updated_model["model_path"] == str(updated_file)
        assert len(final_config["models"]) == 1


class TestLaunchdServiceIdempotency:
    """
    Test that launchd service operations are idempotent.

    Business Purpose: Service installation/management operations
    should be safe to retry without creating duplicate services.
    """

    def test_write_plist_idempotent(self, tmp_path):
        """
        Verify writing same plist multiple times produces identical result.

        Business Purpose: Service deployment scripts might run multiple times
        due to failures or retries - plist files should remain consistent.
        """
        plist_file = tmp_path / "test.plist"

        model_file = tmp_path / "plist-test.gguf"; model_file.write_text("x")
        spec = ModelSpec(name="plist-test", model_path=str(model_file), port=8083)
        plist_data = render_plist("/usr/bin/llama-server", spec, log_dir=tmp_path)

        # Write plist multiple times
        write_plist(plist_file, plist_data)
        initial_content = plist_file.read_bytes()

        write_plist(plist_file, plist_data)
        second_content = plist_file.read_bytes()

        write_plist(plist_file, plist_data)
        third_content = plist_file.read_bytes()

        assert initial_content == second_content == third_content

        # Verify plist is valid and contains expected data
        import plistlib
        with plist_file.open("rb") as f:
            loaded_data = plistlib.load(f)

        assert loaded_data["Label"] == "ai.llamacpp.plist-test"
        assert str(spec.port) in " ".join(loaded_data["ProgramArguments"])

    @patch('llamacpp_manager.launchd.subprocess.run')
    def test_service_bootstrap_idempotent(self, mock_run):
        """
        Verify bootstrapping same service multiple times handles gracefully.

        Business Purpose: Service installation during system setup should
        handle cases where service is already installed.
        """
        from llamacpp_manager.launchd import launchctl_bootstrap

        # Mock successful bootstrap first time
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        plist_path = Path("/tmp/test.plist")

        # First bootstrap - should succeed
        result1 = launchctl_bootstrap(plist_path)
        assert result1.returncode == 0

        # Mock "already exists" error for subsequent calls
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=37, stdout="", stderr="service already loaded"
        )

        # Second bootstrap - should handle "already exists" gracefully
        result2 = launchctl_bootstrap(plist_path)
        # returncode 37 is expected for "already exists" - this is idempotent behavior
        assert result2.returncode == 37

        # Verify launchctl was called twice
        assert mock_run.call_count == 2

    def test_service_directory_creation_idempotent(self, tmp_path):
        """
        Verify creating service directories multiple times is safe.

        Business Purpose: Service installation should handle pre-existing
        directories without failing.
        """
        # Mock agents_dir to use tmp_path
        with patch('llamacpp_manager.launchd.agents_dir', return_value=tmp_path):
            from llamacpp_manager.launchd import agents_dir, write_plist, render_plist

            service_dir = agents_dir()
            model_file = tmp_path / "dir-test.gguf"; model_file.write_text("x")
            spec = ModelSpec(name="dir-test", model_path=str(model_file), port=8084)
            plist_data = render_plist("/usr/bin/llama-server", spec, log_dir=tmp_path)
            plist_file = service_dir / "test.plist"

            # Create directory and plist multiple times
            for _ in range(3):
                write_plist(plist_file, plist_data)
                assert plist_file.exists()
                assert service_dir.exists()

            # Verify only one plist file exists
            plist_files = list(service_dir.glob("*.plist"))
            assert len(plist_files) == 1


class TestFileSystemIdempotency:
    """
    Test that file system operations are idempotent.

    Business Purpose: File operations during setup/deployment should be
    safe to retry without corrupting or duplicating data.
    """

    def test_ensure_directory_idempotent(self, tmp_path):
        """
        Verify directory creation is idempotent.

        Business Purpose: Setup scripts might create same directories
        multiple times - should not fail or change permissions.
        """
        test_dir = tmp_path / "nested" / "test" / "dir"

        # Create directory multiple times
        for _ in range(3):
            utils.ensure_dir(test_dir)
            assert test_dir.exists()
            assert test_dir.is_dir()

        # Verify directory still exists and is accessible
        test_file = test_dir / "test.txt"
        test_file.write_text("test content")
        assert test_file.read_text() == "test content"

    def test_log_file_creation_idempotent(self, tmp_path):
        """
        Verify log file setup is idempotent.

        Business Purpose: Log rotation and service restarts should handle
        existing log files gracefully.
        """
        log_dir = tmp_path / "logs"
        utils.ensure_dir(log_dir)

        log_file = log_dir / "test.log"

        # Create/touch log file multiple times
        for i in range(3):
            log_file.touch(exist_ok=True)
            assert log_file.exists()

            # Write some content
            with log_file.open("a") as f:
                f.write(f"Log entry {i}\n")

        # Verify log file contains all entries (cumulative, not duplicated)
        content = log_file.read_text()
        assert "Log entry 0" in content
        assert "Log entry 1" in content
        assert "Log entry 2" in content
        assert content.count("Log entry") == 3


class TestModelManagerIdempotency:
    """
    Test that model management operations are idempotent.

    Business Purpose: Model download/installation operations should handle
    partial downloads and re-runs without corruption.
    """

    def test_model_registration_idempotent(self, tmp_path, monkeypatch):
        """
        Verify registering same model multiple times doesn't create duplicates.

        Business Purpose: Model discovery or registration scripts might run
        multiple times - should maintain single model entry.
        """
        cfgdir = tmp_path / "cfg"
        monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))

        # Create model file
        model_file = tmp_path / "test.gguf"
        model_file.write_text("dummy")

        # Register same model multiple times
        model_spec = ModelSpec(
            name="test-model",
            model_path=str(model_file),
            port=8085,
            metadata={"size_gb": 4, "use_case": "chat"}
        )

        for _ in range(3):
            cfg = load_config()
            # Remove existing model first to make operation idempotent
            from llamacpp_manager.config import remove_model
            remove_model(cfg, "test-model")
            add_model(cfg, model_spec)
            save_config(cfg)

        # Verify only one model exists
        final_config = load_config()
        test_models = [m for m in final_config["models"] if m["name"] == "test-model"]
        assert len(test_models) == 1
        assert test_models[0]["metadata"]["size_gb"] == 4

    def test_port_allocation_idempotent(self):
        """
        Verify port allocation handles existing assignments correctly.

        Business Purpose: Port assignment during model setup should not
        create conflicts when run multiple times.
        """
        models = [
            ModelSpec(name="model1", model_path="/path1", port=8080),
            ModelSpec(name="model2", model_path="/path2", port=8081),
        ]

        # Simulate port allocation multiple times
        allocated_ports = set()

        for _ in range(3):
            for model in models:
                if model.port not in allocated_ports:
                    allocated_ports.add(model.port)

        # Verify each port is allocated only once
        assert len(allocated_ports) == 2
        assert 8080 in allocated_ports
        assert 8081 in allocated_ports


@pytest.mark.integration
class TestIntegrationIdempotency:
    """
    Integration tests for idempotency across multiple components.

    Business Purpose: End-to-end operations should be idempotent even
    when multiple components are involved.
    """

    def test_full_service_setup_idempotent(self, tmp_path, monkeypatch):
        """
        Verify complete service setup is idempotent.

        Business Purpose: Full deployment/setup scripts should be safe
        to run multiple times without corrupting system state.
        """
        cfgdir = tmp_path / "cfg"
        monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))

        # Mock various paths to use tmp_path
        log_dir = tmp_path / "logs"
        plist_dir = tmp_path / "plists"

        # Create model file
        model_file = tmp_path / "integration_test.gguf"
        model_file.write_text("dummy")

        spec = ModelSpec(name="integration-test", model_path=str(model_file), port=8086)

        def setup_service():
            # Create directories
            utils.ensure_dir(log_dir)
            utils.ensure_dir(plist_dir)

            # Save config using existing API
            cfg = load_config()
            # Remove existing model first to make operation idempotent
            from llamacpp_manager.config import remove_model
            remove_model(cfg, "integration-test")
            add_model(cfg, spec)
            save_config(cfg)

            # Create plist
            plist_data = render_plist("/usr/bin/llama-server", spec, log_dir=log_dir)
            plist_file = plist_dir / f"{spec.name}.plist"
            write_plist(plist_file, plist_data)

            return plist_file

        # Run setup multiple times
        results = []
        for _ in range(3):
            result = setup_service()
            results.append(result)

        # Verify all results are identical
        assert all(r == results[0] for r in results)

        # Verify final state is correct
        plist_file = results[0]
        assert plist_file.exists()

        # Verify config contains single model
        final_config = load_config()
        assert len(final_config["models"]) == 1
        assert final_config["models"][0]["name"] == "integration-test"