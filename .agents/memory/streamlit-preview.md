---
name: Streamlit 预览约束
description: Python 应用在路径路由工作区的运行约束
---
本项目坚持 Python + Streamlit，不应因预览注册所使用的模板改为 React 应用。

**Why:** 用户明确指定技术栈。普通 webview 工作流虽然能启动 Streamlit，但共享预览代理未获得路由，返回 Backend Not Configured。

**How to apply:** 维护已注册 web 服务的 Streamlit 启动配置；托管开发工作流的当前目录为 artifact 目录，启动脚本必须正确定位项目根目录。数据库已获用户授权接入，机器学习仍不在范围内。
