from __future__ import annotations

import pandas as pd
from clearml import Task

from utils.metrics import compute_metrics, KS

_SCALAR_KEYS = [
    'video_mrr',
    'video_map',
    'ndcg@10',
    'video_f1@5',
    'mean_iou',
    'mean_iou@top1',
    'mean_iou@top5',
    'moment_mrr@iou03',
    'moment_mrr@iou05',
    'moment_mrr@iou07',
]

_CURVES = [
    ('Video Recall@K',              'video_recall@{}'),
    ('Video nDCG@K',                'ndcg@{}'),
    ('Video F1@K',                  'video_f1@{}'),
    ('Moment Recall@K IoU>=0.3',    'moment_recall@{}@iou03'),
    ('Moment Recall@K IoU>=0.5',    'moment_recall@{}@iou05'),
    ('Moment Recall@K IoU>=0.7',    'moment_recall@{}@iou07'),
]


def log_experiment(
    task_name: str,
    config_dict: dict,
    results_df: pd.DataFrame,
    annotations: list[dict],
    project_name: str = 'nlv-search',
    extra_params: dict = None,
) -> Task:
    task: Task = Task.create(project_name=project_name, task_name=task_name)

    params = {k: str(v) for k, v in {**config_dict, **(extra_params or {})}.items()}
    task.connect(params)

    logger = task.get_logger()
    metrics = compute_metrics(results_df, annotations)

    for key in _SCALAR_KEYS:
        if key in metrics:
            logger.report_scalar(
                title=key,
                series='score',
                value=metrics[key],
                iteration=0,
            )

    for title, key_tpl in _CURVES:
        for k in KS:
            key = key_tpl.format(k)
            if key in metrics:
                logger.report_scalar(
                    title=title,
                    series='score',
                    value=metrics[key],
                    iteration=k,
                )

    return task
