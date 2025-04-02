FROM ubuntu:24.04

# without the matching nvidia-utils the GPU can not be found 
# be sure to use the same version as the nvidia driver on the server (defined in 44ai-infra)
RUN apt update && apt install -y ffmpeg git make curl wget build-essential ninja-build libstdc++6

# fix nvidia-utils version for now
RUN mkdir -p /nvidia-utils
RUN cd /nvidia-utils && wget https://db.cluster.44ai.ch/api/files/4w1vvtmayswbiwc/ol85linz87wyfi2/nvidia_utils_packages_24_04_7GwfuDoTwv.tar.gz -O nvidia-utils-packages.tar.gz
RUN cd /nvidia-utils && tar -xvf nvidia-utils-packages.tar.gz

RUN cd /nvidia-utils && apt install ./*.deb -y

# Install Miniforge (from conda-forge, includes mamba)
RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O Miniforge3.sh \
    && chmod +x Miniforge3.sh \
    && ./Miniforge3.sh -b -p /opt/conda \
    && rm Miniforge3.sh

ENV PATH="/opt/conda/bin:$PATH"


# Create conda env with python 3.13 using mamba
# install the proper libcudnn version =8.0 -> 8 installs 8.2.1 but torch is compiled with 8.9
RUN mamba create -y -p /opt/conda/envs/44ai-docker python=3.12 cudnn=8.9 -c conda-forge \
    && conda clean -afy

# Activate the environment by default
SHELL ["conda", "run", "-p", "/opt/conda/envs/44ai-docker", "/bin/bash", "-c"]

# Optional: Set env vars
ENV CONDA_DEFAULT_ENV=44ai-docker
ENV PATH="/opt/conda/envs/44ai-docker/bin:$PATH"

RUN pip install uv

WORKDIR /serve_app

COPY scripts/ scripts/
COPY projects/ projects/
RUN uv pip install huggingface_hub modelscope
RUN python projects/web_server/download_models.py

COPY magic_pdf/ magic_pdf/
COPY setup.py .

# need for python local build
COPY README.md .
COPY requirements.txt .

# RUN uv pip install torch
# RUN uv pip install --no-build-isolation 'detectron2 @ git+https://github.com/facebookresearch/detectron2.git@main' 
RUN uv pip install torch && \
  uv pip install --no-build-isolation 'detectron2 @ git+https://github.com/facebookresearch/detectron2.git@main' && \
  uv pip install -e ".[full]" && \
  uv pip install paddlepaddle-gpu==3.0.0rc1 -i https://www.paddlepaddle.org.cn/packages/stable/cu123/ && \
  uv pip install -r projects/web_server/requirements.txt


# GPU Accel
# RUN uv pip install --system paddlepaddle-gpu==3.0.0rc1 -i https://www.paddlepaddle.org.cn/packages/stable/cu123/
# Install Server requirements
# RUN uv pip install --system -r projects/web_server/requirements.txt

COPY Makefile .
ENV SERVER_PORT="8000"
# to overwrite the fallback into the conda env which has an too old version...
ENV LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libstdc++.so.6"
ENV API_KEY="mamaistdiebeste"

RUN make download-paddle-models

EXPOSE 8000
CMD ["make", "start"]