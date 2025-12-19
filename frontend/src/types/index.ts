/**
 * TrueTrend CN - TypeScript 类型定义
 */

// 情绪类型
export type Sentiment = 'angry' | 'happy' | 'sad' | 'neutral';

// 平台类型
export type Platform = 'weibo' | 'zhihu' | 'bilibili' | 'douyin' | 'baidu';

// 生命周期阶段
export type LifecyclePhase = 'birth' | 'rise' | 'peak' | 'decline' | 'death';

// 单个热词
export interface TrendItem {
    keyword: string;
    platforms: Platform[];
    raw_heat_score: number;
    real_score: number;
    sentiment: Sentiment;
    first_seen: string;
    peak_time: string;
    last_seen: string;
    is_marketing: boolean;
    platform_count: number;
}

// 生命周期数据点
export interface LifecyclePoint {
    timestamp: string;
    heat_score: number;
    phase: LifecyclePhase;
}

// 生命周期响应
export interface LifecycleData {
    keyword: string;
    data_points: LifecyclePoint[];
    birth_date: string;
    peak_date: string;
    death_date: string | null;
    total_days: number;
}

// 热词列表响应
export interface TrendResponse {
    trends: TrendItem[];
    total_count: number;
    generated_at: string;
}

// 时间轴月份
export interface TimelineMonth {
    month: string;
    top_trends: TrendItem[];
}

// 时间轴响应
export interface TimelineResponse {
    timeline: TimelineMonth[];
    year: number;
}

// 气泡图节点
export interface BubbleNode {
    id: string;
    keyword: string;
    real_score: number;
    sentiment: Sentiment;
    platforms: Platform[];
    platform_count: number;
    radius: number;
    x?: number;
    y?: number;
    fx?: number | null;
    fy?: number | null;
}

// 分数分解
export interface ScoreBreakdown {
    base_heat: number;
    platform_multiplier: number;
    longevity_factor: number;
    marketing_penalty: number;
}

// 情绪颜色映射
export const SENTIMENT_COLORS: Record<Sentiment, string> = {
    angry: '#ff3366',
    happy: '#00ff9f',
    sad: '#00d4ff',
    neutral: '#8888aa',
};

// 平台显示名称
export const PLATFORM_NAMES: Record<Platform, string> = {
    weibo: '微博',
    zhihu: '知乎',
    bilibili: 'B站',
    douyin: '抖音',
    baidu: '百度',
};

// 平台颜色
export const PLATFORM_COLORS: Record<Platform, string> = {
    weibo: '#ff8200',
    zhihu: '#0084ff',
    bilibili: '#fb7299',
    douyin: '#000000',
    baidu: '#2932e1',
};
