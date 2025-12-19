'use client';

/**
 * TrueTrend CN - 年度时间轴
 * 横向滚动，按月份显示热词
 */

import { useRef } from 'react';
import { motion } from 'framer-motion';
import { TimelineMonth, TrendItem, SENTIMENT_COLORS } from '@/types';

interface TimelineProps {
    data: TimelineMonth[];
    onTrendClick?: (trend: TrendItem) => void;
}

// 月份中文名称
const MONTH_NAMES: Record<string, string> = {
    '01': '一月', '02': '二月', '03': '三月', '04': '四月',
    '05': '五月', '06': '六月', '07': '七月', '08': '八月',
    '09': '九月', '10': '十月', '11': '十一月', '12': '十二月',
};

export default function Timeline({ data, onTrendClick }: TimelineProps) {
    const scrollRef = useRef<HTMLDivElement>(null);

    const scrollLeft = () => {
        if (scrollRef.current) {
            scrollRef.current.scrollBy({ left: -300, behavior: 'smooth' });
        }
    };

    const scrollRight = () => {
        if (scrollRef.current) {
            scrollRef.current.scrollBy({ left: 300, behavior: 'smooth' });
        }
    };

    if (!data || data.length === 0) {
        return (
            <div className="text-center text-gray-400 py-8 font-mono">
                暂无时间轴数据
            </div>
        );
    }

    return (
        <div className="relative">
            {/* 左滚动按钮 */}
            <button
                onClick={scrollLeft}
                className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 
                   bg-cyber-surface border border-neon-green/50 rounded-full
                   flex items-center justify-center text-neon-green
                   hover:bg-neon-green hover:text-cyber-dark transition-all
                   shadow-[0_0_10px_rgba(0,255,159,0.3)]"
            >
                ◀
            </button>

            {/* 时间轴容器 */}
            <div
                ref={scrollRef}
                className="overflow-x-auto scrollbar-hide px-12 py-4"
                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
            >
                <div className="flex gap-6 min-w-max">
                    {data.map((month, monthIndex) => (
                        <motion.div
                            key={month.month}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: monthIndex * 0.05 }}
                            className="flex-shrink-0 w-64"
                        >
                            {/* 月份标题 */}
                            <div className="text-center mb-4">
                                <div className="inline-block px-4 py-2 bg-cyber-surface border border-cyber-border rounded">
                                    <span className="font-display text-lg text-neon-green">
                                        {MONTH_NAMES[month.month.split('-')[1]] || month.month}
                                    </span>
                                    <span className="text-gray-500 text-sm ml-2 font-mono">
                                        {month.month}
                                    </span>
                                </div>
                                {/* 连接线 */}
                                <div className="w-0.5 h-4 bg-cyber-border mx-auto" />
                            </div>

                            {/* 月份节点 */}
                            <div className="relative">
                                {/* 垂直时间线 */}
                                <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-cyber-border -translate-x-1/2" />

                                {/* 热词卡片 */}
                                <div className="space-y-3 relative z-10">
                                    {month.top_trends.slice(0, 5).map((trend, idx) => (
                                        <motion.div
                                            key={trend.keyword}
                                            whileHover={{ scale: 1.02, x: 5 }}
                                            whileTap={{ scale: 0.98 }}
                                            onClick={() => onTrendClick?.(trend)}
                                            className="neon-card cursor-pointer relative overflow-hidden group"
                                        >
                                            {/* 情绪指示条 */}
                                            <div
                                                className="absolute left-0 top-0 bottom-0 w-1"
                                                style={{ backgroundColor: SENTIMENT_COLORS[trend.sentiment] }}
                                            />

                                            {/* 排名标签 */}
                                            <div className="absolute -top-1 -right-1 w-6 h-6 
                                      bg-neon-green text-cyber-dark 
                                      flex items-center justify-center 
                                      text-xs font-bold rounded-bl">
                                                {idx + 1}
                                            </div>

                                            {/* 内容 */}
                                            <div className="pl-3">
                                                <h4 className="font-mono font-bold text-white group-hover:text-neon-green transition-colors truncate">
                                                    {trend.keyword}
                                                </h4>
                                                <div className="flex justify-between items-center mt-1 text-xs">
                                                    <span className="text-gray-400">
                                                        {trend.platform_count} 平台
                                                    </span>
                                                    <span className="text-neon-green font-mono">
                                                        {Math.round(trend.real_score / 1000)}k
                                                    </span>
                                                </div>
                                            </div>

                                            {/* Hover 效果 */}
                                            <div className="absolute inset-0 bg-neon-green/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* 右滚动按钮 */}
            <button
                onClick={scrollRight}
                className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 
                   bg-cyber-surface border border-neon-green/50 rounded-full
                   flex items-center justify-center text-neon-green
                   hover:bg-neon-green hover:text-cyber-dark transition-all
                   shadow-[0_0_10px_rgba(0,255,159,0.3)]"
            >
                ▶
            </button>

            {/* 底部装饰线 */}
            <div className="h-0.5 bg-gradient-to-r from-transparent via-neon-green/30 to-transparent mt-4" />
        </div>
    );
}
