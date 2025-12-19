"""
TrueTrend CN - 情感分析器
参考 BettaFish InsightEngine 实现

支持两种分析模式:
1. SnowNLP (轻量级，本地运行，无需 GPU)
2. 关键词规则引擎 (兜底方案)
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# 尝试导入 SnowNLP
try:
    from snownlp import SnowNLP
    SNOWNLP_AVAILABLE = True
except ImportError:
    SNOWNLP_AVAILABLE = False
    print("[SentimentAnalyzer] SnowNLP 未安装，将使用规则引擎")


class SentimentType(str, Enum):
    """情绪类型"""
    ANGRY = "angry"      # 愤怒
    HAPPY = "happy"      # 开心
    SAD = "sad"          # 忧郁
    NEUTRAL = "neutral"  # 中性


@dataclass
class SentimentResult:
    """情感分析结果"""
    text: str
    sentiment: SentimentType
    confidence: float  # 0.0 - 1.0
    raw_score: float   # 原始分数 (SnowNLP: 0-1)
    method: str        # 使用的方法: snownlp / rules


class SentimentAnalyzer:
    """
    中文情感分析器
    
    参考 BettaFish WeiboMultilingualSentimentAnalyzer 实现
    使用 SnowNLP + 规则引擎双重分析
    """
    
    # ============================================================
    # 情绪关键词规则 (优先级高于 NLP)
    # ============================================================
    
    # 愤怒关键词
    ANGRY_KEYWORDS = [
        "愤怒", "怒", "骂", "烂", "垃圾", "崩", "傻", "蠢", "恶心", 
        "讨厌", "滚", "去死", "无耻", "可恶", "气死", "操", "妈的",
        "黑心", "坑", "骗", "假", "渣", "恨", "混蛋", "无语",
    ]
    
    # 开心关键词
    HAPPY_KEYWORDS = [
        "哈哈", "开心", "太棒", "牛", "赞", "厉害", "爱", "喜欢",
        "感谢", "幸福", "欢乐", "可爱", "哇", "耶", "好看", "优秀",
        "帅", "美", "甜", "暖", "支持", "期待", "激动", "感动",
        "泪目", "破防", "yyds", "绝绝子", "无敌", "顶",
    ]
    
    # 忧郁关键词
    SAD_KEYWORDS = [
        "哭", "难过", "心疼", "悲", "伤心", "遗憾", "可怜", "唉",
        "累", "丧", "emo", "抑郁", "焦虑", "绝望", "痛", "苦",
        "无奈", "心酸", "叹气", "泪", "别了", "再见", "结束",
    ]
    
    # ============================================================
    # 情绪分数阈值
    # ============================================================
    
    # SnowNLP 返回 0-1 的积极概率
    # 0.0 - 0.3: 愤怒
    # 0.3 - 0.5: 忧郁
    # 0.5 - 0.7: 中性
    # 0.7 - 1.0: 开心
    
    THRESHOLD_ANGRY = 0.3
    THRESHOLD_SAD = 0.5
    THRESHOLD_NEUTRAL = 0.7
    
    def __init__(self, enable_snownlp: bool = True):
        """
        初始化情感分析器
        
        Args:
            enable_snownlp: 是否启用 SnowNLP (需要安装)
        """
        self.use_snownlp = enable_snownlp and SNOWNLP_AVAILABLE
        
        # 预编译正则
        self._angry_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in self.ANGRY_KEYWORDS),
            re.IGNORECASE
        )
        self._happy_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in self.HAPPY_KEYWORDS),
            re.IGNORECASE
        )
        self._sad_pattern = re.compile(
            '|'.join(re.escape(kw) for kw in self.SAD_KEYWORDS),
            re.IGNORECASE
        )
    
    def analyze(self, text: str) -> SentimentResult:
        """
        分析单个文本的情感
        
        流程:
        1. 先用关键词规则检测 (高优先级)
        2. 再用 SnowNLP 分析 (如果可用)
        3. 最后返回中性
        """
        if not text or not text.strip():
            return SentimentResult(
                text=text,
                sentiment=SentimentType.NEUTRAL,
                confidence=0.5,
                raw_score=0.5,
                method="empty"
            )
        
        # 1. 关键词规则检测
        rule_result = self._analyze_by_rules(text)
        if rule_result:
            return rule_result
        
        # 2. SnowNLP 分析
        if self.use_snownlp:
            try:
                snlp_result = self._analyze_by_snownlp(text)
                return snlp_result
            except Exception as e:
                print(f"[SentimentAnalyzer] SnowNLP 分析失败: {e}")
        
        # 3. 默认返回中性
        return SentimentResult(
            text=text,
            sentiment=SentimentType.NEUTRAL,
            confidence=0.5,
            raw_score=0.5,
            method="default"
        )
    
    def _analyze_by_rules(self, text: str) -> Optional[SentimentResult]:
        """
        使用关键词规则分析
        
        返回 None 表示规则未匹配
        """
        # 统计各类关键词出现次数
        angry_matches = len(self._angry_pattern.findall(text))
        happy_matches = len(self._happy_pattern.findall(text))
        sad_matches = len(self._sad_pattern.findall(text))
        
        total_matches = angry_matches + happy_matches + sad_matches
        
        # 如果没有匹配任何关键词，返回 None
        if total_matches == 0:
            return None
        
        # 计算主导情绪
        max_matches = max(angry_matches, happy_matches, sad_matches)
        
        if max_matches == 0:
            return None
        
        # 确定情绪类型
        if angry_matches == max_matches:
            sentiment = SentimentType.ANGRY
            raw_score = 0.2  # 映射到低分
        elif happy_matches == max_matches:
            sentiment = SentimentType.HAPPY
            raw_score = 0.85  # 映射到高分
        else:
            sentiment = SentimentType.SAD
            raw_score = 0.4
        
        # 置信度基于匹配数量
        confidence = min(0.6 + max_matches * 0.1, 0.95)
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            confidence=confidence,
            raw_score=raw_score,
            method="rules"
        )
    
    def _analyze_by_snownlp(self, text: str) -> SentimentResult:
        """使用 SnowNLP 分析"""
        s = SnowNLP(text)
        
        # sentiments 返回积极概率 (0-1)
        raw_score = s.sentiments
        
        # 映射到情绪类型
        if raw_score < self.THRESHOLD_ANGRY:
            sentiment = SentimentType.ANGRY
        elif raw_score < self.THRESHOLD_SAD:
            sentiment = SentimentType.SAD
        elif raw_score < self.THRESHOLD_NEUTRAL:
            sentiment = SentimentType.NEUTRAL
        else:
            sentiment = SentimentType.HAPPY
        
        # 置信度基于分数距离阈值的程度
        if sentiment == SentimentType.HAPPY:
            confidence = 0.5 + (raw_score - 0.7) * 1.5
        elif sentiment == SentimentType.ANGRY:
            confidence = 0.5 + (0.3 - raw_score) * 1.5
        else:
            confidence = 0.5 + abs(raw_score - 0.5)
        
        confidence = max(0.3, min(0.95, confidence))
        
        return SentimentResult(
            text=text,
            sentiment=sentiment,
            confidence=confidence,
            raw_score=raw_score,
            method="snownlp"
        )
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        批量分析多个文本
        """
        return [self.analyze(text) for text in texts]
    
    def get_dominant_sentiment(
        self, 
        texts: List[str]
    ) -> Tuple[SentimentType, float]:
        """
        获取一组文本的主导情绪
        
        Returns:
            (主导情绪类型, 平均置信度)
        """
        if not texts:
            return SentimentType.NEUTRAL, 0.5
        
        results = self.analyze_batch(texts)
        
        # 统计各情绪出现次数
        counts: Dict[SentimentType, int] = {}
        total_confidence = 0.0
        
        for result in results:
            counts[result.sentiment] = counts.get(result.sentiment, 0) + 1
            total_confidence += result.confidence
        
        # 找出最多的情绪
        dominant = max(counts.items(), key=lambda x: x[1])
        avg_confidence = total_confidence / len(results)
        
        return dominant[0], avg_confidence


# 全局单例
_sentiment_analyzer: Optional[SentimentAnalyzer] = None


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """获取全局 SentimentAnalyzer 实例"""
    global _sentiment_analyzer
    
    if _sentiment_analyzer is None:
        _sentiment_analyzer = SentimentAnalyzer()
    
    return _sentiment_analyzer


def analyze_sentiment(text: str) -> SentimentType:
    """便捷函数: 分析文本情感，返回情绪类型"""
    analyzer = get_sentiment_analyzer()
    result = analyzer.analyze(text)
    return result.sentiment
