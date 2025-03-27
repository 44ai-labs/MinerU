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