from datetime import date

from django import forms


JOB_TYPE_SESSION_SORT = 'session_sort'
JOB_TYPE_TOPIC_ABANDON = 'topic_abandon'
JOB_TYPE_CHOICES = [
    (JOB_TYPE_SESSION_SORT, 'Session整理'),
    (JOB_TYPE_TOPIC_ABANDON, 'Topic废除'),
]
JOB_TYPE_ASSIGNMENT = 'assignment'

TOPIC_REQUIRED_COLUMNS = ['真实细分Agent', 'topic_id', 'topic类型', '标注日期', 'query有效性']
DEFAULT_TOPIC_TARGET_DATE = '2026-02-02'
DEFAULT_CROSS_DOMAIN_RETAIN_COUNT = 7
TOPIC_ORDER_ROW_COUNT = 'row_count'
TOPIC_ORDER_RANDOM = 'random'
TOPIC_ORDER_TOPIC = 'topic'
TOPIC_ORDER_ORIGINAL = 'original'
TOPIC_ORDER_CHOICES = [
    (TOPIC_ORDER_ROW_COUNT, '按行数升序保留'),
    (TOPIC_ORDER_RANDOM, '随机顺序'),
    (TOPIC_ORDER_TOPIC, 'topic排序'),
    (TOPIC_ORDER_ORIGINAL, '原始文档顺序'),
]
DEFAULT_TOPIC_ORDER_MODE = TOPIC_ORDER_TOPIC

DEFAULT_RETAIN_RULES = {
    ('QA', '单轮session'): 3,
    ('QA', '单轮topic'): 3,
    ('QA', '多轮topic'): 5,
    ('VisionQA', '单轮session'): 2,
    ('VisionQA', '单轮topic'): 2,
    ('VisionQA', '多轮topic'): 3,
    ('Chat', '单轮session'): 1,
    ('Chat', '单轮topic'): 1,
    ('Chat', '多轮topic'): 1,
    ('toolsAgent', '单轮session'): 4,
    ('toolsAgent', '单轮topic'): 4,
    ('toolsAgent', '多轮topic'): 7,
    ('controlAgent', '单轮session'): 3,
    ('controlAgent', '单轮topic'): 3,
    ('controlAgent', '多轮topic'): 5,
    ('contentAgent', '单轮session'): 1,
    ('contentAgent', '单轮topic'): 1,
    ('contentAgent', '多轮topic'): 2,
    ('productAgent', '单轮session'): 1,
    ('productAgent', '单轮topic'): 1,
    ('productAgent', '多轮topic'): 2,
    ('iotAgent', '单轮session'): 1,
    ('iotAgent', '单轮topic'): 1,
    ('iotAgent', '多轮topic'): 2,
    ('lifeAgent', '单轮session'): 1,
    ('lifeAgent', '单轮topic'): 1,
    ('lifeAgent', '多轮topic'): 2,
    ('mapAgent', '单轮session'): 1,
    ('mapAgent', '单轮topic'): 1,
    ('mapAgent', '多轮topic'): 2,
    ('openplatform', '单轮session'): 1,
    ('openplatform', '单轮topic'): 1,
    ('openplatform', '多轮topic'): 1,
    ('aiCreativeAgent', '单轮session'): 1,
    ('aiCreativeAgent', '单轮topic'): 1,
    ('aiCreativeAgent', '多轮topic'): 1,
}

DEFAULT_RETAIN_RULES_TEXT = "\n".join(
    f"{agent},{topic_type},{count}"
    for (agent, topic_type), count in DEFAULT_RETAIN_RULES.items()
)

ASSIGNMENT_REQUIRED_COLUMNS = ['是否废除', 'topic_id', '规范类别']

DEFAULT_CATEGORY_TIME = {
    '通用问答': 10,
    '图片问答': 10,
    '工具控制导航': 5,
    'AI创作': 8,
    '内容': 7,
    '生活服务': 10,
    '产品问答': 10,
    'IOT': 5,
    '多指令': 5,
    'nonsense': 2,
}

DEFAULT_CATEGORY_TIME_TEXT = "\n".join(
    f"{category},{minutes}"
    for category, minutes in DEFAULT_CATEGORY_TIME.items()
)

DEFAULT_ANNOTATORS_CONFIG = {
    '谢秋晨': ['通用问答', '图片问答', '工具控制导航', 'AI创作', '内容', '生活服务', '产品问答', 'IOT', '多指令', 'nonsense'],
    '郑平': ['通用问答', '图片问答', '工具控制导航', 'AI创作', '内容', '生活服务', '产品问答', 'IOT', '多指令', 'nonsense'],
    '桑鹏钧': ['通用问答', '图片问答', '工具控制导航', 'AI创作', '内容', '生活服务', '产品问答', 'IOT', '多指令', 'nonsense'],
    '南文俊': ['通用问答', '图片问答', '工具控制导航', 'AI创作', '内容', '生活服务', '产品问答', 'IOT', '多指令', 'nonsense'],
    '李承': ['通用问答', '图片问答', '工具控制导航', 'AI创作', '内容', '生活服务', '产品问答', 'IOT', '多指令', 'nonsense'],
}

DEFAULT_ANNOTATORS_CONFIG_TEXT = "\n".join(
    f"{name}:{','.join(categories)}"
    for name, categories in DEFAULT_ANNOTATORS_CONFIG.items()
)

DEFAULT_TARGET_MINUTES = 300

DEFAULT_TARGET_COLUMNS = [
    'request_id', 'add_session_id', 'session_id', 'device_id', 'timestamp',
    'query', 'to_speak', 'to_read', 'history', 'domain', 'sample_type',
    'agent_nums', 'round_nums', 'asr_url', 'query_to_client', 'norm_code',
    'label', 'domain_judge', 'intent_category', 'intention', 'user_agent',
    'model', 'skill_name', 'system_prompt', 'chat_prompt', 'func_name',
    'reject_type', 'is_filtered', 'score_domains', 'large_model_traceid',
    'toast_stream', 'speak_stream', 'isllmallowed', 'isllmasr', 'image_url',
    'model_type', 'duplex_mode', 'inject_result', 'rejection_hint', 'is_wake_up',
    'knowledge_source', 'knowledge_content', 'llm_knowledges_user',
    'capabilities_version', 'enable_search', 'ref', 'is_open_deepthinking',
    'is_user_cancel', 'is_tts_cut', 'longitude', 'latitude', 'app_version', 'miui_version'
]

REQUIRED_SORT_COLUMNS = ['add_session_id', 'timestamp']
MISSING_COLUMN_CHOICES = [
    ('strict', '严格模式（缺列即失败）'),
    ('fill_empty', '宽松模式（缺失普通列补空）'),
]


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    widget = MultiFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if not data:
            if self.required:
                raise forms.ValidationError('请至少上传一个文件。')
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [single_file_clean(item, initial) for item in data]


class SessionSortForm(forms.Form):
    files = MultiFileField(
        label='上传文件',
        required=False,
        widget=MultiFileInput(attrs={'accept': '.csv,.xls,.xlsx'})
    )
    target_columns_text = forms.CharField(
        label='目标列顺序',
        widget=forms.Textarea(attrs={'rows': 18}),
        initial='\n'.join(DEFAULT_TARGET_COLUMNS),
        help_text='建议一行一个字段名，也兼容 Python 列表格式。'
    )
    chunk_size = forms.IntegerField(
        label='每个输出文件最大行数',
        min_value=1,
        initial=500
    )
    missing_column_mode = forms.ChoiceField(
        label='缺失列处理方式',
        choices=MISSING_COLUMN_CHOICES,
        initial='strict'
    )

    def clean_files(self):
        files = self.cleaned_data.get('files') or []
        validate_uploaded_files(files)
        return files

    def clean_target_columns_text(self):
        raw = self.cleaned_data['target_columns_text']
        columns = parse_target_columns(raw)
        if not columns:
            raise forms.ValidationError('目标列顺序不能为空。')
        duplicates = find_duplicates(columns)
        if duplicates:
            raise forms.ValidationError(f"目标列顺序中存在重复字段: {', '.join(duplicates)}")
        missing_required = [col for col in REQUIRED_SORT_COLUMNS if col not in columns]
        if missing_required:
            raise forms.ValidationError(
                f"目标列顺序必须包含排序必需字段: {', '.join(missing_required)}"
            )
        self.cleaned_data['target_columns'] = columns
        return raw


class TopicAbandonForm(forms.Form):
    files = MultiFileField(
        label='上传文件',
        required=False,
        widget=MultiFileInput(attrs={'accept': '.csv,.xls,.xlsx'})
    )
    target_date = forms.CharField(
        label='目标日期',
        initial=DEFAULT_TOPIC_TARGET_DATE,
        help_text='格式示例：2026-02-02'
    )
    topic_order_mode = forms.ChoiceField(
        label='候选topic保留顺序',
        choices=TOPIC_ORDER_CHOICES,
        initial=DEFAULT_TOPIC_ORDER_MODE,
        help_text='可选随机顺序、按topic_id排序、按原始文档中首次出现的顺序。'
    )
    cross_domain_retain_count = forms.IntegerField(
        label='跨垂域topic保留数量',
        min_value=0,
        initial=DEFAULT_CROSS_DOMAIN_RETAIN_COUNT
    )
    retain_rules_text = forms.CharField(
        label='RETAIN_RULES 配置',
        widget=forms.Textarea(attrs={'rows': 18}),
        initial=DEFAULT_RETAIN_RULES_TEXT,
        help_text='每行一条规则，格式：Agent,topic类型,数量'
    )

    def clean_files(self):
        files = self.cleaned_data.get('files') or []
        validate_uploaded_files(files)
        return files

    def clean_target_date(self):
        raw = (self.cleaned_data.get('target_date') or '').strip()
        if not raw:
            raise forms.ValidationError('目标日期不能为空。')
        try:
            normalized = date.fromisoformat(raw).strftime('%Y-%m-%d')
        except ValueError:
            raise forms.ValidationError('目标日期格式错误，请使用 YYYY-MM-DD。')
        return normalized

    def clean_retain_rules_text(self):
        raw = self.cleaned_data.get('retain_rules_text', '')
        rules = parse_retain_rules(raw)
        if not rules:
            raise forms.ValidationError('RETAIN_RULES 不能为空。')
        self.cleaned_data['retain_rules'] = rules
        return raw

    def clean_topic_order_mode(self):
        value = self.cleaned_data.get('topic_order_mode')
        valid_values = {choice[0] for choice in TOPIC_ORDER_CHOICES}
        if value not in valid_values:
            raise forms.ValidationError('候选topic保留顺序无效。')
        return value


class AssignmentForm(forms.Form):
    files = MultiFileField(
        label='上传文件',
        required=False,
        widget=MultiFileInput(attrs={'accept': '.csv,.xls,.xlsx'})
    )
    category_time_text = forms.CharField(
        label='规范类别时间配置',
        widget=forms.Textarea(attrs={'rows': 12}),
        initial=DEFAULT_CATEGORY_TIME_TEXT,
        help_text='每行一条，格式：类别名,分钟数'
    )
    annotators_config_text = forms.CharField(
        label='标注员配置',
        widget=forms.Textarea(attrs={'rows': 8}),
        initial=DEFAULT_ANNOTATORS_CONFIG_TEXT,
        help_text='每行一条，格式：标注员名:类别1,类别2,...'
    )
    target_minutes = forms.IntegerField(
        label='每人目标分钟数',
        min_value=1,
        initial=DEFAULT_TARGET_MINUTES,
    )

    def clean_files(self):
        files = self.cleaned_data.get('files') or []
        validate_uploaded_files(files)
        return files

    def clean_category_time_text(self):
        raw = self.cleaned_data.get('category_time_text', '')
        category_time = parse_category_time(raw)
        if not category_time:
            raise forms.ValidationError('规范类别时间配置不能为空。')
        self.cleaned_data['category_time'] = category_time
        return raw

    def clean_annotators_config_text(self):
        raw = self.cleaned_data.get('annotators_config_text', '')
        annotators_config = parse_annotators_config(raw)
        if not annotators_config:
            raise forms.ValidationError('标注员配置不能为空。')
        self.cleaned_data['annotators_config'] = annotators_config
        return raw


def validate_uploaded_files(uploaded_files):
    if not uploaded_files:
        raise forms.ValidationError('请至少上传一个文件。')

    allowed = {'.csv', '.xls', '.xlsx'}
    for uploaded in uploaded_files:
        suffix = ''
        if '.' in uploaded.name:
            suffix = uploaded.name[uploaded.name.rfind('.'):].lower()
        if suffix not in allowed:
            raise forms.ValidationError(f'文件格式不支持：{uploaded.name}')


def parse_target_columns(raw_text):
    text = (raw_text or '').strip()
    if not text:
        return []

    if text.startswith('[') and text.endswith(']'):
        inner = text[1:-1]
        parts = [part.strip() for part in inner.split(',')]
        columns = []
        for part in parts:
            normalized = part.strip().strip('"').strip("'")
            if normalized:
                columns.append(normalized)
        return columns

    columns = []
    for line in text.splitlines():
        normalized = line.strip().strip(',').strip('"').strip("'")
        if normalized:
            columns.append(normalized)
    return columns


def parse_retain_rules(raw_text):
    text = (raw_text or '').strip()
    if not text:
        return {}

    rules = {}
    for index, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        parts = [part.strip() for part in stripped.split(',')]
        if len(parts) != 3:
            raise forms.ValidationError(f'第 {index} 行格式错误，应为：Agent,topic类型,数量')

        agent, topic_type, count_text = parts
        if not agent or not topic_type:
            raise forms.ValidationError(f'第 {index} 行的 Agent 或 topic类型不能为空')

        try:
            count = int(count_text)
        except ValueError:
            raise forms.ValidationError(f'第 {index} 行的数量必须是整数')

        if count < 0:
            raise forms.ValidationError(f'第 {index} 行的数量不能小于 0')

        rules[(agent, topic_type)] = count

    return rules


def find_duplicates(items):
    seen = set()
    duplicates = []
    for item in items:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        seen.add(item)
    return duplicates


def parse_category_time(raw_text):
    text = (raw_text or '').strip()
    if not text:
        return {}
    result = {}
    for index, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        parts = [p.strip() for p in stripped.split(',')]
        if len(parts) != 2:
            raise forms.ValidationError(f'第 {index} 行格式错误，应为：类别名,分钟数')
        category, minutes_text = parts
        if not category:
            raise forms.ValidationError(f'第 {index} 行的类别名不能为空')
        try:
            minutes = int(minutes_text)
        except ValueError:
            raise forms.ValidationError(f'第 {index} 行的分钟数必须是整数')
        if minutes < 0:
            raise forms.ValidationError(f'第 {index} 行的分钟数不能小于 0')
        result[category] = minutes
    return result


def parse_annotators_config(raw_text):
    text = (raw_text or '').strip()
    if not text:
        return {}
    result = {}
    for index, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if ':' not in stripped:
            raise forms.ValidationError(
                f'第 {index} 行格式错误，应为：标注员名:类别1,类别2,...'
            )
        name, categories_text = stripped.split(':', 1)
        name = name.strip()
        if not name:
            raise forms.ValidationError(f'第 {index} 行的标注员名不能为空')
        categories = [c.strip() for c in categories_text.split(',') if c.strip()]
        if not categories:
            raise forms.ValidationError(f'第 {index} 行至少需要一个类别')
        result[name] = categories
    return result
