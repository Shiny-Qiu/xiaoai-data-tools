import io
import threading
import uuid

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .forms import (
    DEFAULT_ANNOTATORS_CONFIG_TEXT,
    DEFAULT_CATEGORY_TIME_TEXT,
    DEFAULT_CROSS_DOMAIN_RETAIN_COUNT,
    DEFAULT_RETAIN_RULES_TEXT,
    DEFAULT_TARGET_COLUMNS,
    DEFAULT_TARGET_MINUTES,
    DEFAULT_TOPIC_TARGET_DATE,
    JOB_TYPE_ASSIGNMENT,
    JOB_TYPE_SESSION_SORT,
    JOB_TYPE_TOPIC_ABANDON,
    AssignmentForm,
    SessionSortForm,
    TopicAbandonForm,
)
from .services import (
    process_assignment_uploaded_files,
    process_topic_uploaded_files,
    process_uploaded_files,
)


DOWNLOAD_CACHE = {}
TASK_CACHE = {}
TASK_CACHE_LOCK = threading.Lock()


def clone_uploaded_files(uploaded_files):
    cloned_files = []
    for uploaded_file in uploaded_files:
        uploaded_file.seek(0)
        cloned_files.append(
            SimpleUploadedFile(
                name=uploaded_file.name,
                content=uploaded_file.read(),
                content_type=getattr(uploaded_file, 'content_type', None),
            )
        )
    return cloned_files


def build_base_context(session_form=None, topic_form=None, assignment_form=None, active_job_type=JOB_TYPE_SESSION_SORT):
    return {
        'session_form': session_form or SessionSortForm(),
        'topic_form': topic_form or TopicAbandonForm(),
        'assignment_form': assignment_form or AssignmentForm(),
        'active_job_type': active_job_type,
        'summary': None,
        'result_items': [],
        'download_ready': False,
        'download_url': None,
        'default_target_columns': '\n'.join(DEFAULT_TARGET_COLUMNS),
        'default_topic_target_date': DEFAULT_TOPIC_TARGET_DATE,
        'default_cross_domain_retain_count': DEFAULT_CROSS_DOMAIN_RETAIN_COUNT,
        'default_retain_rules_text': DEFAULT_RETAIN_RULES_TEXT,
        'default_category_time_text': DEFAULT_CATEGORY_TIME_TEXT,
        'default_annotators_config_text': DEFAULT_ANNOTATORS_CONFIG_TEXT,
        'default_target_minutes': DEFAULT_TARGET_MINUTES,
    }


def index(request):
    context = build_base_context()
    return render(request, 'sorter/index.html', context)


def build_summary(batch_result):
    return {
        'total_files': batch_result.total_files,
        'success_files': batch_result.success_files,
        'failed_files': batch_result.failed_files,
        'total_output_files': batch_result.total_output_files,
        'has_warning': batch_result.has_warning,
    }


def serialize_result(item):
    return {
        'input_filename': item.input_filename,
        'success': item.success,
        'input_rows': item.input_rows,
        'output_files': item.output_files,
        'warnings': item.warnings,
        'errors': item.errors,
    }


def build_task_payload(task_id, uploaded_files, job_type):
    return {
        'task_id': task_id,
        'job_type': job_type,
        'status': 'queued',
        'stage': 'queued',
        'message': '任务已创建，等待开始',
        'current_file': '',
        'completed_files': 0,
        'total_files': len(uploaded_files),
        'percent': 0,
        'summary': None,
        'result_items': [],
        'download_ready': False,
        'download_url': None,
        'error': '',
    }


def get_forms_for_request(request):
    job_type = request.POST.get('job_type', JOB_TYPE_SESSION_SORT)
    if job_type == JOB_TYPE_TOPIC_ABANDON:
        topic_form = TopicAbandonForm(request.POST, request.FILES)
        return job_type, SessionSortForm(), topic_form, AssignmentForm(), topic_form
    if job_type == JOB_TYPE_ASSIGNMENT:
        assignment_form = AssignmentForm(request.POST, request.FILES)
        return job_type, SessionSortForm(), TopicAbandonForm(), assignment_form, assignment_form
    session_form = SessionSortForm(request.POST, request.FILES)
    return JOB_TYPE_SESSION_SORT, session_form, TopicAbandonForm(), AssignmentForm(), session_form


@require_POST
def process_view(request):
    job_type, session_form, topic_form, assignment_form, active_form = get_forms_for_request(request)
    context = build_base_context(
        session_form=session_form,
        topic_form=topic_form,
        assignment_form=assignment_form,
        active_job_type=job_type,
    )

    if not active_form.is_valid():
        return render(request, 'sorter/index.html', context)

    uploaded_files = active_form.cleaned_data.get('files') or []
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]

    uploaded_files = clone_uploaded_files(uploaded_files)

    task_id = uuid.uuid4().hex
    with TASK_CACHE_LOCK:
        TASK_CACHE[task_id] = build_task_payload(task_id, uploaded_files, job_type)

    def update_task(progress):
        with TASK_CACHE_LOCK:
            task = TASK_CACHE.get(task_id)
            if not task:
                return
            task.update(progress)

    def run_task():
        try:
            update_task({
                'status': 'running',
                'stage': 'starting',
                'message': '后台任务已启动',
            })

            if job_type == JOB_TYPE_TOPIC_ABANDON:
                batch_result = process_topic_uploaded_files(
                    uploaded_files=uploaded_files,
                    target_date=active_form.cleaned_data['target_date'],
                    retain_rules=active_form.cleaned_data['retain_rules'],
                    cross_domain_retain_count=active_form.cleaned_data['cross_domain_retain_count'],
                    topic_order_mode=active_form.cleaned_data['topic_order_mode'],
                    progress_callback=update_task,
                )
            elif job_type == JOB_TYPE_ASSIGNMENT:
                batch_result = process_assignment_uploaded_files(
                    uploaded_files=uploaded_files,
                    category_time=active_form.cleaned_data['category_time'],
                    annotators_config=active_form.cleaned_data['annotators_config'],
                    target_minutes=active_form.cleaned_data['target_minutes'],
                    progress_callback=update_task,
                )
            else:
                batch_result = process_uploaded_files(
                    uploaded_files=uploaded_files,
                    target_columns=active_form.cleaned_data['target_columns'],
                    chunk_size=active_form.cleaned_data['chunk_size'],
                    missing_column_mode=active_form.cleaned_data['missing_column_mode'],
                    progress_callback=update_task,
                )

            download_url = None
            if batch_result.zip_bytes:
                token = uuid.uuid4().hex
                DOWNLOAD_CACHE[token] = batch_result.zip_bytes
                download_url = reverse('sorter:download', args=[token])

            update_task({
                'status': 'finished',
                'stage': 'finished',
                'message': '全部文件处理完成',
                'percent': 100,
                'current_file': '',
                'summary': build_summary(batch_result),
                'result_items': [serialize_result(item) for item in batch_result.results],
                'download_ready': bool(download_url),
                'download_url': download_url,
            })
        except Exception as exc:
            update_task({
                'status': 'failed',
                'stage': 'failed',
                'message': '处理失败',
                'error': str(exc),
            })

    threading.Thread(target=run_task, daemon=True).start()
    return JsonResponse({'task_id': task_id})


@require_GET
def progress_view(request, task_id):
    with TASK_CACHE_LOCK:
        task = TASK_CACHE.get(task_id)
        if not task:
            return JsonResponse({'error': '任务不存在或已失效。'}, status=404)
        return JsonResponse(task)


def download(request, token):
    zip_bytes = DOWNLOAD_CACHE.get(token)
    if not zip_bytes:
        raise Http404('下载内容不存在或已失效。')
    return FileResponse(
        io.BytesIO(zip_bytes),
        as_attachment=True,
        filename='处理结果.zip',
        content_type='application/zip',
    )


def assignment_view(request):
    context = {
        'form': AssignmentForm(),
        'default_category_time_text': DEFAULT_CATEGORY_TIME_TEXT,
        'default_annotators_config_text': DEFAULT_ANNOTATORS_CONFIG_TEXT,
        'default_target_minutes': DEFAULT_TARGET_MINUTES,
    }
    return render(request, 'sorter/assignment.html', context)


@require_POST
def assignment_process_view(request):
    form = AssignmentForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = []
        for field_errors in form.errors.values():
            for error in field_errors:
                errors.append(str(error))
        return JsonResponse({'error': '; '.join(errors)}, status=400)

    uploaded_files = form.cleaned_data.get('files') or []
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]
    uploaded_files = clone_uploaded_files(uploaded_files)

    task_id = uuid.uuid4().hex
    with TASK_CACHE_LOCK:
        TASK_CACHE[task_id] = build_task_payload(task_id, uploaded_files, JOB_TYPE_ASSIGNMENT)

    category_time = form.cleaned_data['category_time']
    annotators_config = form.cleaned_data['annotators_config']
    target_minutes = form.cleaned_data['target_minutes']

    def update_task(progress):
        with TASK_CACHE_LOCK:
            task = TASK_CACHE.get(task_id)
            if task:
                task.update(progress)

    def run_task():
        try:
            update_task({
                'status': 'running',
                'stage': 'starting',
                'message': '后台任务已启动',
            })
            batch_result = process_assignment_uploaded_files(
                uploaded_files=uploaded_files,
                category_time=category_time,
                annotators_config=annotators_config,
                target_minutes=target_minutes,
                progress_callback=update_task,
            )
            download_url = None
            if batch_result.zip_bytes:
                token = uuid.uuid4().hex
                DOWNLOAD_CACHE[token] = batch_result.zip_bytes
                download_url = reverse('sorter:download', args=[token])
            update_task({
                'status': 'finished',
                'stage': 'finished',
                'message': '全部文件处理完成',
                'percent': 100,
                'current_file': '',
                'summary': build_summary(batch_result),
                'result_items': [serialize_result(item) for item in batch_result.results],
                'download_ready': bool(download_url),
                'download_url': download_url,
            })
        except Exception as exc:
            update_task({
                'status': 'failed',
                'stage': 'failed',
                'message': '处理失败',
                'error': str(exc),
            })

    threading.Thread(target=run_task, daemon=True).start()
    return JsonResponse({'task_id': task_id})


def health(request):
    context = build_base_context()
    context['health'] = 'ok'
    return render(request, 'sorter/index.html', context)
