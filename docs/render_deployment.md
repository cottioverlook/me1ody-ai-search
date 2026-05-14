# Render 上线部署指南

## 部署目标

把 Me1ody AI Search 部署成两个 Render 服务：

- `me1ody-ai-search-backend`：FastAPI 后端，Docker 部署。
- `me1ody-ai-search-frontend`：Vue 前端，Static Site 部署。

项目已提供 `render.yaml`，可以用 Render Blueprint 从 GitHub 仓库一键创建服务。

## 上线前准备

你需要准备：

- GitHub 仓库，用来托管这个项目代码。
- Render 账号。
- Tavily API Key。
- DeepSeek API Key。
- 一个测试密码，例如 `me1ody-test-2026`，只发给参与测试的同学。

不要把真实 API Key 写进代码或提交到 GitHub。

## 第一步：上传到 GitHub

如果项目还不是 Git 仓库，可以在项目根目录执行：

```powershell
git init
git add .
git commit -m "Prepare Render deployment"
```

然后在 GitHub 创建一个私有仓库或公开仓库，并按 GitHub 页面提示推送。

## 第二步：创建 Render Blueprint

1. 打开 Render Dashboard。
2. 点击 `New`。
3. 选择 `Blueprint`。
4. 连接你的 GitHub 仓库。
5. Render 会读取项目根目录的 `render.yaml`。
6. 创建服务时，Render 会要求填写 `sync: false` 的环境变量。

后端环境变量填写：

```env
PUBLIC_TEST_TOKEN=你分发给同学的测试密码
TAVILY_API_KEY=你的 Tavily Key
DEEPSEEK_API_KEY=你的 DeepSeek Key
```

前端环境变量填写：

```env
VITE_API_BASE_URL=https://你的后端服务地址
```

通常后端地址类似：

```text
https://me1ody-ai-search-backend.onrender.com
```

如果 Render 实际生成的地址不同，等后端创建完成后，复制真实地址，更新前端服务的 `VITE_API_BASE_URL`，然后重新部署前端。

## 第三步：检查服务

后端健康检查：

```text
https://你的后端服务地址/api/ready
```

应该返回：

```json
{"status":"ready","environment":"render","database":"ok"}
```

前端访问：

```text
https://你的前端服务地址
```

点击右上角钥匙图标，输入测试密码，再进行搜索。

## Demo 模式

如果你想先不消耗 API 额度，可以在 Render 后端环境变量里设置：

```env
DEMO_MODE=true
```

此时系统会使用本地预置来源和回答，仍然展示完整检索链路、RAG、引用审计和历史保存流程。

想恢复真实搜索时，改回：

```env
DEMO_MODE=false
```

## 公网测试保护

项目已加入两层保护：

- `PUBLIC_TEST_TOKEN`：测试密码，不知道密码的人不能调用搜索接口。
- `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_PER_DAY`：按 IP 做简单限流，避免 API 额度被刷。

默认限制：

```env
RATE_LIMIT_PER_MINUTE=6
RATE_LIMIT_PER_DAY=80
```

## 免费版注意事项

Render 免费 Web Service 可能会休眠。长时间无人访问后，第一次打开或第一次搜索会比较慢，这是正常现象。

当前 Render 配置使用 SQLite 的临时文件路径：

```env
DATABASE_URL=sqlite+aiosqlite:////tmp/me1ody.db
```

这适合同学短期测试，但重新部署或服务重启后，历史记录可能丢失。如果后续要长期开放，应升级到 Postgres。

## 推荐测试流程

1. 先开启 `DEMO_MODE=true`，确认前端、后端、测试密码和页面流程都正常。
2. 再改成 `DEMO_MODE=false`，用真实 API 搜索 2-3 个问题。
3. 把前端链接和测试密码发给同学。
4. 让同学反馈：速度、回答质量、来源可信度、是否出现报错。
