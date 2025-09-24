class LlamacppManager < Formula
  desc "Toolkit for managing local llama-server instances (from llama.cpp) on macOS"
  homepage "https://github.com/your-username/llamacpp-manager"
  url "https://github.com/your-username/llamacpp-manager/archive/v1.0.0.tar.gz"
  sha256 "YOUR_SHA256_HASH_HERE"  # Generate this after creating the tarball
  license "Proprietary"
  head "https://github.com/your-username/llamacpp-manager.git", branch: "main"

  depends_on "python@3.11"
  depends_on "llama.cpp"

  resource "PyYAML" do
    url "https://files.pythonhosted.org/packages/cd/e5/af35f7ea75cf72f2cd079c95ee16797de7cd71f29ea7c68ae5ce7be1eda2b/PyYAML-6.0.1.tar.gz"
    sha256 "bfdf460b1736c775f2ba9f6a92bca30bc2095067b8a9d77876d1fad6cc3b4a43"
  end

  resource "mcp" do
    url "https://files.pythonhosted.org/packages/source/m/mcp/mcp-1.0.0.tar.gz"
    sha256 "REPLACE_WITH_ACTUAL_MCP_HASH"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/source/h/httpx/httpx-0.25.2.tar.gz"
    sha256 "8b8fcaa0c8ea7b05edd69a094e63a2094c4efcb48129fb757361bc423c0ad9e8"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic/pydantic-2.5.0.tar.gz"
    sha256 "b5635de53e6686fe7a44b5cf25fcc419a0d5e5c1a1efe73d49d48fe7586db854"
  end

  resource "docker" do
    url "https://files.pythonhosted.org/packages/source/d/docker/docker-6.1.3.tar.gz"
    sha256 "aa6d17830045ba5ef0168d5eaa34d37beeb113948c413affe1d5991fc11f9a20"
  end

  resource "jinja2" do
    url "https://files.pythonhosted.org/packages/source/j/jinja2/Jinja2-3.1.2.tar.gz"
    sha256 "31351a702a408a9e7595a8fc6150fc3f43bb6bf7e319770cbc0db9df9437e852"
  end

  def install
    # Install Python dependencies
    virtualenv_install_with_resources

    # Ensure CLI scripts are in PATH
    bin.install_symlink libexec/"bin/llamacpp-manager"
    bin.install_symlink libexec/"bin/llamacpp-mcp-server"

    # Create default directories
    (var/"llamacpp-manager/config").mkpath
    (var/"llamacpp-manager/logs").mkpath

    # Install shell completion (if available)
    generate_completions_from_executable(bin/"llamacpp-manager", "--help-completion",
                                         shells: [:bash, :zsh])
  end

  def post_install
    # Set up default configuration if none exists
    config_dir = var/"llamacpp-manager/config"
    unless (config_dir/"config.yaml").exist?
      ohai "Creating default configuration..."
      system bin/"llamacpp-manager", "--config-dir", config_dir,
             "--log-dir", var/"llamacpp-manager/logs", "init"
    end
  end

  service do
    # Optional: create a service for auto-starting models
    run [opt_bin/"llamacpp-manager", "ensure-running"]
    run_type :interval
    interval 60
    keep_alive false
    log_path var/"log/llamacpp-manager.log"
    error_log_path var/"log/llamacpp-manager.log"
  end

  test do
    # Test that the CLI works
    output = shell_output("#{bin}/llamacpp-manager --version")
    assert_match "0.1.0", output

    # Test initialization
    testdir = testpath/"test-config"
    testdir.mkpath
    system bin/"llamacpp-manager", "--config-dir", testdir, "init"
    assert_predicate testdir/"config.yaml", :exist?

    # Test configuration commands
    system bin/"llamacpp-manager", "--config-dir", testdir, "config", "list"

    # Test MCP server can start
    assert_match "MCP", shell_output("#{bin}/llamacpp-mcp-server --help")
  end
end