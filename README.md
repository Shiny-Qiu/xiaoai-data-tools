# xiaoai-data-tools
基于 Django 本地运行的网站，用于简单的数据处理，现支持三种网页处理模式  ：1. Session整理（按 add_session_id 与 timestamp 排序，并按设定行数拆分输出）；2. Topic废除（按目标日期、RETAIN_RULES、跨垂域保留数输出带 是否废除 的结果）3. 理想态人力分配（根据规范类别时间与标注员配置，自动将 topic 分配给标注员）
