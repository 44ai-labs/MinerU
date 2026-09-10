# Use the official vllm image for gpu with Volta、Turing、Blackwell architecture (7.0 < Compute Capability < 8.0 or Compute Capability >= 10.0)
# Compute Capability version query (https://developer.nvidia.com/cuda-gpus)
# support x86_64 architecture and ARM(AArch64) architecture
FROM vllm/vllm-openai:v0.11.0

# Use the official vllm image for gpu with Ampere、Ada Lovelace、Hopper architecture (8.0 <= Compute Capability <= 9.0)
# only support x86_64 architecture
# FROM vllm/vllm-openai:v0.10.1.1

# Install libgl for opencv support & Noto fonts for Chinese characters
RUN apt-get update && \
    apt-get install -y \
        fonts-noto-core \
        fonts-noto-cjk \
        fontconfig \
        libgl1 && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy MinerU source code
COPY . /app/mineru
WORKDIR /app/mineru

# Install mineru from source
RUN python3 -m pip install -U -e '.[all]' --break-system-packages && \
    python3 -m pip cache purge

# Download models and update the configuration file
RUN /bin/bash -c "mineru-models-download -s huggingface -m all"

# Copy entrypoint script
COPY docker/global/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose API port
EXPOSE 8000

# Set the entry point to start API server and run warmup
ENTRYPOINT ["/entrypoint.sh"]