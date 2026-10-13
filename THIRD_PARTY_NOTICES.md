# Third-party notices

redact-mac is GPL-3.0-or-later. It uses, but does not bundle, the following, each
installed by `install.sh` under its own license:

| Component | Use | License |
|---|---|---|
| [openai/privacy-filter](https://github.com/openai/privacy-filter) (`opf`), commit `f7f00ca` | Tokenization, Viterbi decoding, span logic | Apache-2.0 |
| OpenAI Privacy Filter model weights, via [mlx-community/openai-privacy-filter-bf16](https://huggingface.co/mlx-community/openai-privacy-filter-bf16) | The model | Apache-2.0 |
| [mlx-embeddings](https://github.com/Blaizzy/mlx-embeddings), commit `9b28270` | MLX model implementation | GPL-3.0 |
| [MLX](https://github.com/ml-explore/mlx), [mlx-lm](https://github.com/ml-explore/mlx-lm) | GPU runtime | MIT |
| [PyTorch](https://pytorch.org) | Tensor glue for `opf` | BSD-style / Apache-2.0 |
| [tiktoken](https://github.com/openai/tiktoken) | Tokenizer | MIT |

`engine/opf_checkpoint/config.json` and `viterbi_calibration.json` are copied unchanged
from the OpenAI Privacy Filter checkpoint (Apache-2.0, © OpenAI).

"OpenAI" and "Privacy Filter" are OpenAI's names. This project is independent and not
endorsed by OpenAI.
