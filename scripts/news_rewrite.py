#!/usr/bin/env python3
"""新闻洗稿模块 - 改写新闻标题和摘要，避免原封不动搬运"""

import os
import json
import re
import hashlib
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# 中文改写模板
REWRITE_TEMPLATES_ZH = [
    "{title}，这一消息引发行业关注",
    "最新动态：{title}",
    "重磅！{title}",
    "深度解读：{title}",
    "{title}，业内人士怎么看？",
    "刚刚，{title}",
    "突发：{title}",
    "{title}，这意味着什么？",
]

# 英文改写模板
REWRITE_TEMPLATES_EN = [
    "Breaking: {title}",
    "Latest: {title}",
    "In depth: {title}",
    "Analysis: {title}",
    "Update: {title}",
    "Report: {title}",
]


def rewrite_title(title, lang="zh"):
    """改写标题，使其更具吸引力"""
    if not title:
        return title
    
    # 如果标题已经包含改写标记，跳过
    if any(marker in title for marker in ["重磅", "刚刚", "突发", "最新动态", "深度解读", "Breaking:", "Latest:"]):
        return title
    
    # 根据语言选择模板
    templates = REWRITE_TEMPLATES_ZH if lang == "zh" else REWRITE_TEMPLATES_EN
    
    # 使用标题的 hash 选择模板，保证同一标题每次改写结果一致
    idx = int(hashlib.md5(title.encode()).hexdigest(), 16) % len(templates)
    
    return templates[idx].format(title=title)


def rewrite_summary(summary, title, lang="zh"):
    """改写摘要，使其更精炼"""
    if not summary:
        return summary
    
    # 如果摘要太短，直接返回
    if len(summary) < 50:
        return summary
    
    # 去除重复的标题内容
    if summary.startswith(title):
        summary = summary[len(title):].strip()
    
    # 去除开头的标点符号
    summary = re.sub(r'^[，,。.、\s]+', '', summary)
    
    # 截断到合适的长度
    if len(summary) > 150:
        # 找到第一个句号、问号、感叹号
        for i, char in enumerate(summary):
            if char in '。！？!?.' and i > 50:
                summary = summary[:i + 1]
                break
        else:
            summary = summary[:150] + "..."
    
    # 添加引导语
    if lang == "zh":
        prefixes = ["据悉，", "据了解，", "消息称，", "据报道，", "有分析指出，"]
        idx = int(hashlib.md5(summary.encode()).hexdigest(), 16) % len(prefixes)
        if not any(summary.startswith(p) for p in prefixes):
            summary = prefixes[idx] + summary
    
    return summary


def process_news():
    """处理新闻，进行洗稿"""
    news_path = os.path.join(DATA_DIR, "news.json")
    if not os.path.exists(news_path):
        return "无新闻数据"
    
    with open(news_path, "r", encoding="utf-8") as f:
        news = json.load(f)
    
    updated_count = 0
    
    for item in news:
        # 只处理没有改写过的新闻
        if item.get("rewritten"):
            continue
        
        lang = item.get("lang", "zh")
        original_title = item.get("title", "")
        original_summary = item.get("summary", "")
        
        # 改写标题
        new_title = rewrite_title(original_title, lang)
        if new_title != original_title:
            item["title_original"] = original_title
            item["title"] = new_title
        
        # 改写摘要
        new_summary = rewrite_summary(original_summary, original_title, lang)
        if new_summary != original_summary:
            item["summary_original"] = original_summary
            item["summary"] = new_summary
        
        # 标记已改写
        item["rewritten"] = True
        item["rewritten_at"] = datetime.now().isoformat()
        
        updated_count += 1
    
    # 保存
    with open(news_path, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)
    
    return f"洗稿完成：{updated_count} 条新闻"


if __name__ == "__main__":
    print(process_news())
