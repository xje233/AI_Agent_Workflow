"""输出护栏模块：幻觉检测、格式校验、安全过滤、兜底回复"""
import re
from typing import Optional


class OutputGuard:
    """Agent 输出守卫，对 LLM 输出进行多层校验"""

    # 幻觉特征模式
    HALLUCINATION_PATTERNS = [
        (r'(?:文件|文档)\s*[「\u201c]([^「」\u201c\u201d]+)[」\u201d]', "提及了未经验证的文件名"),
        (r"\d{4}[-年]\d{1,2}[-月]\d{1,2}[日号]", "包含具体日期"),
        (r"(?:收入|利润|营收|销售额).*?(?:\d[\d,.]*)\s*(?:万|亿|元|美元)", "包含财务数据"),
        (r"(?:电话|手机)[：:]\s*\d{3,}", "包含电话号码"),
        (r"(?:邮箱|Email)[：:]\s*\S+@\S+", "包含邮箱地址"),
        (r"根据.{0,5}(?:内部|机密|未公开)", "引用未公开信息"),
    ]

    # 越界拒绝词
    BOUNDARY_REFUSAL_PATTERNS = [
        r"(?:政治|政府|党|选举|民主|人权|宗教|种族)",
        r"(?:色情|赌博|毒品|武器|暴力|自杀)",
        r"(?:黑产|刷单|诈骗|洗钱|套利)",
    ]

    # 最低质量标准
    MIN_CONTENT_LENGTH = 3            # 太短视为废输出
    MAX_REPETITION_RATIO = 0.6        # 重复率过高视为循环输出

    @classmethod
    def check_empty(cls, text: str) -> dict:
        """检查空输出，返回结果 dict"""
        if not text or not text.strip():
            return {"ok": False, "reason": "empty_output"}
        if len(text.strip()) < cls.MIN_CONTENT_LENGTH:
            return {"ok": False, "reason": "too_short"}
        return {"ok": True, "reason": None}

    @classmethod
    def check_hallucination(cls, text: str) -> dict:
        """检测可能的幻觉内容，返回结果 dict"""
        warnings = []
        for pattern, desc in cls.HALLUCINATION_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                warnings.append(f"{desc}: {matches[:2]}")
        return {"ok": len(warnings) == 0, "warnings": warnings}

    @classmethod
    def check_repetition(cls, text: str) -> dict:
        """检查内容是否陷入重复循环，返回结果 dict"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if len(lines) < 3:
            return {"ok": True, "reason": None}
        unique = len(set(lines))
        if unique / len(lines) < (1 - cls.MAX_REPETITION_RATIO):
            return {"ok": False, "reason": "repetitive_output"}
        return {"ok": True, "reason": None}

    @classmethod
    def check_boundary(cls, text: str) -> dict:
        """检查是否越界，返回结果 dict"""
        for pattern in cls.BOUNDARY_REFUSAL_PATTERNS:
            if re.search(pattern, text):
                return {"ok": False, "reason": "boundary_violation"}
        return {"ok": True, "reason": None}

    @classmethod
    def validate(cls, text: str) -> dict:
        """
        综合校验，返回结构化结果 dict：
        {
            "text": 最终文本,
            "has_issue": 是否存在问题（需要兜底或警告）,
            "issues": [问题标签列表],
            "used_fallback": 是否使用了兜底回复,
        }
        校验顺序：空检查 → 重复检查 → 幻觉检测 → 越界检查
        """
        issues = []

        # 1. 空检查
        result = cls.check_empty(text)
        if not result["ok"]:
            return {
                "text": cls.fallback(result["reason"]),
                "has_issue": True,
                "issues": [result["reason"]],
                "used_fallback": True,
            }

        # 2. 重复检查
        result = cls.check_repetition(text)
        if not result["ok"]:
            return {
                "text": cls.fallback(result["reason"]),
                "has_issue": True,
                "issues": [result["reason"]],
                "used_fallback": True,
            }

        # 3. 幻觉检测（仅警告，不阻断）
        result = cls.check_hallucination(text)
        if not result["ok"]:
            text += "\n\n> ⚠️ 提示：回复中可能包含未验证的信息，建议核实。"
            issues.extend(result["warnings"])

        # 4. 越界检查
        result = cls.check_boundary(text)
        if not result["ok"]:
            return {
                "text": cls.fallback(result["reason"]),
                "has_issue": True,
                "issues": [result["reason"]],
                "used_fallback": True,
            }

        return {
            "text": text,
            "has_issue": len(issues) > 0,
            "issues": issues,
            "used_fallback": False,
        }

    @classmethod
    def fallback(cls, reason: str = "unknown") -> str:
        """生成兜底回复"""
        fallbacks = {
            "empty_output": "抱歉，我暂时无法生成有效的回复。请尝试重新描述您的问题。",
            "too_short": "抱歉，回复内容不完整。请重新提问或换个方式描述。",
            "repetitive_output": "抱歉，回复生成异常。请刷新页面后重试。",
            "boundary_violation": "该问题超出了我的服务范围。我是企业知识工作助手，请提出业务相关的问题。",
        }
        return fallbacks.get(
            reason,
            "抱歉，处理您的请求时遇到了问题。请稍后重试或联系管理员。"
        )


# 全局单例
guard = OutputGuard()
