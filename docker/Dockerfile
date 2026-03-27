# Multi-stage build for llama.cpp server
FROM alpine:3.19 AS builder

# Install build dependencies
RUN apk add --no-cache \
    git \
    cmake \
    make \
    g++ \
    pkgconfig \
    linux-headers

# Build llama.cpp from source - use recent version with --jinja support
WORKDIR /build
RUN git clone https://github.com/ggerganov/llama.cpp.git . && \
    git checkout master

RUN cmake -B build \
    -DCMAKE_BUILD_TYPE=Release \
    -DGGML_NATIVE=OFF \
    -DBUILD_SHARED_LIBS=ON && \
    cmake --build build --config Release --target llama-server -j$(nproc)

# Runtime stage
FROM alpine:3.19

# Install runtime dependencies
RUN apk add --no-cache \
    libgcc \
    libstdc++ \
    libgomp \
    ca-certificates \
    curl

# Create non-root user for security
RUN addgroup -g 1000 llama && \
    adduser -D -s /bin/sh -u 1000 -G llama llama

# Copy binary and shared libraries from builder stage
COPY --from=builder /build/build/bin/llama-server /usr/local/bin/llama-server
COPY --from=builder /build/build/bin/*.so* /usr/local/lib/
RUN chmod +x /usr/local/bin/llama-server && \
    ldconfig /usr/local/lib || true

# Create directories with proper permissions
RUN mkdir -p /models /logs && \
    chown -R llama:llama /models /logs

# Copy scripts
COPY docker/scripts/entrypoint.sh /usr/local/bin/
COPY docker/scripts/healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/healthcheck.sh

# Switch to non-root user
USER llama

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Default port (can be overridden)
EXPOSE 8080

# Default command - will be overridden by llamaCPPManager
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["--help"]