'use client';

/**
 * TrueTrend CN - 解码动画加载器
 * 数据加载时显示的"解码"效果
 */

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DecodingLoaderProps {
    text?: string;
    isLoading?: boolean;
    children?: React.ReactNode;
}

// 随机字符集
const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@#$%&*!?<>[]{}';

function getRandomChar(): string {
    return CHARS[Math.floor(Math.random() * CHARS.length)];
}

function generateRandomString(length: number): string {
    return Array.from({ length }, () => getRandomChar()).join('');
}

export default function DecodingLoader({
    text = 'DECODING...',
    isLoading = true,
    children
}: DecodingLoaderProps) {
    // 初始使用确定性字符串避免水合错误
    const [displayText, setDisplayText] = useState(text);
    const [decodedIndex, setDecodedIndex] = useState(0);
    const [isMounted, setIsMounted] = useState(false);

    // 确保只在客户端运行随机逻辑
    useEffect(() => {
        setIsMounted(true);
    }, []);

    useEffect(() => {
        if (!isMounted) return;

        if (!isLoading) {
            setDisplayText(text);
            setDecodedIndex(text.length);
            return;
        }

        // 初始化随机字符串
        setDisplayText(generateRandomString(text.length));
        setDecodedIndex(0);

        // 随机闪烁效果
        const flickerInterval = setInterval(() => {
            setDisplayText(prev => {
                const chars = prev.split('');
                for (let i = decodedIndex; i < chars.length; i++) {
                    if (Math.random() > 0.5) {
                        chars[i] = getRandomChar();
                    }
                }
                return chars.join('');
            });
        }, 50);

        // 逐步解码
        const decodeInterval = setInterval(() => {
            setDecodedIndex(prev => {
                if (prev >= text.length) {
                    clearInterval(decodeInterval);
                    clearInterval(flickerInterval);
                    return prev;
                }
                setDisplayText(current => {
                    const chars = current.split('');
                    chars[prev] = text[prev];
                    return chars.join('');
                });
                return prev + 1;
            });
        }, 100);

        return () => {
            clearInterval(flickerInterval);
            clearInterval(decodeInterval);
        };
    }, [text, isLoading, isMounted]);

    return (
        <AnimatePresence mode="wait">
            {isLoading ? (
                <motion.div
                    key="loader"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex flex-col items-center justify-center min-h-[200px] gap-6"
                >
                    {/* 解码文字 */}
                    <div className="relative">
                        <motion.span
                            className="font-mono text-2xl font-bold text-neon-green tracking-widest"
                            animate={{
                                textShadow: [
                                    '0 0 5px #00ff9f, 0 0 10px #00ff9f',
                                    '0 0 10px #00ff9f, 0 0 20px #00ff9f, 0 0 30px #00ff9f',
                                    '0 0 5px #00ff9f, 0 0 10px #00ff9f',
                                ],
                            }}
                            transition={{ duration: 1, repeat: Infinity }}
                        >
                            {displayText}
                        </motion.span>
                    </div>

                    {/* 进度条 */}
                    <div className="w-64 h-1 bg-cyber-border rounded-full overflow-hidden">
                        <motion.div
                            className="h-full bg-neon-green"
                            initial={{ width: '0%' }}
                            animate={{ width: `${(decodedIndex / text.length) * 100}%` }}
                            transition={{ duration: 0.1 }}
                        />
                    </div>

                    {/* 扫描线动画 */}
                    <motion.div
                        className="absolute inset-0 bg-gradient-to-b from-transparent via-neon-green/5 to-transparent pointer-events-none"
                        animate={{ y: ['-100%', '100%'] }}
                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                    />
                </motion.div>
            ) : (
                <motion.div
                    key="content"
                    initial={{ opacity: 0, filter: 'blur(10px)' }}
                    animate={{ opacity: 1, filter: 'blur(0px)' }}
                    transition={{ duration: 0.5 }}
                >
                    {children}
                </motion.div>
            )}
        </AnimatePresence>
    );
}

/**
 * 简单的加载指示器
 */
export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
    const sizeClasses = {
        sm: 'w-4 h-4',
        md: 'w-8 h-8',
        lg: 'w-12 h-12',
    };

    return (
        <motion.div
            className={`${sizeClasses[size]} border-2 border-neon-green border-t-transparent rounded-full`}
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
    );
}

/**
 * 数据加载骨架屏
 */
export function DataSkeleton({
    rows = 3,
    className = ''
}: {
    rows?: number;
    className?: string;
}) {
    // 使用固定宽度避免水合错误
    const widths = [85, 70, 90, 65, 80];

    return (
        <div className={`space-y-3 ${className}`}>
            {Array.from({ length: rows }).map((_, i) => (
                <motion.div
                    key={i}
                    className="h-4 bg-cyber-border rounded"
                    animate={{ opacity: [0.3, 0.6, 0.3] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.1 }}
                    style={{ width: `${widths[i % widths.length]}%` }}
                />
            ))}
        </div>
    );
}
