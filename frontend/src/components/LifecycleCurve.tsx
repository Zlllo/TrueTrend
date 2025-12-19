'use client';

/**
 * TrueTrend CN - 生命周期曲线
 * 展示热词从诞生到消亡的热度变化
 */

import { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceDot,
    Area,
    ComposedChart,
} from 'recharts';
import { LifecycleData, LifecyclePoint } from '@/types';

interface LifecycleCurveProps {
    data: LifecycleData | null;
    onClose?: () => void;
}

// 阶段颜色和标签
const PHASE_CONFIG = {
    birth: { color: '#00d4ff', label: '诞生', icon: '🌱' },
    rise: { color: '#00ff9f', label: '上升', icon: '📈' },
    peak: { color: '#ffff00', label: '巅峰', icon: '⚡' },
    decline: { color: '#ff8800', label: '衰退', icon: '📉' },
    death: { color: '#ff3366', label: '消亡', icon: '💀' },
};

export default function LifecycleCurve({ data, onClose }: LifecycleCurveProps) {
    // 格式化图表数据
    const chartData = useMemo(() => {
        if (!data) return [];

        return data.data_points.map((point: LifecyclePoint) => ({
            date: new Date(point.timestamp).toLocaleDateString('zh-CN', {
                month: 'short',
                day: 'numeric'
            }),
            timestamp: point.timestamp,
            heat: Math.round(point.heat_score),
            phase: point.phase,
            phaseLabel: PHASE_CONFIG[point.phase]?.label || point.phase,
        }));
    }, [data]);

    // 找到峰值点
    const peakPoint = useMemo(() => {
        if (!chartData.length) return null;
        return chartData.reduce((max, p) => p.heat > max.heat ? p : max, chartData[0]);
    }, [chartData]);

    if (!data) {
        return null;
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="neon-card"
        >
            {/* 头部 */}
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h3 className="font-display text-2xl text-neon-green neon-text">
                        {data.keyword}
                    </h3>
                    <p className="text-gray-400 text-sm mt-1 font-mono">
                        生命周期: {data.total_days} 天
                    </p>
                </div>

                {onClose && (
                    <button
                        onClick={onClose}
                        className="w-8 h-8 flex items-center justify-center
                       text-gray-400 hover:text-neon-pink 
                       border border-cyber-border hover:border-neon-pink
                       rounded transition-all"
                    >
                        ✕
                    </button>
                )}
            </div>

            {/* 阶段时间线 */}
            <div className="flex justify-between mb-6 px-4">
                <div className="text-center">
                    <div className="text-2xl mb-1">🌱</div>
                    <div className="text-xs text-neon-blue font-mono">诞生</div>
                    <div className="text-xs text-gray-500">
                        {new Date(data.birth_date).toLocaleDateString('zh-CN')}
                    </div>
                </div>

                <div className="flex-1 flex items-center px-4">
                    <div className="h-0.5 w-full bg-gradient-to-r from-neon-blue via-neon-green to-neon-pink" />
                </div>

                <div className="text-center">
                    <div className="text-2xl mb-1">⚡</div>
                    <div className="text-xs text-neon-green font-mono">巅峰</div>
                    <div className="text-xs text-gray-500">
                        {new Date(data.peak_date).toLocaleDateString('zh-CN')}
                    </div>
                </div>

                <div className="flex-1 flex items-center px-4">
                    <div className="h-0.5 w-full bg-gradient-to-r from-neon-green via-orange-500 to-neon-pink" />
                </div>

                <div className="text-center">
                    <div className="text-2xl mb-1">💀</div>
                    <div className="text-xs text-neon-pink font-mono">消亡</div>
                    <div className="text-xs text-gray-500">
                        {data.death_date
                            ? new Date(data.death_date).toLocaleDateString('zh-CN')
                            : '持续中'}
                    </div>
                </div>
            </div>

            {/* 图表 */}
            <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                        <defs>
                            <linearGradient id="heatGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#00ff9f" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#00ff9f" stopOpacity={0} />
                            </linearGradient>
                        </defs>

                        <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="#1f1f2e"
                            vertical={false}
                        />

                        <XAxis
                            dataKey="date"
                            stroke="#666"
                            tick={{ fill: '#888', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                            axisLine={{ stroke: '#1f1f2e' }}
                        />

                        <YAxis
                            stroke="#666"
                            tick={{ fill: '#888', fontSize: 10, fontFamily: 'JetBrains Mono' }}
                            axisLine={{ stroke: '#1f1f2e' }}
                            tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
                        />

                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#12121a',
                                border: '1px solid #00ff9f',
                                borderRadius: '8px',
                                fontFamily: 'JetBrains Mono',
                            }}
                            labelStyle={{ color: '#00ff9f' }}
                            formatter={(value: number, name: string) => [
                                `${value.toLocaleString()}`,
                                '热度'
                            ]}
                        />

                        <Area
                            type="monotone"
                            dataKey="heat"
                            stroke="transparent"
                            fill="url(#heatGradient)"
                        />

                        <Line
                            type="monotone"
                            dataKey="heat"
                            stroke="#00ff9f"
                            strokeWidth={3}
                            dot={false}
                            activeDot={{
                                r: 6,
                                fill: '#00ff9f',
                                stroke: '#0a0a0f',
                                strokeWidth: 2,
                            }}
                        />

                        {/* 峰值标记 */}
                        {peakPoint && (
                            <ReferenceDot
                                x={peakPoint.date}
                                y={peakPoint.heat}
                                r={8}
                                fill="#ffff00"
                                stroke="#0a0a0f"
                                strokeWidth={2}
                            />
                        )}
                    </ComposedChart>
                </ResponsiveContainer>
            </div>

            {/* 统计卡片 */}
            <div className="grid grid-cols-3 gap-4 mt-6">
                <div className="bg-cyber-dark p-3 rounded border border-cyber-border text-center">
                    <div className="text-2xl font-display text-neon-blue">
                        {data.total_days}
                    </div>
                    <div className="text-xs text-gray-400 font-mono">活跃天数</div>
                </div>

                <div className="bg-cyber-dark p-3 rounded border border-cyber-border text-center">
                    <div className="text-2xl font-display text-neon-green">
                        {peakPoint ? `${(peakPoint.heat / 1000).toFixed(1)}k` : '-'}
                    </div>
                    <div className="text-xs text-gray-400 font-mono">峰值热度</div>
                </div>

                <div className="bg-cyber-dark p-3 rounded border border-cyber-border text-center">
                    <div className="text-2xl font-display text-neon-pink">
                        {chartData.length > 0
                            ? Math.round((peakPoint?.heat || 0) / chartData[0].heat * 100) / 100
                            : '-'}x
                    </div>
                    <div className="text-xs text-gray-400 font-mono">增长倍数</div>
                </div>
            </div>
        </motion.div>
    );
}
