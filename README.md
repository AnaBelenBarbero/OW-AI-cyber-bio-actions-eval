# OW-AI-actions-eval

Actions speack louder than words. Secure AI actions.


```
# Run with defaults (decision_making scenarios)
make run-eval

# Run cyber scenarios
make run-cyber

# Run with custom model and port
make run-eval MODEL_NAME="your-model" PORT=9000

# Run with custom temperature and output file
make run-eval SCENARIOS=cyber TEMPERATURE=0.5 OUTPUT_FILE=cyber_results.json

# Override multiple parameters
make run-eval SCENARIOS=decision_making MODEL_NAME="custom-model" MODEL_PARENT="parent" MAX_TOKENS=1024
```

## Prepatarion

Base env setup. Using `python 3.12` and `UV` virtual env instead of project to quickly avoid some vllm-pytorch-gcc-cpu/gpu CUDA-OS headaches running it multiplatform. *ToBeImproved*

```
# UV install
curl -LsSf https://astral.sh/uv/install.sh | sh

uv venv --python 3.12 --seed

source .venv/bin/activate

uv pip install vllm --torch-backend=auto

uv pip install datasets peft bitsandbytes trl accelerate flashinfer-python streamlit \
    jupyterlab ipykernel ipywidgets 
```

Reproducibility in this kind of programs can be a bit tricky. If you face problems with GCC or python-dev:

```
sudo apt update
sudo apt install -y libc6-dev libstdc++-11-dev
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-11 20
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-11 20
sudo update-alternatives --set gcc /usr/bin/gcc-11
sudo update-alternatives --set g++ /usr/bin/g++-11

sudo apt-get update && sudo apt-get install -y python3.12-dev
```

## Models

Run in `2xH100`. It should be possible and easy to run it also in 1xH100 or even a A100/T4 by twicking the params.

```
make run-all
```

### Qwen3-8B

`make run-eval SCENARIOS=decision_making,cyber MODEL_NAME="Qwen/Qwen3-8B" MODEL_PARENT="Qwen3-8B" MAX_MODEL_LEN=17000` 

Abliterated

`make run-eval SCENARIOS=decision_making,cyber MODEL_NAME="Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1" MODEL_PARENT="Qwen3-8B" MAX_MODEL_LEN=20000` 

Step by step:
`vllm serve Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1 --tensor-parallel-size 1 --gpu-memory-utilization 0.95 --max-model-len 12000 --enable-auto-tool-choice --tool-call-parser hermes`
`uv run python scripts/run_eval.py --scenarios decision-making`


### Mistral-8B

```
make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="mistralai/Ministral-8B-Instruct-2410" MODEL_PARENT="Mistral-8B" TOOL_CALL_PARSER="mistral" LOAD_FORMAT="mistral" CONFIG_FORMAT="mistral" TOKENIZER_MODE="mistral" EXTRA_BODY='{}'
``` 

Step by step:
`vllm serve mistralai/Ministral-8B-Instruct-2410 --tensor-parallel-size 1 --gpu-memory-utilization 0.95 --max-model-len 12000 --enable-auto-tool-choice --tool-call-parser mistral --load-format mistral --config-format mistral`
`uv run python scripts/run_eval.py --scenarios decision-making --model-name mistralai/Ministral-8B-Instruct-2410 --model-parent Mistral-8B`

### Deepseek

make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="deepseek-ai/DeepSeek-R1-Distill-Llama-70B" MODEL_PARENT="DeepSeek-R1-70B" TOOL_CALL_PARSER="deepseek_v31" MAX_MODEL_LEN=4096 GPU_MEMORY_UTILIZATION=0.8 MAX_NUM_BATCHED_TOKENS=256 EXTRA_BODY='{}' ENFORCE_EAGER=true

vllm serve deepseek-ai/DeepSeek-R1-Distill-Llama-70B
    --enable-auto-tool-choice 
    --tool-call-parser deepseek_v31 
    --max-model-len 4096 --gpu-memory-utilization 0.8 --max-num-batched-tokens 256

deepseek-ai/DeepSeek-R1-Distill-Llama-70B

vllm serve cerebras/MiniMax-M2-REAP-162B-A10B \
    --tensor-parallel-size 8 \
    --tool-call-parser minimax_m2 \
    --reasoning-parser minimax_m2_append_think \
    --trust-remote-code \
    --enable_expert_parallel \
    --enable-auto-tool-choice --gpu-memory-utilization 0.8 --max-model-len 4096  
### GTP-OSS

```
make run-eval SCENARIOS=decision-making,cyber MODEL_NAME="openai/gpt-oss-120b" MODEL_PARENT="gptoss-120B" TOOL_CALL_PARSER="openai" EXTRA_BODY='{}'
```

Abliterated

```
make run-eval SCENARIOS=decision-making,cyber MODEL_NAME="kldzj/gpt-oss-120b-heretic" MODEL_PARENT="gptoss-120B" TOOL_CALL_PARSER="openai" EXTRA_BODY='{}'
```

Step by step:
```
vllm serve kldzj/gpt-oss-120b-heretic-v2-bf16 --tensor-parallel-size 2 --tool-call-parser openai --enable-auto-tool-choice --max-model-len 4096 --gpu-memory-utilization 0.8 --max-num-batched-tokens 256

uv run python scripts/run_eval.py --scenarios decision-making --model-name openai/gpt-oss-120b --model-parent gtposs-120B
```

## App

The app serves the database created after running the evaluations. It uses the same repository to retrieve overall stats and experiment runs.

`uv run streamlit run app/app.py`