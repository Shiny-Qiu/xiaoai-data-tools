from __future__ import annotations

import io
import os
import random
import zipfile
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import pandas as pd
from django.core.files.uploadedfile import UploadedFile

from .forms import (
    ASSIGNMENT_REQUIRED_COLUMNS,
    REQUIRED_SORT_COLUMNS,
    TOPIC_ORDER_ORIGINAL,
    TOPIC_ORDER_RANDOM,
    TOPIC_ORDER_ROW_COUNT,
    TOPIC_ORDER_TOPIC,
    TOPIC_REQUIRED_COLUMNS,
)


@dataclass
class FileProcessResult:
    input_filename: str
    success: bool
    input_rows: int = 0
    output_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class BatchProcessResult:
    results: List[FileProcessResult]
    zip_bytes: Optional[bytes] = None

    @property
    def total_files(self):
        return len(self.results)

    @property
    def success_files(self):
        return sum(1 for item in self.results if item.success)

    @property
    def failed_files(self):
        return sum(1 for item in self.results if not item.success)

    @property
    def total_output_files(self):
        return sum(len(item.output_files) for item in self.results)

    @property
    def has_warning(self):
        return any(item.warnings for item in self.results)


def read_uploaded_file(uploaded_file: UploadedFile) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    uploaded_file.seek(0)
    if name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    if name.endswith(('.xls', '.xlsx')):
        return pd.read_excel(uploaded_file)
    raise ValueError(f'不支持的文件格式: {uploaded_file.name}')


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer.read()


def build_zip_bytes(output_payloads: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, payload in output_payloads:
            archive.writestr(name, payload)
    buffer.seek(0)
    return buffer.read()


def build_session_output_name(source_name: str, index: int, total: int) -> str:
    base_name, _ = os.path.splitext(source_name)
    if total == 1:
        return f'{base_name}_整理后.xlsx'
    return f'{base_name}_整理后_{index}.xlsx'


def build_topic_output_name(source_name: str) -> str:
    base_name, _ = os.path.splitext(source_name)
    return f'{base_name}_处理结果.xlsx'


def split_dataframe(df: pd.DataFrame, chunk_size: int):
    if chunk_size <= 0:
        raise ValueError('chunk_size 必须大于 0')
    if df.empty:
        return [df]
    return [df.iloc[start:start + chunk_size].copy() for start in range(0, len(df), chunk_size)]


def sort_session_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    working = df.copy()
    missing_required = [col for col in REQUIRED_SORT_COLUMNS if col not in working.columns]
    if missing_required:
        raise ValueError('缺少排序必需列：' + ', '.join(missing_required))

    timestamp_series = pd.to_datetime(working['timestamp'], errors='coerce')
    has_invalid_timestamp = timestamp_series.isna().any()
    working['__sort_timestamp__'] = timestamp_series
    working = working.sort_values(
        by=['add_session_id', '__sort_timestamp__', 'timestamp'],
        kind='mergesort',
        na_position='last'
    )
    working = working.drop(columns=['__sort_timestamp__'])
    return working.reset_index(drop=True), bool(has_invalid_timestamp)


def process_single_session_file(uploaded_file: UploadedFile, target_columns, chunk_size: int, missing_column_mode: str):
    result = FileProcessResult(input_filename=uploaded_file.name, success=False)
    try:
        df = read_uploaded_file(uploaded_file)
        result.input_rows = len(df)

        missing_columns = [col for col in target_columns if col not in df.columns]
        if missing_columns:
            if missing_column_mode == 'strict':
                result.errors.append('以下目标列在输入文件中缺失：' + ', '.join(missing_columns))
                return [], result
            for col in missing_columns:
                df[col] = ''
            result.warnings.append('以下目标列缺失，已按空值补齐：' + ', '.join(missing_columns))

        normalized_df = df[target_columns].copy()
        sorted_df, has_invalid_timestamp = sort_session_dataframe(normalized_df)
        if has_invalid_timestamp:
            result.warnings.append('timestamp 列部分值无法解析，已排在最后。')

        chunks = split_dataframe(sorted_df, chunk_size)
        output_files = []
        for idx, chunk in enumerate(chunks, start=1):
            output_name = build_session_output_name(uploaded_file.name, idx, len(chunks))
            output_files.append((output_name, dataframe_to_excel_bytes(chunk)))
            result.output_files.append(output_name)

        result.success = True
        return output_files, result
    except Exception as exc:
        result.errors.append(str(exc))
        return [], result


def order_topic_ids(candidate_df: pd.DataFrame, topic_order_mode: str):
    topic_df = candidate_df.copy()
    if topic_df.empty:
        return []

    topic_df['__topic_id_str__'] = topic_df['topic_id'].astype(str)

    if topic_order_mode == TOPIC_ORDER_ROW_COUNT:
        topic_counts = topic_df['__topic_id_str__'].value_counts()
        return topic_counts.sort_values(ascending=True).index.tolist()

    if topic_order_mode == TOPIC_ORDER_RANDOM:
        unique_topic_ids = topic_df['__topic_id_str__'].drop_duplicates().tolist()
        random.shuffle(unique_topic_ids)
        return unique_topic_ids

    if topic_order_mode == TOPIC_ORDER_ORIGINAL:
        return topic_df['__topic_id_str__'].drop_duplicates().tolist()

    unique_topic_ids = sorted(topic_df['__topic_id_str__'].drop_duplicates().tolist())
    return unique_topic_ids


def apply_topic_rules(df: pd.DataFrame, target_date: str, retain_rules, cross_domain_retain_count: int, topic_order_mode: str):
    working = df.copy()
    try:
        working['__target_date__'] = pd.to_datetime(working['标注日期'], errors='coerce').dt.strftime('%Y-%m-%d')
    except Exception:
        working['__target_date__'] = working['标注日期'].astype(str).str.split().str[0]

    working['是否废除'] = '是'
    messages = []

    date_mask_all = working['__target_date__'] == target_date
    target_date_df = working.loc[date_mask_all].copy()

    if not date_mask_all.any():
        messages.append(f'文件中没有找到日期为 {target_date} 的数据')

    invalid_topic_ids = target_date_df.groupby('topic_id')['query有效性'].apply(
        lambda series: series.eq('不参评query').all()
    ) if not target_date_df.empty else pd.Series(dtype=bool)
    invalid_topic_ids = set(invalid_topic_ids[invalid_topic_ids].index.astype(str).tolist())

    if invalid_topic_ids:
        messages.append(
            f'日期 {target_date} 下发现 {len(invalid_topic_ids)} 个 topic_id 的 query有效性 全部为不参评query，将剔除这些 topic 的所有数据'
        )

    order_mode_label = {
        TOPIC_ORDER_ROW_COUNT: '按行数升序保留',
        TOPIC_ORDER_RANDOM: '随机顺序',
        TOPIC_ORDER_TOPIC: 'topic排序',
        TOPIC_ORDER_ORIGINAL: '原始文档顺序',
    }.get(topic_order_mode, 'topic排序')
    messages.append(f'当前候选topic保留顺序：{order_mode_label}')

    date_mask = date_mask_all & (~working['topic_id'].astype(str).isin(invalid_topic_ids))

    retained_topic_ids = set()

    for (agent_type, topic_type), retain_count in retain_rules.items():
        condition = date_mask & (working['真实细分Agent'] == agent_type) & (working['topic类型'] == topic_type)
        matched_df = working.loc[condition]
        unique_topic_ids = order_topic_ids(matched_df, topic_order_mode)
        current_count = len(unique_topic_ids)

        if current_count < retain_count:
            missing = retain_count - current_count
            messages.append(
                f'⚠️ [不足] 日期 {target_date} 下规则 [{agent_type} - {topic_type}]: 目标 {retain_count}, 实际 {current_count}, 缺少 {missing} 组'
            )
        else:
            messages.append(
                f'规则 [{agent_type} - {topic_type}]: 目标 {retain_count}, 实际 {current_count}, 满足要求'
            )

        selected_topic_ids = unique_topic_ids[:retain_count]
        retained_topic_ids.update(selected_topic_ids)

    cross_condition = date_mask & (working['topic类型'] == '跨垂域topic') & (~working['topic_id'].astype(str).isin(retained_topic_ids))
    cross_df = working.loc[cross_condition]
    unique_cross_topic_ids = order_topic_ids(cross_df, topic_order_mode)
    current_cross_count = len(unique_cross_topic_ids)

    if current_cross_count < cross_domain_retain_count:
        missing = cross_domain_retain_count - current_cross_count
        messages.append(
            f'⚠️ [不足] 日期 {target_date} 下规则 [跨垂域topic]: 目标 {cross_domain_retain_count}, 实际 {current_cross_count} (未被其他覆盖), 缺少 {missing} 组'
        )
    else:
        messages.append(
            f'规则 [跨垂域topic]: 目标 {cross_domain_retain_count}, 实际 {current_cross_count}, 满足要求'
        )

    cross_topic_ids = unique_cross_topic_ids[:cross_domain_retain_count]
    retained_topic_ids.update(cross_topic_ids)

    final_condition = working['topic_id'].astype(str).isin(retained_topic_ids) & date_mask
    working.loc[final_condition, '是否废除'] = '否'
    final_retain_count = int(final_condition.sum())
    messages.append(f"日期 {target_date} 下保留（是否废除='否'）的总行数: {final_retain_count}")

    working.drop(columns=['__target_date__'], inplace=True)
    return working, messages, len(invalid_topic_ids), len(retained_topic_ids)


def process_single_topic_file(
    uploaded_file: UploadedFile,
    target_date: str,
    retain_rules,
    cross_domain_retain_count: int,
    topic_order_mode: str,
):
    result = FileProcessResult(input_filename=uploaded_file.name, success=False)
    try:
        df = read_uploaded_file(uploaded_file)
        result.input_rows = len(df)

        missing_required = [col for col in TOPIC_REQUIRED_COLUMNS if col not in df.columns]
        if missing_required:
            result.errors.append('缺少topic处理必需字段：' + ', '.join(missing_required))
            return [], result

        output_name = build_topic_output_name(uploaded_file.name)
        processed_df, rule_messages, invalid_topic_count, retained_topic_count = apply_topic_rules(
            df,
            target_date=target_date,
            retain_rules=retain_rules,
            cross_domain_retain_count=cross_domain_retain_count,
            topic_order_mode=topic_order_mode,
        )

        result.warnings.extend(rule_messages)
        if not (processed_df['是否废除'] == '否').any():
            result.warnings.append(f'目标日期 {target_date} 下没有命中任何保留topic。')
        result.warnings.append(f'目标日期 {target_date} 下剔除了 {invalid_topic_count} 个 query有效性 全部为不参评query 的topic。')
        result.warnings.append(f'目标日期 {target_date} 下共保留 {retained_topic_count} 个topic。')
        result.warnings.append(f'处理完成，已生成结果文件：{output_name}')

        output_files = [(output_name, dataframe_to_excel_bytes(processed_df))]
        result.output_files.append(output_name)
        result.success = True
        return output_files, result
    except Exception as exc:
        result.errors.append(str(exc))
        return [], result


def process_uploaded_files(
    uploaded_files,
    target_columns,
    chunk_size: int,
    missing_column_mode: str,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> BatchProcessResult:
    results = []
    output_payloads = []
    total_files = len(uploaded_files)

    for index, uploaded_file in enumerate(uploaded_files, start=1):
        if progress_callback:
            progress_callback({
                'status': 'running',
                'stage': 'reading',
                'message': f'正在处理第 {index}/{total_files} 个文件',
                'current_file': uploaded_file.name,
                'completed_files': index - 1,
                'total_files': total_files,
                'percent': int(((index - 1) / max(total_files, 1)) * 100),
            })

        output_files, result = process_single_session_file(
            uploaded_file=uploaded_file,
            target_columns=target_columns,
            chunk_size=chunk_size,
            missing_column_mode=missing_column_mode,
        )
        output_payloads.extend(output_files)
        results.append(result)

        if progress_callback:
            progress_callback({
                'status': 'running',
                'stage': 'finished_file',
                'message': f'已完成第 {index}/{total_files} 个文件',
                'current_file': uploaded_file.name,
                'completed_files': index,
                'total_files': total_files,
                'percent': int((index / max(total_files, 1)) * 100),
                'result_items': [
                    {
                        'input_filename': item.input_filename,
                        'success': item.success,
                        'input_rows': item.input_rows,
                        'output_files': item.output_files,
                        'warnings': item.warnings,
                        'errors': item.errors,
                    }
                    for item in results
                ],
                'summary': {
                    'total_files': len(results),
                    'success_files': sum(1 for item in results if item.success),
                    'failed_files': sum(1 for item in results if not item.success),
                    'total_output_files': sum(len(item.output_files) for item in results),
                    'has_warning': any(item.warnings for item in results),
                },
                'download_ready': False,
            })

    zip_bytes = build_zip_bytes(output_payloads) if output_payloads else None
    return BatchProcessResult(results=results, zip_bytes=zip_bytes)


def process_topic_uploaded_files(
    uploaded_files,
    target_date,
    retain_rules,
    cross_domain_retain_count,
    topic_order_mode,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> BatchProcessResult:
    results = []
    output_payloads = []
    total_files = len(uploaded_files)

    for index, uploaded_file in enumerate(uploaded_files, start=1):
        if progress_callback:
            progress_callback({
                'status': 'running',
                'stage': 'reading',
                'message': f'正在处理第 {index}/{total_files} 个文件',
                'current_file': uploaded_file.name,
                'completed_files': index - 1,
                'total_files': total_files,
                'percent': int(((index - 1) / max(total_files, 1)) * 100),
            })

        output_files, result = process_single_topic_file(
            uploaded_file=uploaded_file,
            target_date=target_date,
            retain_rules=retain_rules,
            cross_domain_retain_count=cross_domain_retain_count,
            topic_order_mode=topic_order_mode,
        )
        output_payloads.extend(output_files)
        results.append(result)

        if progress_callback:
            progress_callback({
                'status': 'running',
                'stage': 'finished_file',
                'message': f'已完成第 {index}/{total_files} 个文件',
                'current_file': uploaded_file.name,
                'completed_files': index,
                'total_files': total_files,
                'percent': int((index / max(total_files, 1)) * 100),
                'result_items': [
                    {
                        'input_filename': item.input_filename,
                        'success': item.success,
                        'input_rows': item.input_rows,
                        'output_files': item.output_files,
                        'warnings': item.warnings,
                        'errors': item.errors,
                    }
                    for item in results
                ],
                'summary': {
                    'total_files': len(results),
                    'success_files': sum(1 for item in results if item.success),
                    'failed_files': sum(1 for item in results if not item.success),
                    'total_output_files': sum(len(item.output_files) for item in results),
                    'has_warning': any(item.warnings for item in results),
                },
                'download_ready': False,
            })

    zip_bytes = build_zip_bytes(output_payloads) if output_payloads else None
    return BatchProcessResult(results=results, zip_bytes=zip_bytes)


def build_assignment_output_name(source_name: str) -> str:
    base_name, _ = os.path.splitext(source_name)
    return f'{base_name}_人力分配结果.xlsx'


def get_topic_info(df_not_abolish: pd.DataFrame, category_time: dict):
    topic_groups = df_not_abolish.groupby('topic_id')
    topics_info = []

    for topic_id, group in topic_groups:
        total_time = 0
        category_details: dict[str, int] = {}

        for _, row in group.iterrows():
            category = row['规范类别']
            if category not in category_time:
                continue
            total_time += category_time[category]
            category_details[category] = category_details.get(category, 0) + 1

        if total_time == 0:
            continue

        topics_info.append({
            'topic_id': topic_id,
            'category_details': category_details,
            'items_count': len(group),
            'total_time': total_time,
        })

    return topics_info


def assign_topics(topics_info, annotators_config, target_minutes):
    annotator_time = {name: 0 for name in annotators_config}
    annotator_topics: dict[str, list] = {name: [] for name in annotators_config}
    max_allowed_time = target_minutes * 1.1
    messages = []

    topic_candidates = []
    for topic in topics_info:
        topic_categories = set(topic['category_details'].keys())
        eligible = [
            name for name, allowed in annotators_config.items()
            if topic_categories.issubset(set(allowed))
        ]
        topic_candidates.append({
            'topic': topic,
            'eligible_annotators': eligible,
            'eligible_count': len(eligible),
        })

    topic_candidates.sort(key=lambda x: (
        x['eligible_count'],
        -x['topic']['total_time'],
        str(x['topic']['topic_id']),
    ))

    assigned_ids: set = set()

    for item in topic_candidates:
        topic = item['topic']
        eligible = item['eligible_annotators']
        cat_info = ', '.join(f"{k}:{v}" for k, v in topic['category_details'].items())

        if not eligible:
            messages.append(
                f"跳过 topic {topic['topic_id']}（类别：[{cat_info}]）：无可承接标注员"
            )
            continue

        feasible = []
        for name in eligible:
            new_time = annotator_time[name] + topic['total_time']
            if new_time <= max_allowed_time:
                feasible.append((name, new_time))

        if not feasible:
            messages.append(
                f"跳过 topic {topic['topic_id']}（类别：[{cat_info}]）：分配后超上限"
            )
            continue

        best_name, best_time = min(
            feasible,
            key=lambda x: (
                annotator_time[x[0]],
                x[0],
            ),
        )

        annotator_topics[best_name].append(topic)
        annotator_time[best_name] = best_time
        assigned_ids.add(topic['topic_id'])
        messages.append(
            f"分配 topic {topic['topic_id']}（{topic['total_time']}min）"
            f"→ {best_name}（累计 {best_time}min）"
        )

    for name in annotators_config:
        count = len(annotator_topics[name])
        total = annotator_time[name]
        messages.append(f"标注员 {name}：{count} 个 topic，共 {total}/{target_minutes} 分钟")

    unassigned = [t for t in topics_info if t['topic_id'] not in assigned_ids]
    if unassigned:
        messages.append(f"未分配 topic 数：{len(unassigned)}")

    return annotator_topics, messages


def process_single_assignment_file(
    uploaded_file: UploadedFile,
    category_time: dict,
    annotators_config: dict,
    target_minutes: int,
):
    result = FileProcessResult(input_filename=uploaded_file.name, success=False)
    try:
        df = read_uploaded_file(uploaded_file)
        result.input_rows = len(df)

        missing = [col for col in ASSIGNMENT_REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            result.errors.append('缺少人力分配必需字段：' + ', '.join(missing))
            return [], result

        df_not_abolish = df[df['是否废除'] == '否'].copy()
        if df_not_abolish.empty:
            result.errors.append('没有找到是否废除为"否"的数据')
            return [], result

        topics_info = get_topic_info(df_not_abolish, category_time)
        if not topics_info:
            result.errors.append('没有提取到有效的 topic')
            return [], result

        annotator_topics, messages = assign_topics(
            topics_info, annotators_config, target_minutes,
        )
        result.warnings.extend(messages)

        topic_to_annotator = {}
        for name, topics in annotator_topics.items():
            for topic in topics:
                topic_to_annotator[topic['topic_id']] = name

        df['理想态标注员'] = ''
        for topic_id, annotator in topic_to_annotator.items():
            df.loc[df['topic_id'] == topic_id, '理想态标注员'] = annotator

        output_name = build_assignment_output_name(uploaded_file.name)
        output_files = [(output_name, dataframe_to_excel_bytes(df))]
        result.output_files.append(output_name)
        result.success = True
        return output_files, result
    except Exception as exc:
        result.errors.append(str(exc))
        return [], result


def process_assignment_uploaded_files(
    uploaded_files,
    category_time: dict,
    annotators_config: dict,
    target_minutes: int,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> BatchProcessResult:
    results = []
    output_payloads = []
    total_files = len(uploaded_files)

    for index, uploaded_file in enumerate(uploaded_files, start=1):
        if progress_callback:
            progress_callback({
                'status': 'running',
                'stage': 'reading',
                'message': f'正在处理第 {index}/{total_files} 个文件',
                'current_file': uploaded_file.name,
                'completed_files': index - 1,
                'total_files': total_files,
                'percent': int(((index - 1) / max(total_files, 1)) * 100),
            })

        output_files, result = process_single_assignment_file(
            uploaded_file=uploaded_file,
            category_time=category_time,
            annotators_config=annotators_config,
            target_minutes=target_minutes,
        )
        output_payloads.extend(output_files)
        results.append(result)

        if progress_callback:
            progress_callback({
                'status': 'running',
                'stage': 'finished_file',
                'message': f'已完成第 {index}/{total_files} 个文件',
                'current_file': uploaded_file.name,
                'completed_files': index,
                'total_files': total_files,
                'percent': int((index / max(total_files, 1)) * 100),
                'result_items': [
                    {
                        'input_filename': item.input_filename,
                        'success': item.success,
                        'input_rows': item.input_rows,
                        'output_files': item.output_files,
                        'warnings': item.warnings,
                        'errors': item.errors,
                    }
                    for item in results
                ],
                'summary': {
                    'total_files': len(results),
                    'success_files': sum(1 for item in results if item.success),
                    'failed_files': sum(1 for item in results if not item.success),
                    'total_output_files': sum(len(item.output_files) for item in results),
                    'has_warning': any(item.warnings for item in results),
                },
                'download_ready': False,
            })

    zip_bytes = build_zip_bytes(output_payloads) if output_payloads else None
    return BatchProcessResult(results=results, zip_bytes=zip_bytes)
