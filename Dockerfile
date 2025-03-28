FROM ubuntu:24.04

# without the matching nvidia-utils the GPU can not be found 
# be sure to use the same version as the nvidia driver on the server (defined in 44ai-infra)
RUN apt update && apt install -y ffmpeg git make wget build-essential ninja-build libstdc++6

# fix nvidia-utils version for now
RUN mkdir -p /nvidia-utils
RUN cd /nvidia-utils && wget https://db.cluster.44ai.ch/api/files/4w1vvtmayswbiwc/ol85linz87wyfi2/nvidia_utils_packages_24_04_7GwfuDoTwv.tar.gz -O nvidia-utils-packages.tar.gz
RUN cd /nvidia-utils && tar -xvf nvidia-utils-packages.tar.gz

RUN cd /nvidia-utils && apt install ./*.deb -y

RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && bash miniconda.sh -b -p /root/miniconda3 && rm miniconda.sh && echo "export PATH=/root/miniconda3/bin:$PATH" >> ~/.bashrc
ENV PATH="/root/miniconda3/bin:$PATH"

# install the proper libcudnn version

RUN conda install python=3.12 cudnn=8 -c conda-forge
# to get the CONDA_PREFIX
# run it in a running container:  echo $CONDA_PREFIX
# it is /home/ray/anaconda3
# ENV LD_LIBRARY_PATH="/root/miniconda3/lib:$LD_LIBRARY_PATH"

RUN pip install uv

WORKDIR /serve_app

COPY scripts/ scripts/
COPY projects/ projects/
RUN uv pip install --system huggingface_hub modelscope
RUN python projects/web_server/download_models.py

COPY magic_pdf/ magic_pdf/
COPY setup.py .


RUN uv pip install --system torch
RUN uv pip install --system --no-build-isolation 'detectron2 @ git+https://github.com/facebookresearch/detectron2.git@main' 

# need for python local build
COPY README.md .
COPY requirements.txt .
RUN uv pip install --system -e ".[full]"


# GPU Accel
RUN uv pip install --system paddlepaddle-gpu==3.0.0rc1 -i https://www.paddlepaddle.org.cn/packages/stable/cu123/

# Install Server requirements

RUN uv pip install --system -r projects/web_server/requirements.txt

COPY Makefile .

ENV SERVER_PORT="8000"
# to overwrite the fallback into the conda env which has an too old version...
ENV LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libstdc++.so.6"

EXPOSE 8000
CMD ["make", "start"]