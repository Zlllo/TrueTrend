import type { Config } from 'tailwindcss'

const config: Config = {
    content: [
        './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
        './src/components/**/*.{js,ts,jsx,tsx,mdx}',
        './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // 赛博朋克配色
                cyber: {
                    dark: '#0a0a0f',
                    darker: '#050508',
                    surface: '#12121a',
                    border: '#1f1f2e',
                },
                neon: {
                    green: '#00ff9f',
                    pink: '#ff00ff',
                    blue: '#00d4ff',
                    red: '#ff3366',
                    yellow: '#ffff00',
                },
                sentiment: {
                    angry: '#ff3366',    // 愤怒 - 红
                    happy: '#00ff9f',    // 开心 - 绿
                    sad: '#00d4ff',      // 忧郁 - 蓝
                    neutral: '#8888aa',  // 中性 - 灰
                }
            },
            fontFamily: {
                mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
                display: ['Orbitron', 'monospace'],
            },
            animation: {
                'pulse-neon': 'pulse-neon 2s ease-in-out infinite',
                'glitch': 'glitch 1s ease-in-out infinite',
                'scanline': 'scanline 8s linear infinite',
                'decode': 'decode 0.5s steps(10) forwards',
                'float': 'float 6s ease-in-out infinite',
            },
            keyframes: {
                'pulse-neon': {
                    '0%, 100%': {
                        boxShadow: '0 0 5px var(--tw-shadow-color), 0 0 20px var(--tw-shadow-color)',
                        opacity: '1'
                    },
                    '50%': {
                        boxShadow: '0 0 15px var(--tw-shadow-color), 0 0 40px var(--tw-shadow-color)',
                        opacity: '0.8'
                    },
                },
                'glitch': {
                    '0%, 100%': { transform: 'translate(0)' },
                    '20%': { transform: 'translate(-2px, 2px)' },
                    '40%': { transform: 'translate(-2px, -2px)' },
                    '60%': { transform: 'translate(2px, 2px)' },
                    '80%': { transform: 'translate(2px, -2px)' },
                },
                'scanline': {
                    '0%': { transform: 'translateY(-100%)' },
                    '100%': { transform: 'translateY(100vh)' },
                },
                'decode': {
                    '0%': { opacity: '0', filter: 'blur(10px)' },
                    '100%': { opacity: '1', filter: 'blur(0)' },
                },
                'float': {
                    '0%, 100%': { transform: 'translateY(0)' },
                    '50%': { transform: 'translateY(-10px)' },
                },
            },
            backgroundImage: {
                'grid-pattern': 'linear-gradient(#1f1f2e 1px, transparent 1px), linear-gradient(90deg, #1f1f2e 1px, transparent 1px)',
                'cyber-gradient': 'linear-gradient(135deg, #0a0a0f 0%, #12121a 50%, #0a0a0f 100%)',
            },
        },
    },
    plugins: [],
}

export default config
