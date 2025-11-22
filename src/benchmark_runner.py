import torch
import gc
from transformers import AutoTokenizer, AutoModelForCausalLM

from typing import Dict, Any, TypedDict, Union
from datasets import Dataset, DatasetDict



BootstrapingParams = TypedDict('BootstrapingParams', {'num_runs': int})


def _is_vllm_model(model) -> bool:
    """Check if model is a vLLM LLM instance."""
    from vllm import LLM, SamplingParams

    return isinstance(model, LLM)


def _convert_to_sampling_params(model_params: Union[Dict[str, Any], Any]) -> Any:
    """Convert HF-style model_params to vLLM SamplingParams.
    
    If model_params is already a SamplingParams object, return it as-is.
    Otherwise, convert the dict to SamplingParams with parameter name mapping.
    """    
    from vllm import LLM, SamplingParams

    # If already a SamplingParams object, return as-is
    if isinstance(model_params, SamplingParams):
        return model_params
    
    # Create a copy to avoid modifying the original
    vllm_params = model_params.copy()
    
    # Handle parameter name mapping
    if "max_new_tokens" in vllm_params:
        vllm_params["max_tokens"] = vllm_params.pop("max_new_tokens")
    elif "max_length" in vllm_params and "max_tokens" not in vllm_params:
        vllm_params["max_tokens"] = vllm_params.pop("max_length")
    
    # Remove parameters that don't apply to vLLM or need special handling
    # vLLM doesn't use input_ids/attention_mask, so we can ignore those
    vllm_params.pop("input_ids", None)
    vllm_params.pop("attention_mask", None)
    
    return SamplingParams(**vllm_params)

def _generate_batch(batch, model, tokenizer, device, model_params, run_id=0):
    # HuggingFace path: tokenize and generate
    inputs = tokenizer(
        batch["input_template"],
        padding=True,
        truncation=True,
        return_tensors="pt"
    ).to(device)
    
    try:
        with torch.no_grad():
            outputs = model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                **model_params
            )
        decoded = [
            tokenizer.decode(o, skip_special_tokens=True)
            for o in outputs
        ]
    finally:
        # Explicitly delete tensors to free GPU memory
        del inputs
        del outputs
    batch[f"output_{run_id}"] = decoded
    return batch

def run_benchmark( #TODO: improve interface
    ds,
    model,
    tokenizer,
    device=None,
    model_params=None,
    input_key="messages",
    top_n=None,
    boostraping_params: BootstrapingParams | None = None,
    batch_size: int = 32
):
    # Apply top_n selection once at the beginning
    if top_n:
        ds = ds.select(range(top_n))
    
    # Set default model_params once
    if model_params is None:
        model_params = {
            "max_new_tokens": 30,
            "temperature": 0.1,
        }
    
    # 1. Apply chat template once (outside the loop)
    def apply_template(batch):
        batch["input_template"] = [
            tokenizer.apply_chat_template(msg, tokenize=False, add_generation_prompt=True, disable_thinking=False)
            for msg in batch[input_key]
        ]
        return batch
    ds = ds.map(apply_template, batched=True)
    
    # 2. Generate for each run
    num_runs = boostraping_params['num_runs'] if boostraping_params is not None else 1
    for run in range(num_runs):
        print(f"Running benchmark for run {run}")
        if _is_vllm_model(model):
            # vLLM path: use SamplingParams and string prompts
            sampling_params = _convert_to_sampling_params(model_params)
            outputs = model.generate(
                ds["input_template"],
                sampling_params
            )
            # Extract text from vLLM output format
            decoded = [
                output.outputs[0].text for output in outputs
            ]
            ds = ds.add_column(f"output_{run}", decoded)
        else:
            ds = ds.map(lambda batch: _generate_batch(batch, model, tokenizer, device, model_params, run_id=run), batched=True, batch_size=batch_size)
        
        # Clear CUDA cache and run garbage collection after each run
        if not _is_vllm_model(model) and torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    return ds
