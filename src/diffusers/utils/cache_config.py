from dataclasses import dataclass, field
from typing import Dict, List
import torch

@dataclass
class CacheConfig:
    init_kv_step: int = 10
    cache_key: Dict[int, torch.Tensor] = field(default_factory=dict)
    cache_value: Dict[int, torch.Tensor] = field(default_factory=dict)
    selected_tokens: torch.Tensor = None
    step: int = 0

    # refresh_kv_steps: List[int] = field(default_factory=lambda: [100])
    refresh_kv_steps: List[int] = field(default_factory=lambda: [20, 30, 40, 45, 46, 47, 48, 49])
    layer_index: int = 0
    enabled: bool = False
