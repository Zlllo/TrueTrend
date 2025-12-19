'use client';

/**
 * TrueTrend CN - 主页
 * 去伪存真 - 年度网络热词分析仪表盘
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import GravityBubbleChart from '@/components/GravityBubbleChart';
import Timeline from '@/components/Timeline';
import LifecycleCurve from '@/components/LifecycleCurve';
import DecodingLoader from '@/components/DecodingLoader';
import {
    TrendItem,
    TrendResponse,
    TimelineResponse,
    LifecycleData,
    SENTIMENT_COLORS,
    PLATFORM_NAMES,
    Platform,
} from '@/types';

// Mock 数据 (用于前端独立开发 - 后端连接后可删除)
const MOCK_TRENDS: TrendItem[] = [
    { keyword: '黑神话悟空', platforms: ['weibo', 'zhihu', 'bilibili', 'douyin', 'baidu'] as Platform[], raw_heat_score: 180000, real_score: 450000, sentiment: 'happy', first_seen: '2024-08-01', peak_time: '2024-08-20', last_seen: '2024-09-15', is_marketing: false, platform_count: 5 },
    { keyword: '淄博烧烤', platforms: ['weibo', 'zhihu', 'bilibili', 'douyin', 'baidu'] as Platform[], raw_heat_score: 160000, real_score: 380000, sentiment: 'happy', first_seen: '2024-03-01', peak_time: '2024-04-15', last_seen: '2024-06-01', is_marketing: false, platform_count: 5 },
    { keyword: 'ChatGPT', platforms: ['weibo', 'zhihu', 'bilibili', 'baidu'] as Platform[], raw_heat_score: 150000, real_score: 320000, sentiment: 'neutral', first_seen: '2024-01-01', peak_time: '2024-02-10', last_seen: '2024-12-31', is_marketing: false, platform_count: 4 },
    { keyword: '哈尔滨冰雪', platforms: ['weibo', 'zhihu', 'bilibili', 'douyin', 'baidu'] as Platform[], raw_heat_score: 155000, real_score: 360000, sentiment: 'happy', first_seen: '2024-01-01', peak_time: '2024-01-20', last_seen: '2024-02-28', is_marketing: false, platform_count: 5 },
    { keyword: 'city不city', platforms: ['weibo', 'bilibili', 'douyin'] as Platform[], raw_heat_score: 140000, real_score: 220000, sentiment: 'happy', first_seen: '2024-07-01', peak_time: '2024-07-15', last_seen: '2024-08-30', is_marketing: false, platform_count: 3 },
    { keyword: '延迟退休', platforms: ['weibo', 'zhihu', 'bilibili', 'baidu'] as Platform[], raw_heat_score: 130000, real_score: 280000, sentiment: 'angry', first_seen: '2024-09-01', peak_time: '2024-09-15', last_seen: '2024-10-31', is_marketing: false, platform_count: 4 },
    { keyword: '烂尾楼', platforms: ['weibo', 'zhihu', 'douyin', 'baidu'] as Platform[], raw_heat_score: 125000, real_score: 260000, sentiment: 'angry', first_seen: '2024-05-01', peak_time: '2024-06-10', last_seen: '2024-08-31', is_marketing: false, platform_count: 4 },
    { keyword: 'i人e人', platforms: ['weibo', 'zhihu', 'bilibili', 'douyin'] as Platform[], raw_heat_score: 110000, real_score: 230000, sentiment: 'neutral', first_seen: '2024-04-01', peak_time: '2024-05-20', last_seen: '2024-07-31', is_marketing: false, platform_count: 4 },
    { keyword: '35岁危机', platforms: ['weibo', 'zhihu', 'bilibili'] as Platform[], raw_heat_score: 105000, real_score: 200000, sentiment: 'sad', first_seen: '2024-03-01', peak_time: '2024-04-01', last_seen: '2024-06-30', is_marketing: false, platform_count: 3 },
    { keyword: '孔乙己文学', platforms: ['weibo', 'zhihu', 'bilibili'] as Platform[], raw_heat_score: 98000, real_score: 190000, sentiment: 'sad', first_seen: '2024-02-15', peak_time: '2024-03-10', last_seen: '2024-05-15', is_marketing: false, platform_count: 3 },
    { keyword: '遥遥领先', platforms: ['weibo', 'bilibili', 'zhihu', 'douyin', 'baidu'] as Platform[], raw_heat_score: 120000, real_score: 300000, sentiment: 'happy', first_seen: '2024-08-01', peak_time: '2024-09-01', last_seen: '2024-11-30', is_marketing: false, platform_count: 5 },
    { keyword: '南方小土豆', platforms: ['weibo', 'bilibili', 'douyin'] as Platform[], raw_heat_score: 95000, real_score: 150000, sentiment: 'happy', first_seen: '2024-01-05', peak_time: '2024-01-15', last_seen: '2024-02-20', is_marketing: false, platform_count: 3 },
    { keyword: '特种兵旅游', platforms: ['weibo', 'bilibili', 'douyin', 'zhihu'] as Platform[], raw_heat_score: 100000, real_score: 210000, sentiment: 'happy', first_seen: '2024-04-01', peak_time: '2024-05-01', last_seen: '2024-07-15', is_marketing: false, platform_count: 4 },
    { keyword: '县城婆罗门', platforms: ['weibo', 'zhihu', 'bilibili', 'douyin'] as Platform[], raw_heat_score: 90000, real_score: 185000, sentiment: 'angry', first_seen: '2024-06-01', peak_time: '2024-06-20', last_seen: '2024-08-15', is_marketing: false, platform_count: 4 },
    { keyword: '繁花', platforms: ['weibo', 'zhihu', 'bilibili', 'douyin'] as Platform[], raw_heat_score: 115000, real_score: 240000, sentiment: 'happy', first_seen: '2024-01-01', peak_time: '2024-01-10', last_seen: '2024-02-28', is_marketing: false, platform_count: 4 },
];

const MOCK_TIMELINE = [
    { month: '2024-01', top_trends: MOCK_TRENDS.filter(t => t.keyword.includes('哈尔滨') || t.keyword.includes('繁花') || t.keyword.includes('小土豆')).slice(0, 5) },
    { month: '2024-02', top_trends: MOCK_TRENDS.filter(t => t.keyword.includes('ChatGPT') || t.keyword.includes('孔乙己')).slice(0, 5) },
    { month: '2024-03', top_trends: MOCK_TRENDS.filter(t => t.keyword.includes('淄博') || t.keyword.includes('35岁')).slice(0, 5) },
    { month: '2024-04', top_trends: MOCK_TRENDS.filter(t => t.keyword.includes('i人') || t.keyword.includes('特种兵')).slice(0, 5) },
    { month: '2024-05', top_trends: MOCK_TRENDS.filter(t => t.keyword.includes('烂尾') || t.keyword.includes('县城')).slice(0, 5) },
    { month: '2024-06', top_trends: MOCK_TRENDS.filter(t => t.keyword.includes('延迟') || t.keyword.includes('city')).slice(0, 5) },
    { month: '2024-07', top_trends: MOCK_TRENDS.filter(t => t.keyword.includes('city') || t.keyword.includes('遥遥')).slice(0, 5) },
    { month: '2024-08', top_trends: MOCK_TRENDS.filter(t => t.keyword.includes('黑神话') || t.keyword.includes('遥遥')).slice(0, 5) },
];

const MOCK_LIFECYCLE: LifecycleData = {
    keyword: '黑神话悟空',
    data_points: Array.from({ length: 45 }, (_, i) => {
        const day = i + 1;
        const peak = 20;
        let heat = 0;
        if (day <= peak) {
            heat = 10000 * Math.pow(day / peak, 1.5) + Math.random() * 2000;
        } else {
            heat = 10000 * Math.pow(1 - (day - peak) / 25, 0.8) + Math.random() * 1000;
        }
        return {
            timestamp: new Date(2024, 7, day).toISOString(),
            heat_score: Math.max(500, heat),
            phase: day < 5 ? 'birth' : day < peak ? 'rise' : day === peak ? 'peak' : day > 40 ? 'death' : 'decline',
        };
    }),
    birth_date: '2024-08-01',
    peak_date: '2024-08-20',
    death_date: '2024-09-15',
    total_days: 45,
};

export default function HomePage() {
    const [isLoading, setIsLoading] = useState(true);
    const [trends, setTrends] = useState<TrendItem[]>([]);
    const [selectedTrend, setSelectedTrend] = useState<TrendItem | null>(null);
    const [lifecycleData, setLifecycleData] = useState<LifecycleData | null>(null);
    const [activeTab, setActiveTab] = useState<'bubble' | 'timeline'>('bubble');
    const [dataSource, setDataSource] = useState<'live' | 'mock'>('live');
    const [error, setError] = useState<string | null>(null);

    // 获取真实数据，失败则降级使用 Mock
    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            setError(null);

            try {
                // 调用实时 API
                const response = await fetch('http://localhost:8000/api/trends/live?limit=30');

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();

                // 转换 API 数据格式以匹配 TrendItem
                const formattedTrends: TrendItem[] = data.trends.map((item: any) => ({
                    keyword: item.keyword,
                    platforms: item.platforms || [],
                    raw_heat_score: item.raw_heat_score || 0,
                    real_score: item.real_score || item.raw_heat_score || 0,
                    sentiment: item.sentiment || 'neutral',
                    first_seen: item.first_seen || new Date().toISOString(),
                    peak_time: item.first_seen || new Date().toISOString(),
                    last_seen: item.last_seen || new Date().toISOString(),
                    is_marketing: item.is_marketing || false,
                    platform_count: item.platform_count || item.platforms?.length || 1,
                }));

                setTrends(formattedTrends);
                setDataSource('live');
                console.log(`🔴 实时数据加载成功: ${formattedTrends.length} 条`);

            } catch (err) {
                console.warn('实时数据获取失败，使用 Mock 数据:', err);
                setError('实时数据获取失败，已切换至演示数据');
                setTrends(MOCK_TRENDS);
                setDataSource('mock');
            }

            setIsLoading(false);
        };

        loadData();
    }, []);

    // 处理热词点击
    const handleTrendClick = (trend: TrendItem) => {
        setSelectedTrend(trend);
        // 模拟加载生命周期数据 (TODO: 未来调用 /api/trends/{keyword}/lifecycle)
        setLifecycleData({
            ...MOCK_LIFECYCLE,
            keyword: trend.keyword,
        });
    };

    return (
        <div className="min-h-screen p-6 lg:p-8">
            {/* 头部 */}
            <header className="mb-8">
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4"
                >
                    <div>
                        <h1 className="font-display text-4xl lg:text-5xl text-neon-green neon-text tracking-wider">
                            TRUETREND<span className="text-neon-pink">.CN</span>
                        </h1>
                        <p className="text-gray-400 font-mono mt-2 text-sm lg:text-base">
                            去伪存真 // 穿透营销迷雾 // 挖掘真实记忆
                        </p>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className={`data-tag ${dataSource === 'live' ? 'data-tag-green' : 'data-tag-yellow'}`}>
                            <span className={`w-2 h-2 rounded-full ${dataSource === 'live' ? 'bg-neon-green' : 'bg-yellow-500'} animate-pulse mr-2`} />
                            {dataSource === 'live' ? 'LIVE DATA' : 'DEMO DATA'}
                        </div>
                        <div className="text-gray-500 font-mono text-sm">
                            {new Date().getFullYear()} 年度报告
                        </div>
                    </div>
                </motion.div>

                {/* 分隔线 */}
                <div className="h-px bg-gradient-to-r from-neon-green via-neon-pink to-transparent mt-6" />
            </header>

            {/* 数据统计栏 */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
            >
                {[
                    { label: '分析热词', value: trends.length || '--', color: 'neon-green' },
                    { label: '覆盖平台', value: '5', color: 'neon-blue' },
                    { label: '过滤营销', value: '23%', color: 'neon-pink' },
                    { label: '数据精度', value: '94.7%', color: 'neon-green' },
                ].map((stat, i) => (
                    <div key={i} className="neon-card text-center">
                        <div className={`text-3xl font-display text-${stat.color}`}>
                            {stat.value}
                        </div>
                        <div className="text-gray-400 text-xs font-mono mt-1">
                            {stat.label}
                        </div>
                    </div>
                ))}
            </motion.div>

            {/* 主内容区 */}
            <div className="space-y-8">
                {/* 标签切换 */}
                <div className="flex gap-4">
                    <button
                        onClick={() => setActiveTab('bubble')}
                        className={`glitch-btn ${activeTab === 'bubble' ? 'bg-neon-green text-cyber-dark' : ''}`}
                    >
                        GRAVITY BUBBLE
                    </button>
                    <button
                        onClick={() => setActiveTab('timeline')}
                        className={`glitch-btn ${activeTab === 'timeline' ? 'bg-neon-green text-cyber-dark' : ''}`}
                    >
                        TIMELINE
                    </button>
                </div>

                {/* 可视化区域 */}
                <DecodingLoader isLoading={isLoading} text="DECRYPTING DATA...">
                    <AnimatePresence mode="wait">
                        {activeTab === 'bubble' ? (
                            <motion.div
                                key="bubble"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                <GravityBubbleChart
                                    data={trends}
                                    width={typeof window !== 'undefined' ? Math.min(window.innerWidth - 48, 1200) : 1200}
                                    height={600}
                                    onBubbleClick={handleTrendClick}
                                />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="timeline"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                            >
                                <Timeline
                                    data={MOCK_TIMELINE}
                                    onTrendClick={handleTrendClick}
                                />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </DecodingLoader>

                {/* 生命周期弹窗 */}
                <AnimatePresence>
                    {selectedTrend && lifecycleData && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
                            onClick={() => setSelectedTrend(null)}
                        >
                            <motion.div
                                initial={{ scale: 0.9, y: 20 }}
                                animate={{ scale: 1, y: 0 }}
                                exit={{ scale: 0.9, y: 20 }}
                                className="max-w-2xl w-full"
                                onClick={e => e.stopPropagation()}
                            >
                                <LifecycleCurve
                                    data={lifecycleData}
                                    onClose={() => setSelectedTrend(null)}
                                />
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* 热词排行榜 */}
                {!isLoading && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                    >
                        <h2 className="font-display text-2xl text-neon-green mb-4">
                            TOP TRENDS // 年度热词榜
                        </h2>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            {trends.slice(0, 10).map((trend, idx) => (
                                <motion.div
                                    key={trend.keyword}
                                    whileHover={{ scale: 1.02 }}
                                    className="neon-card flex items-center gap-4 cursor-pointer"
                                    onClick={() => handleTrendClick(trend)}
                                >
                                    {/* 排名 */}
                                    <div className={`w-10 h-10 flex items-center justify-center font-display text-xl
                    ${idx < 3 ? 'bg-neon-green text-cyber-dark' : 'bg-cyber-dark text-neon-green border border-neon-green/50'}
                    rounded`}
                                    >
                                        {idx + 1}
                                    </div>

                                    {/* 内容 */}
                                    <div className="flex-1">
                                        <h3 className="font-bold text-white">{trend.keyword}</h3>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span
                                                className="w-2 h-2 rounded-full"
                                                style={{ backgroundColor: SENTIMENT_COLORS[trend.sentiment] }}
                                            />
                                            <span className="text-xs text-gray-400 font-mono">
                                                {trend.platform_count} 平台 · RealScore {(trend.real_score / 1000).toFixed(1)}k
                                            </span>
                                        </div>
                                    </div>

                                    {/* 平台标签 */}
                                    <div className="flex gap-1">
                                        {trend.platforms.slice(0, 3).map(p => (
                                            <span key={p} className="data-tag text-xs">
                                                {PLATFORM_NAMES[p as Platform]?.[0]}
                                            </span>
                                        ))}
                                        {trend.platforms.length > 3 && (
                                            <span className="data-tag text-xs">+{trend.platforms.length - 3}</span>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </div>

            {/* 页脚 */}
            <footer className="mt-16 pt-8 border-t border-cyber-border text-center">
                <p className="text-gray-500 font-mono text-sm">
                    TRUETREND.CN // 去伪存真 // {new Date().getFullYear()}
                </p>
                <p className="text-gray-600 text-xs mt-2">
                    数据仅供参考，不代表任何官方立场
                </p>
            </footer>
        </div>
    );
}
