import torch
import torch.nn.functional as F
from typing import Union


def cosine_similarity(
    v1: Union[torch.Tensor,list],
    v2: Union[torch.Tensor,list]
) -> float:

    if not isinstance(v1, torch.Tensor):
        v1 = torch.tensor(v1)

    if not isinstance(v2, torch.Tensor):
        v2 = torch.tensor(v2)

    v1 = v1.flatten().float()
    v2 = v2.flatten().float()

    return F.cosine_similarity(
        v1,
        v2,
        dim=0
    ).item()