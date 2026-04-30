from __future__ import annotations

import ast

import numpy as np
import pandas as pd

_KS = [1, 2, 3, 5, 10, 15, 20]
KS = _KS


def iou_with_windows(pred_start: float, pred_end: float, gt_windows: list) -> float:
    """Лучший IoU предсказанного сегмента с любым из gt_windows."""
    best = 0.0
    for gs, ge in gt_windows:
        inter = max(0.0, min(pred_end, float(ge)) - max(pred_start, float(gs)))
        if inter == 0.0:
            continue
        union = max(pred_end, float(ge)) - min(pred_start, float(gs))
        best = max(best, inter / union)
    return best


def compute_metrics(
    results_df: pd.DataFrame,
    annotations: list[dict],
    iou_thresholds: list[float] = None,
) -> dict:
    if iou_thresholds is None:
        iou_thresholds = [0.3, 0.5, 0.7]

    ann_by_qid = {a['qid']: a for a in annotations}
    qids = [a['qid'] for a in annotations]

    video_rr, video_aps = [], []
    video_recall_k     = {k: [] for k in _KS}
    video_precision_k  = {k: [] for k in _KS}
    ndcg_k             = {k: [] for k in _KS}
    video_f1_k         = {k: [] for k in _KS}
    moment_hit1        = {t: [] for t in iou_thresholds}
    moment_rr          = {t: [] for t in iou_thresholds}
    moment_recall_k    = {k: {t: [] for t in iou_thresholds} for k in _KS}
    moment_precision_k = {k: {t: [] for t in iou_thresholds} for k in _KS}
    iou_when_correct   = []
    iou_top1_vals      = []
    iou_top5_vals      = []

    for qid in qids:
        ann = ann_by_qid.get(qid)
        if ann is None:
            continue
        gt_vid = ann['vid']
        gt_windows = ann['relevant_windows']

        preds = results_df[results_df['qid'] == qid].sort_values('rank')
        video_correct = (preds['pred_vid'] == gt_vid).values

        for k in _KS:
            top_k = video_correct[:k]
            r = int(top_k.any())
            p = float(top_k.sum()) / k
            video_recall_k[k].append(r)
            video_precision_k[k].append(p)

            # nDCG@K (IDCG = 1.0 для одного релевантного документа)
            dcg = sum(1.0 / np.log2(i + 2) for i, c in enumerate(video_correct[:k]) if c)
            ndcg_k[k].append(dcg)

            # F1@K
            denom = p + r
            video_f1_k[k].append(2 * p * r / denom if denom > 0 else 0.0)

        idx = int(np.argmax(video_correct)) if video_correct.any() else -1
        video_rr.append(1.0 / (idx + 1) if idx >= 0 else 0.0)

        n_hit, aps = 0, []
        for i, c in enumerate(video_correct):
            if c:
                n_hit += 1
                aps.append(n_hit / (i + 1))
        video_aps.append(float(np.mean(aps)) if aps else 0.0)

        ious = np.array([
            iou_with_windows(row['pred_start'], row['pred_end'], gt_windows)
            if row['pred_vid'] == gt_vid else 0.0
            for _, row in preds.iterrows()
        ])

        if video_correct.any():
            iou_when_correct.append(float(ious[video_correct].max()))

        # mean_iou@top1
        if len(preds) > 0:
            top1_row = preds.iloc[0]
            if top1_row['pred_vid'] == gt_vid:
                iou_top1_vals.append(
                    iou_with_windows(top1_row['pred_start'], top1_row['pred_end'], gt_windows)
                )

        # mean_iou@top5
        top5 = preds.iloc[:5]
        correct_top5 = top5[top5['pred_vid'] == gt_vid]
        if not correct_top5.empty:
            ious5 = [
                iou_with_windows(r['pred_start'], r['pred_end'], gt_windows)
                for _, r in correct_top5.iterrows()
            ]
            iou_top5_vals.append(max(ious5))

        for t in iou_thresholds:
            mc = ious >= t
            moment_hit1[t].append(int(mc[0]) if len(mc) > 0 else 0)
            for k in _KS:
                top_k_mc = mc[:k]
                moment_recall_k[k][t].append(int(top_k_mc.any()))
                moment_precision_k[k][t].append(float(top_k_mc.sum()) / k)
            midx = int(np.argmax(mc)) if mc.any() else -1
            moment_rr[t].append(1.0 / (midx + 1) if midx >= 0 else 0.0)

    result = {
        **{f'video_recall@{k}':    float(np.mean(video_recall_k[k]))    for k in _KS},
        **{f'video_precision@{k}': float(np.mean(video_precision_k[k])) for k in _KS},
        **{f'ndcg@{k}':            float(np.mean(ndcg_k[k]))            for k in _KS},
        **{f'video_f1@{k}':        float(np.mean(video_f1_k[k]))        for k in _KS},
        'video_mrr':     float(np.mean(video_rr)),
        'video_map':     float(np.mean(video_aps)),
        'mean_iou':      float(np.mean(iou_when_correct)) if iou_when_correct else 0.0,
        'mean_iou@top1': float(np.mean(iou_top1_vals))   if iou_top1_vals   else 0.0,
        'mean_iou@top5': float(np.mean(iou_top5_vals))   if iou_top5_vals   else 0.0,
    }
    for t in iou_thresholds:
        tstr = str(t).replace('.', '')
        result[f'hit@1@iou{tstr}'] = float(np.mean(moment_hit1[t]))
        result[f'moment_mrr@iou{tstr}'] = float(np.mean(moment_rr[t]))
        for k in _KS:
            result[f'moment_recall@{k}@iou{tstr}']    = float(np.mean(moment_recall_k[k][t]))
            result[f'moment_precision@{k}@iou{tstr}'] = float(np.mean(moment_precision_k[k][t]))
    return result


def per_query_stats(
    results_df: pd.DataFrame,
    annotations: list[dict],
    iou_threshold: float = 0.5,
) -> pd.DataFrame:
    ann_by_qid = {a['qid']: a for a in annotations}
    rows = []

    for (qid, index_type), group in results_df.groupby(['qid', 'index_type']):
        ann = ann_by_qid.get(qid)
        if ann is None:
            continue
        gt_vid = ann['vid']
        gt_windows = ann['relevant_windows']
        query = group.iloc[0]['query']

        preds = group.sort_values('rank')
        top1 = preds.iloc[0]

        correct_mask = preds['pred_vid'] == gt_vid
        first_rank = float(preds[correct_mask].iloc[0]['rank']) if correct_mask.any() else float('inf')

        best_iou = 0.0
        for _, row in preds.iterrows():
            if row['pred_vid'] == gt_vid:
                best_iou = max(best_iou, iou_with_windows(row['pred_start'], row['pred_end'], gt_windows))

        top1_iou = (
            iou_with_windows(top1['pred_start'], top1['pred_end'], gt_windows)
            if top1['pred_vid'] == gt_vid else 0.0
        )

        # iou@top3
        correct_top3 = preds.iloc[:3][preds.iloc[:3]['pred_vid'] == gt_vid]
        iou_top3 = max(
            [iou_with_windows(r['pred_start'], r['pred_end'], gt_windows) for _, r in correct_top3.iterrows()],
            default=0.0,
        )

        # iou@top5
        correct_top5 = preds.iloc[:5][preds.iloc[:5]['pred_vid'] == gt_vid]
        iou_top5 = max(
            [iou_with_windows(r['pred_start'], r['pred_end'], gt_windows) for _, r in correct_top5.iterrows()],
            default=0.0,
        )

        # error_class по top-1 (IoU-порог 0.5)
        if top1['pred_vid'] != gt_vid:
            error_class = 'wrong_vid'
        elif top1_iou >= 0.5:
            error_class = 'correct_vid_correct_moment'
        else:
            error_class = 'correct_vid_wrong_moment'

        rows.append({
            'qid':                      qid,
            'query':                    query,
            'gt_vid':                   gt_vid,
            'index_type':               index_type,
            'first_correct_video_rank': first_rank,
            'best_iou':                 best_iou,
            'top1_vid':                 top1['pred_vid'],
            'top1_score':               float(top1['score']),
            'top1_iou':                 top1_iou,
            'iou@top1':                 top1_iou,
            'iou@top3':                 iou_top3,
            'iou@top5':                 iou_top5,
            'error_class':              error_class,
        })

    return pd.DataFrame(rows)
