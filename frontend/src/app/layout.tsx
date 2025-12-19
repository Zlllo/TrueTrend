import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
    title: 'TrueTrend CN | 去伪存真 - 年度网络热词分析',
    description: '穿透商业营销和假热搜的迷雾，挖掘中国互联网真正自发的年度记忆。',
    keywords: ['热词', '年度总结', '网络流行语', '中国互联网', '数据可视化'],
    authors: [{ name: 'TrueTrend CN' }],
    openGraph: {
        title: 'TrueTrend CN | 去伪存真',
        description: '年度网络热词分析 - 挖掘真实的民间记忆',
        type: 'website',
    },
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="zh-CN">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
            </head>
            <body className="min-h-screen bg-cyber-dark antialiased">
                {/* 全局扫描线效果 */}
                <div className="fixed inset-0 pointer-events-none z-[9999]">
                    <div className="absolute inset-0 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,0,0,0.1)_2px,rgba(0,0,0,0.1)_4px)]" />
                </div>

                {/* 主内容 */}
                <main className="relative z-10">
                    {children}
                </main>
            </body>
        </html>
    );
}
