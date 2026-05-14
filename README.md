---
title: Me1ody AI Search Backend
emoji: 🔎
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
---

# Me1ody AI Search

面向考研复试展示的 AI 搜索项目：Tavily 召回、搜索结果智能处理、本地 RAG、DeepSeek 综合回答、引用审计、离线评测和前端可解释展示。

## 本地开发

后端：

```powershell
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

访问：

- 前端：http://127.0.0.1:5173
- 后端健康检查：http://127.0.0.1:8000/api/health
- 后端就绪检查：http://127.0.0.1:8000/api/ready

## 环境变量

后端需要在 `backend/.env` 中配置：

```env
TAVILY_API_KEY=tvly-your-api-key
DEEPSEEK_API_KEY=sk-your-api-key
DATABASE_URL=sqlite+aiosqlite:///./me1ody.db
CORS_ORIGINS=["http://localhost:5173"]
LOG_LEVEL=INFO
APP_ENV=local
EMBEDDING_BACKEND=sentence_transformers
DEMO_MODE=false
```

不要提交 `.env` 或数据库文件。

Docker Compose 默认使用 `EMBEDDING_BACKEND=hash`，避免在容器构建时下载 PyTorch 和 HuggingFace 模型；本地开发默认仍使用 `sentence_transformers`。

如需复试现场稳定演示，可临时设置：

```env
DEMO_MODE=true
EMBEDDING_BACKEND=hash
```

Demo 模式会使用本地预置来源和预置回答，完整跑通搜索召回、结果处理、RAG、流式回答、引用审计和历史保存流程，但不会消耗 Tavily / DeepSeek API 额度。

## 验收命令

```powershell
cd backend
.\venv\Scripts\python.exe -m pytest -q
.\venv\Scripts\python.exe scripts\evaluate_demo.py
.\venv\Scripts\python.exe -m compileall -q app scripts

cd ..\frontend
npm run build
```

## Docker Compose

确认 `backend/.env` 已存在后：

```powershell
docker compose up --build
```

访问：

- 前端：http://localhost:8080
- 后端：http://localhost:8000/api/ready

Compose 会把 SQLite 数据放到 `backend-data` volume，并把 HuggingFace 模型缓存放到 `hf-cache` volume，避免每次重新下载模型。

## 复试展示

- 讲解稿与架构说明：`docs/interview_guide.md`
- 离线评测报告：`docs/evaluation_report.md`
- 现场兜底方案：开启 `DEMO_MODE=true`

## Render 上线

项目已提供 `render.yaml`，可通过 Render Blueprint 部署：

- 后端：Docker Web Service
- 前端：Static Site

部署步骤见：`docs/render_deployment.md`

## 无银行卡上线

如果不想使用 Render 绑卡验证，可使用：

- 后端：Hugging Face Spaces Docker
- 前端：Vercel Static Site

部署步骤见：`docs/free_deployment_no_card.md`
