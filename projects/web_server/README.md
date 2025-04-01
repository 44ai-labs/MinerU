# Web Server Endpoint

```bash
# setup
mamba create python=3.11 --prefix /scratch/janniss/conda/mineru
conda activate /scratch/janniss/conda/mineru
pip install uv
# attention: this installs a really old package due to a deps issue
# uv pip install -U "magic-pdf[full]" --extra-index-url https://wheels.myhloli.com
# install detectron2 manually first
uv pip install --no-build-isolation 'detectron2 @ git+https://github.com/facebookresearch/detectron2.git@main' 
# install locally
uv pip install -e ".[full]"
```

### Install models

```bash
uv pip install huggingface_hub
python scripts/download_models_hf.py
```


### OCR CUDA Acceleration

```bash
uv pip install paddlepaddle-gpu==3.0.0rc1 -i https://www.paddlepaddle.org.cn/packages/stable/cu123/
# install cudnn manually -> libcudnn.so.8: cannot open shared object file: No such file or directory
mamba install cudnn=8 -c conda-forge
```


## Start with custom Path

```bash
# install
python projects/web_server/download_models.py
# needs to be absolute path
MINERU_TOOLS_CONFIG_JSON=$PWD/projects/web_server/magic-pdf-server.json python projects/web_server/simple_test.py
```

### Start and test Server

```bash
# start server
export PYTHONPATH=.
MINERU_TOOLS_CONFIG_JSON=$PWD/projects/web_server/magic-pdf-server.json python projects/web_server/server.py
# test
python projects/web_server/test_client.py
```


### Local k8s test

```bash
# install go
wget https://go.dev/dl/go1.24.1.linux-amd64.tar.gz
rm -rf /usr/local/go && sudo tar -C /usr/local -xzf go1.24.1.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
export PATH=$PATH:$(go env GOPATH)/bin
# install kind
go install sigs.k8s.io/kind@v0.27.0 && kind create cluster

# install the stack :-)
# install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && chmod +x kubectl && sudo mv kubectl /usr/local/bin/

# cluster config
kind export kubeconfig

kubectl create ns mineru-44ai

kubectl apply -f k8s_hidden/dockerhub-secret.yaml
kubectl apply -f k8s/deploy.yaml

```