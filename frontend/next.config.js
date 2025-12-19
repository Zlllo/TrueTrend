/** @type {import('next').NextConfig} */
const nextConfig = {
    // 允许跨域图片
    images: {
        domains: ['localhost'],
    },
    // 启用严格模式
    reactStrictMode: true,
}

module.exports = nextConfig
