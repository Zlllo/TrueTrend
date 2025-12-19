'use client';

/**
 * TrueTrend CN - 重力气泡图
 * 使用 D3.js 力导向图实现，气泡大小代表热度，颜色代表情绪
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as d3 from 'd3';
import { TrendItem, BubbleNode, SENTIMENT_COLORS, PLATFORM_NAMES, Platform } from '@/types';

interface GravityBubbleChartProps {
    data: TrendItem[];
    width?: number;
    height?: number;
    onBubbleClick?: (item: TrendItem) => void;
}

export default function GravityBubbleChart({
    data,
    width = 800,
    height = 600,
    onBubbleClick,
}: GravityBubbleChartProps) {
    const svgRef = useRef<SVGSVGElement>(null);
    const [hoveredNode, setHoveredNode] = useState<BubbleNode | null>(null);
    const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

    // 将 TrendItem 转换为 BubbleNode
    const createNodes = useCallback((items: TrendItem[]): BubbleNode[] => {
        // 计算半径范围
        const scores = items.map(d => d.real_score);
        const minScore = Math.min(...scores);
        const maxScore = Math.max(...scores);

        const radiusScale = d3.scaleSqrt()
            .domain([minScore, maxScore])
            .range([20, 80]);

        return items.map((item, index) => ({
            id: `bubble-${index}`,
            keyword: item.keyword,
            real_score: item.real_score,
            sentiment: item.sentiment,
            platforms: item.platforms,
            platform_count: item.platform_count,
            radius: radiusScale(item.real_score),
        }));
    }, []);

    useEffect(() => {
        if (!svgRef.current || data.length === 0) return;

        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const nodes = createNodes(data);
        const centerX = width / 2;
        const centerY = height / 2;

        // 创建力导向模拟
        const simulation = d3.forceSimulation<BubbleNode>(nodes)
            .force('charge', d3.forceManyBody().strength(5))
            .force('center', d3.forceCenter(centerX, centerY))
            .force('collision', d3.forceCollide<BubbleNode>().radius(d => d.radius + 5).strength(0.8))
            .force('x', d3.forceX(centerX).strength(0.05))
            .force('y', d3.forceY(centerY).strength(0.05));

        // 创建渐变定义
        const defs = svg.append('defs');

        nodes.forEach((node, i) => {
            const gradient = defs.append('radialGradient')
                .attr('id', `gradient-${i}`)
                .attr('cx', '30%')
                .attr('cy', '30%')
                .attr('r', '70%');

            const baseColor = SENTIMENT_COLORS[node.sentiment];
            gradient.append('stop')
                .attr('offset', '0%')
                .attr('stop-color', d3.color(baseColor)?.brighter(1)?.formatHex() || baseColor);
            gradient.append('stop')
                .attr('offset', '100%')
                .attr('stop-color', d3.color(baseColor)?.darker(0.5)?.formatHex() || baseColor);
        });

        // 创建主组
        const g = svg.append('g');

        // 创建气泡组
        const bubbleGroups = g.selectAll<SVGGElement, BubbleNode>('.bubble-group')
            .data(nodes)
            .join('g')
            .attr('class', 'bubble-group')
            .style('cursor', 'pointer');

        // 绘制外发光圈
        bubbleGroups.append('circle')
            .attr('class', 'glow-circle')
            .attr('r', d => d.radius + 5)
            .attr('fill', 'none')
            .attr('stroke', d => SENTIMENT_COLORS[d.sentiment])
            .attr('stroke-width', 2)
            .attr('opacity', 0.3)
            .style('filter', 'blur(5px)');

        // 绘制主气泡
        bubbleGroups.append('circle')
            .attr('class', 'main-circle')
            .attr('r', d => d.radius)
            .attr('fill', (_, i) => `url(#gradient-${i})`)
            .attr('stroke', d => SENTIMENT_COLORS[d.sentiment])
            .attr('stroke-width', 2)
            .attr('opacity', 0.9);

        // 添加文字
        bubbleGroups.append('text')
            .attr('class', 'bubble-text')
            .attr('text-anchor', 'middle')
            .attr('dy', '0.35em')
            .attr('fill', '#ffffff')
            .attr('font-family', 'JetBrains Mono, monospace')
            .attr('font-size', d => Math.min(d.radius / 3, 14))
            .attr('font-weight', 'bold')
            .text(d => d.keyword.length > 6 ? d.keyword.slice(0, 6) + '...' : d.keyword)
            .style('text-shadow', '0 0 5px rgba(0,0,0,0.8)');

        // 鼠标交互
        bubbleGroups
            .on('mouseenter', function (event, d) {
                d3.select(this).select('.main-circle')
                    .transition()
                    .duration(200)
                    .attr('r', d.radius * 1.1)
                    .attr('stroke-width', 3);

                d3.select(this).select('.glow-circle')
                    .transition()
                    .duration(200)
                    .attr('r', d.radius * 1.1 + 8)
                    .attr('opacity', 0.6);

                setHoveredNode(d);
                setTooltipPosition({ x: event.pageX, y: event.pageY });
            })
            .on('mousemove', function (event) {
                setTooltipPosition({ x: event.pageX, y: event.pageY });
            })
            .on('mouseleave', function (event, d) {
                d3.select(this).select('.main-circle')
                    .transition()
                    .duration(200)
                    .attr('r', d.radius)
                    .attr('stroke-width', 2);

                d3.select(this).select('.glow-circle')
                    .transition()
                    .duration(200)
                    .attr('r', d.radius + 5)
                    .attr('opacity', 0.3);

                setHoveredNode(null);
            })
            .on('click', function (event, d) {
                const originalItem = data.find(item => item.keyword === d.keyword);
                if (originalItem && onBubbleClick) {
                    onBubbleClick(originalItem);
                }
            });

        // 拖拽功能
        const drag = d3.drag<SVGGElement, BubbleNode>()
            .on('start', (event, d) => {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                d.fx = d.x;
                d.fy = d.y;
            })
            .on('drag', (event, d) => {
                d.fx = event.x;
                d.fy = event.y;
            })
            .on('end', (event, d) => {
                if (!event.active) simulation.alphaTarget(0);
                d.fx = null;
                d.fy = null;
            });

        bubbleGroups.call(drag);

        // 更新位置
        simulation.on('tick', () => {
            bubbleGroups.attr('transform', d => `translate(${d.x || 0}, ${d.y || 0})`);
        });

        return () => {
            simulation.stop();
        };
    }, [data, width, height, createNodes, onBubbleClick]);

    return (
        <div className="relative">
            {/* SVG 容器 */}
            <svg
                ref={svgRef}
                width={width}
                height={height}
                className="bg-cyber-dark/50 rounded-lg border border-cyber-border"
                style={{
                    background: 'radial-gradient(circle at 50% 50%, rgba(0, 255, 159, 0.03) 0%, transparent 70%)',
                }}
            />

            {/* 悬浮提示卡片 */}
            <AnimatePresence>
                {hoveredNode && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="fixed z-50 neon-card min-w-[200px] pointer-events-none"
                        style={{
                            left: tooltipPosition.x + 15,
                            top: tooltipPosition.y + 15,
                        }}
                    >
                        <h3 className="text-lg font-bold text-neon-green mb-2">
                            {hoveredNode.keyword}
                        </h3>

                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                                <span className="text-gray-400">RealScore:</span>
                                <span className="text-neon-green font-mono">
                                    {hoveredNode.real_score.toLocaleString()}
                                </span>
                            </div>

                            <div className="flex justify-between">
                                <span className="text-gray-400">情绪:</span>
                                <span
                                    className="font-mono"
                                    style={{ color: SENTIMENT_COLORS[hoveredNode.sentiment] }}
                                >
                                    {hoveredNode.sentiment === 'angry' ? '😠 愤怒' :
                                        hoveredNode.sentiment === 'happy' ? '😊 开心' :
                                            hoveredNode.sentiment === 'sad' ? '😢 忧郁' : '😐 中性'}
                                </span>
                            </div>

                            <div className="flex justify-between">
                                <span className="text-gray-400">平台数:</span>
                                <span className="text-white font-mono">
                                    {hoveredNode.platform_count}
                                </span>
                            </div>

                            <div className="pt-2 border-t border-cyber-border">
                                <span className="text-gray-400 text-xs">来源平台:</span>
                                <div className="flex flex-wrap gap-1 mt-1">
                                    {hoveredNode.platforms.map(p => (
                                        <span key={p} className="data-tag data-tag-green text-xs">
                                            {PLATFORM_NAMES[p as Platform]}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* 图例 */}
            <div className="absolute bottom-4 left-4 flex gap-4 text-xs font-mono">
                <div className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded-full bg-sentiment-happy" />
                    <span className="text-gray-400">开心</span>
                </div>
                <div className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded-full bg-sentiment-angry" />
                    <span className="text-gray-400">愤怒</span>
                </div>
                <div className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded-full bg-sentiment-sad" />
                    <span className="text-gray-400">忧郁</span>
                </div>
                <div className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded-full bg-sentiment-neutral" />
                    <span className="text-gray-400">中性</span>
                </div>
            </div>
        </div>
    );
}
