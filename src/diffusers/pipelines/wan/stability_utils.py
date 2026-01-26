"""
Stability Analysis Utilities for Video Editing

This module provides functions to identify stable (non-edited) regions in video
during the inference process, based on x0 prediction history.
"""

import logging

import cv2
import numpy as np
import torch
from scipy import ndimage


def refine_mask(mask, kernel_size=3, remove_small_objects=True, min_object_size=50, fill_holes=True):
    """
    优化二值mask，使用形态学操作让mask更干净连续

    Args:
        mask: (H, W) bool or float tensor
        kernel_size: 形态学操作的kernel大小（默认3，适合小图像）
        remove_small_objects: 是否移除小的孤立区域（默认True）
        min_object_size: 最小保留的对象大小（默认50像素）
        fill_holes: 是否填充空洞（默认True）

    Returns:
        refined_mask: (H, W) bool tensor (same device as input)
    """
    # 记住原始device和dtype
    if torch.is_tensor(mask):
        original_device = mask.device
        mask_np = mask.cpu().numpy().astype(np.uint8)
    else:
        original_device = None
        mask_np = np.array(mask).astype(np.uint8)

    # 确保是二值的 (0 or 1)
    mask_np = (mask_np > 0.5).astype(np.uint8)

    # 1. 闭运算（先膨胀后腐蚀）：填充小空洞，连接邻近区域
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    mask_closed = cv2.morphologyEx(mask_np, cv2.MORPH_CLOSE, kernel)

    # 2. 开运算（先腐蚀后膨胀）：去除小噪声点
    mask_opened = cv2.morphologyEx(mask_closed, cv2.MORPH_OPEN, kernel)

    # 3. 移除小的孤立区域
    if remove_small_objects:
        # 连通域分析
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask_opened, connectivity=8)

        # 保留足够大的区域
        mask_filtered = np.zeros_like(mask_opened)
        for i in range(1, num_labels):  # 跳过背景(label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_object_size:
                mask_filtered[labels == i] = 1

        mask_opened = mask_filtered

    # 4. 填充内部空洞
    if fill_holes:
        mask_filled = ndimage.binary_fill_holes(mask_opened).astype(np.uint8)
    else:
        mask_filled = mask_opened

    # 转换回torch tensor，并保持在原始device上
    refined_mask = torch.from_numpy(mask_filled).bool()
    if original_device is not None:
        refined_mask = refined_mask.to(original_device)

    return refined_mask


def online_stability_check(x0_predictions, current_step, window_start=10, frame_idx=10):
    """
    在线稳定性检测：在推理过程中实时评估稳定性（基于方差）

    Args:
        x0_predictions: list of (B, C, T, H, W) tensors，到目前为止的所有预测
        current_step: 当前步骤（例如13）
        window_start: 从哪一步开始计算方差（默认10）
        frame_idx: 分析哪一帧

    Returns:
        stability_map: (H, W) 稳定性图，基于 [window_start, current_step] 的方差
    """
    if current_step < window_start:
        raise ValueError(f"current_step ({current_step}) must >= window_start ({window_start})")

    # 提取指定帧
    x0_predictions_frame = [x[:, :, frame_idx, :, :] for x in x0_predictions]

    # 只使用 window_start 到 current_step 的数据
    x0_window = x0_predictions_frame[window_start : current_step + 1]

    if len(x0_window) < 2:
        raise ValueError(f"Need at least 2 steps, got {len(x0_window)}")

    # 计算这个窗口内的方差
    x0_stack = torch.stack(x0_window, dim=0)  # (N, B, C, H, W)
    variance = torch.var(x0_stack, dim=0)  # (B, C, H, W)
    variance = variance.mean(dim=1)[0]  # (H, W) - 平均通道，移除batch

    # 归一化：低方差 = 高稳定性
    variance_norm = (variance - variance.min()) / (variance.max() - variance.min() + 1e-8)
    stability_map = 1.0 - variance_norm

    return stability_map


def online_direct_cumulative_change(x0_predictions, current_step, window_start=10, frame_idx=10):
    """
    在线稳定性检测：使用净变化量

    直接比较 current_step 和 window_start 的差异
    变化小 = 稳定（背景），变化大 = 不稳定（编辑区域）
    """
    if current_step <= window_start:
        raise ValueError(f"current_step ({current_step}) must > window_start ({window_start})")

    # 提取指定帧
    x0_predictions_frame = [x[:, :, frame_idx, :, :] for x in x0_predictions]

    # 直接计算净变化（更高效，更符合稳定性定义）
    net_change = torch.norm(x0_predictions_frame[current_step] - x0_predictions_frame[window_start], dim=1)[
        0
    ]  # (H, W)

    # 归一化
    change_norm = (net_change - net_change.min()) / (net_change.max() - net_change.min() + 1e-8)
    stability_map = 1.0 - change_norm

    return stability_map


def velocity_based_stability(
    velocity_list,
    current_step,
    window_start=10,
    frame_idx=0,
    mode="direction_consistency",  # 新: 'average_norm' (norm平均), 'cumulative_norm' (norm累积), 'direction_consistency' (方向一致性, 类似R²)
    normalize=True,
):
    """
    改进的 velocity 稳定性，融入轨迹方向一致性
    """
    if current_step < window_start:
        raise ValueError(f"current_step ({current_step}) must >= window_start ({window_start})")

    # 提取帧的 velocity 历史: list of (C, H, W)
    v_predictions_frame = [v[0, :, frame_idx, :, :] for v in velocity_list[window_start : current_step + 1]]
    num_steps = len(v_predictions_frame)
    if num_steps < 2:
        raise ValueError("Need at least 2 steps for multi-step modes")

    if mode == "average_norm":  # 平均 norm（简单，解决单步不准）
        v_stack = torch.stack(v_predictions_frame, dim=0)  # (N, C, H, W)
        v_norms = torch.norm(v_stack, dim=1)  # (N, H, W)
        metric = v_norms.mean(dim=0)  # (H, W)

    elif mode == "cumulative_norm":  # 累积 norm 变化（类似你的cumulative change）
        cumulative = torch.zeros_like(v_predictions_frame[0][0])  # (H, W)
        for i in range(1, num_steps):
            diff_norm = torch.norm(v_predictions_frame[i] - v_predictions_frame[i - 1], dim=0)
            cumulative += diff_norm
        metric = cumulative

    elif mode == "direction_consistency":  # 方向一致性（类似R²，直线轨迹=高sim）
        # 向量化计算所有像素的方向一致性（完全在GPU上）
        v_stack = torch.stack(v_predictions_frame, dim=0)  # (N, C, H, W)
        N, C, H, W = v_stack.shape

        # 重塑为 (H*W, N, C) 方便批量计算
        v_reshaped = v_stack.permute(2, 3, 0, 1).reshape(H * W, N, C)  # (H*W, N, C)

        # 批量计算 cosine similarity (完全向量化，GPU上)
        # 1. 计算每个向量的 norm: (H*W, N)
        v_norms = torch.norm(v_reshaped, dim=2, keepdim=True)  # (H*W, N, 1)

        # 2. normalize 避免除零
        v_normalized = v_reshaped / (v_norms + 1e-8)  # (H*W, N, C)

        # 3. 批量计算 cosine similarity matrix: (H*W, N, C) @ (H*W, C, N) -> (H*W, N, N)
        sim_matrices = torch.bmm(v_normalized, v_normalized.transpose(1, 2))  # (H*W, N, N)

        # 4. 计算每个像素的平均 similarity (排除对角线)
        # sim_matrices.sum(dim=(1,2)) 是所有元素和，减去对角线 N 个 1.0
        consistency_scores = (sim_matrices.sum(dim=(1, 2)) - N) / (N * (N - 1))  # (H*W,)

        # 5. 处理零向量情况（norm接近0的设为1.0表示完全一致）
        zero_mask = v_norms.squeeze(-1).sum(dim=1) < 1e-6  # (H*W,) 所有步都是零向量
        consistency_scores[zero_mask] = 1.0

        # 重塑回 (H, W)
        consistency_map = consistency_scores.reshape(H, W)
        metric = 1.0 - consistency_map  # 低一致=不稳定（反转，像norm）

    else:
        raise ValueError(f"Unknown mode: {mode}")

    if normalize:
        metric = (metric - metric.min()) / (metric.max() - metric.min() + 1e-8)

    stability_map = 1.0 - metric  # 高stability = 稳定
    return stability_map


def online_cumulative_change(x0_predictions, current_step, window_start=10, frame_idx=10):
    """
    在线稳定性检测：使用累积变化量（推荐方法）

    这个方法计算从window_start到current_step之间，每一步的变化累积和。
    变化小 = 稳定（背景），变化大 = 不稳定（编辑区域）

    Args:
        x0_predictions: list of (B, C, T, H, W) tensors，到目前为止的所有预测
        current_step: 当前步骤（例如13）
        window_start: 从哪一步开始累积变化（默认10）
        frame_idx: 分析哪一帧

    Returns:
        stability_map: (H, W) 稳定性图，值越高越稳定
    """
    if current_step < window_start + 1:
        raise ValueError(f"current_step ({current_step}) must > window_start ({window_start})")

    # 提取指定帧
    x0_predictions_frame = [x[:, :, frame_idx, :, :] for x in x0_predictions]

    # 累积从window_start之后的所有变化
    cumulative_change = torch.zeros_like(x0_predictions_frame[0][0, 0])  # (H, W)

    for i in range(window_start + 1, current_step + 1):
        # 计算第i步与第i-1步的差异
        diff = torch.norm(x0_predictions_frame[i] - x0_predictions_frame[i - 1], dim=1)[0]
        cumulative_change += diff

    # 归一化：累积变化小 = 稳定
    change_norm = (cumulative_change - cumulative_change.min()) / (
        cumulative_change.max() - cumulative_change.min() + 1e-8
    )
    stability_map = 1.0 - change_norm

    return stability_map


def online_stability_mask(
    input_list, current_step, window_start=10, frame_idx=10, threshold=0.5, return_stats=False, method="cumulative"
):
    """
    在线稳定性检测（返回二值mask）- 适合直接用于推理

    Args:
        input_list: list of (B, C, T, H, W) tensors
        current_step: 当前步骤
        window_start: 从哪一步开始计算
        frame_idx: 分析哪一帧
        threshold: 二值化阈值（默认0.5）
        return_stats: 是否返回统计信息
        method: 'cumulative' (推荐) 或 'variance'

    Returns:
        stable_mask: (H, W) bool tensor，True=稳定区域，False=不稳定区域
        如果 return_stats=True，还返回 dict 包含更多信息

    Example:
        # 在推理中使用（推荐累积变化方法）
        stable_mask = online_stability_mask(x0_history[:14], current_step=13, method='cumulative')
        # 对稳定区域和不稳定区域采用不同策略
        edited_regions = ~stable_mask  # 不稳定区域 = 可能的编辑区域
    """
    # 根据方法选择计算函数
    if method == "cumulative":
        # input_list is a list of x0 tensors
        stability_map = online_cumulative_change(input_list, current_step, window_start, frame_idx)
    elif method == "variance":
        # input_list is a list of x0 tensors
        stability_map = online_stability_check(input_list, current_step, window_start, frame_idx)
    elif method == "velocity":
        # input_list is a list of velocity tensors
        stability_map = velocity_based_stability(input_list, current_step, window_start, frame_idx)
    else:
        raise ValueError(f"Unknown method: {method}. Use 'cumulative' or 'variance'")

    stable_mask = stability_map > threshold  # True = stable, False = unstable

    if return_stats:
        stable_pct = stable_mask.float().mean().item() * 100
        unstable_pct = 100 - stable_pct

        stats = {
            "stability_map": stability_map,
            "stable_mask": stable_mask,
            "stable_percentage": stable_pct,
            "unstable_percentage": unstable_pct,
            "mean_stability": stability_map.mean().item(),
            "std_stability": stability_map.std().item(),
            "method": method,
        }
        return stable_mask, stats

    return stable_mask


def get_selected_tokens(
    input_list,
    current_step,
    window_start=8,
    threshold=0.9,
    kernel_size=3,
    remove_small_objects=False,
    min_object_size=50,
    fill_holes=True,
    method="cumulative",
    refresh_kv_steps=[100],
    init_kv_step=100,
    return_stats=False,
):
    """
    在推理过程中识别稳定的tokens（非编辑区域）

    这是一个封装好的函数，用于在pipeline中调用，判断哪些token是非编辑部分。
    基于x0预测的历史数据，通过在线稳定性分析识别出稳定区域（背景）和编辑区域。

    Args:
        input_list: list of (B, C, T, H, W) tensors，历史x0预测
        current_step: int，当前推理步骤
        window_start: int，从哪一步开始分析（默认8）
        threshold: float，稳定性阈值（默认0.9，越高越严格）
        kernel_size: int，形态学操作kernel大小（默认3，对68x90小图像适用）
        remove_small_objects: bool，是否移除小孤立区域（默认True）
        min_object_size: int，最小保留对象大小（默认50像素）
        fill_holes: bool，是否填充空洞（默认True）
        method: str，'cumulative'（推荐）或'variance'
        return_stats: bool，是否返回详细统计信息（默认False）

    Returns:
        stable_masks: list of (H, W) bool tensors，每帧的稳定区域mask
                     True = 稳定区域（非编辑部分）
                     False = 不稳定区域（编辑部分）
        如果 return_stats=True，还返回 list of dict 包含每帧的详细信息

    Usage in Pipeline:
        # 在推理的某一步（例如step 13），获取稳定区域mask
        stable_masks = get_stable_tokens_mask(
            x0_predictions=x0_history[:14],  # 到当前步的所有预测
            current_step=13,
            window_start=8,
            threshold=0.9,
            kernel_size=3  # 对小图像使用小kernel
        )

        # 对每一帧应用不同的处理策略
        for frame_idx, stable_mask in enumerate(stable_masks):
            # stable_mask: True=背景（稳定），False=编辑区域（不稳定）
            edited_mask = ~stable_mask  # 编辑区域
            # 对编辑区域和稳定区域采用不同的guidance策略
    """
    # 确定比较起点：如果是 init_kv_step 则使用 window_start，否则使用上一个 refresh_kv_step
    if current_step == init_kv_step:
        comparison_start = window_start
    else:
        # 找到上一个 refresh_kv_step（最近的且小于 current_step 的）
        previous_refresh_steps = [step for step in refresh_kv_steps if step < current_step]
        if previous_refresh_steps:
            comparison_start = max(previous_refresh_steps)
        else:
            # 如果没有找到上一个 refresh_kv_step，使用 window_start 作为备选
            comparison_start = window_start
    logging.info(
        f"[get_selected_tokens] method: {method} comparison_start: {comparison_start} current_step: {current_step} window_start: {window_start}"
    )
    if current_step < comparison_start:
        raise ValueError(f"current_step ({current_step}) must >= comparison_start ({comparison_start})")

    if len(input_list) < current_step + 1:
        raise ValueError(f"Need at least {current_step + 1} predictions, got {len(input_list)}")

    # 获取帧数
    num_frames = input_list[0].shape[2]  # T dimension

    # 收集所有帧的稳定区域mask
    edited_masks_list = []
    # all_stats = [] if return_stats else None

    for frame_idx in range(num_frames):
        # 1. 使用在线稳定性检测获取原始mask, stable_mask: True = stable, False = unstable
        stable_mask, stats = online_stability_mask(
            input_list,
            current_step=current_step,
            window_start=comparison_start,
            frame_idx=frame_idx,
            threshold=threshold,
            return_stats=True,
            method=method,
        )

        # 2. 优化mask：去噪、平滑、填充空洞
        # 注意：online_stability_mask返回的stable_mask是True=稳定
        # 我们要refine的是编辑区域（~stable_mask），然后再反转回来
        edited_mask_raw = ~stable_mask
        edited_mask_refined = refine_mask(
            edited_mask_raw,
            kernel_size=kernel_size,
            remove_small_objects=remove_small_objects,
            min_object_size=min_object_size,
            fill_holes=fill_holes,
        )

        # 反转回稳定区域mask
        # stable_mask_refined = ~edited_mask_refined

        # 保存（必须clone避免引用问题）
        edited_masks_list.append(edited_mask_refined.clone())

    for i in range(len(edited_masks_list)):
        edited_masks_list[i] = edited_masks_list[i].unsqueeze(0)
    edited_masks = torch.stack(edited_masks_list, dim=1).float()
    torch.save(edited_masks, f"masks_{current_step}.pt")

    mask = torch.nn.functional.max_pool2d(edited_masks, kernel_size=2, stride=2)
    # torch.save(mask, f"masks_{current_step}.pt")
    mask = mask.flatten()
    selected_tokens = torch.nonzero(mask).flatten()  # True = edited, False = stable

    return selected_tokens
