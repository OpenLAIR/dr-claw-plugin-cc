# infra-skills — ML/Scientific Computing Skills for Claude Code

A collection of 81 ML infrastructure and scientific computing skills organized into 20 categories. These skills provide expert guidance for PyTorch, DeepSpeed, vLLM, RLHF, distributed training, model optimization, and more.

## Installation

These skills are designed to be installed per-project via the `infra-skills` meta-skill:

```bash
# In any project directory, invoke:
/infra-skills              # Install all 81 skills
/infra-skills fine-tuning  # Install only fine-tuning skills
/infra-skills inference rag  # Install specific categories
```

The meta-skill symlinks the relevant skills into your project's `.claude/skills/` directory.

## Categories

| # | Category | Skills | Description |
|---|----------|--------|-------------|
| 01 | Model Architecture | litgpt, mamba, nanogpt, rwkv, torchtitan | LLM architectures and implementations |
| 02 | Tokenization | huggingface-tokenizers, sentencepiece | Text tokenization frameworks |
| 03 | Fine-Tuning | axolotl, llama-factory, peft, unsloth | Parameter-efficient and full fine-tuning |
| 04 | Mechanistic Interpretability | nnsight, pyvene, saelens, transformer-lens | Neural network interpretability tools |
| 05 | Data Processing | nemo-curator, ray-data | Scalable data curation and processing |
| 06 | Post-Training | grpo-rl-training, miles, openrlhf, simpo, slime, torchforge, trl-fine-tuning, verl | RLHF, DPO, PPO, and alignment training |
| 07 | Safety & Alignment | constitutional-ai, llamaguard, nemo-guardrails, prompt-guard | LLM safety and content moderation |
| 08 | Distributed Training | accelerate, deepspeed, megatron-core, pytorch-fsdp2, pytorch-lightning, ray-train | Multi-GPU and multi-node training |
| 09 | Infrastructure | lambda-labs, modal, skypilot | GPU cloud and compute orchestration |
| 10 | Optimization | awq, bitsandbytes, flash-attention, gguf, gptq, hqq | Quantization and inference optimization |
| 11 | Evaluation | bigcode-evaluation-harness, lm-evaluation-harness, nemo-evaluator | Model benchmarking and evaluation |
| 12 | Inference & Serving | llama-cpp, sglang, tensorrt-llm, vllm | Production LLM serving |
| 13 | MLOps | mlflow, tensorboard, weights-and-biases | Experiment tracking and model management |
| 14 | Agents | autogpt, crewai, langchain, llamaindex | AI agent frameworks |
| 15 | RAG | chroma, faiss, pinecone, qdrant, sentence-transformers | Vector databases and retrieval |
| 16 | Prompt Engineering | dspy, guidance, instructor, outlines | Structured generation and prompt optimization |
| 17 | Observability | langsmith, phoenix | LLM application monitoring |
| 18 | Multimodal | audiocraft, blip-2, clip, llava, segment-anything, stable-diffusion, whisper | Vision, audio, and multimodal models |
| 19 | Emerging Techniques | knowledge-distillation, long-context, model-merging, model-pruning, moe-training, speculative-decoding | Advanced optimization and scaling |
| 20 | ML Paper Writing | templates, references | Publication-ready ML paper writing |

## Source

These skills are maintained in `~/.orchestra/skills/` and published here for version control and sharing.
