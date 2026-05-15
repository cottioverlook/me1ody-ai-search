# 无银行卡部署方案：Vercel + Hugging Face Spaces

## 部署结构

这个方案把项目拆成两个公网服务：

- 后端：Hugging Face Spaces Docker，运行 FastAPI。
- 前端：Vercel，运行 Vue 静态站点。

这样不需要使用 Render 的银行卡验证流程。

## 一、部署后端到 Hugging Face Spaces

### 1. 创建 Space

1. 打开 Hugging Face。
2. 点击头像旁边的 `New Space`。
3. Space name 建议填写：`me1ody-ai-search-backend`。
4. SDK 选择：`Docker`。
5. Visibility 可以先选 `Public`，方便同学访问；不想公开源码可以选 `Private`。
6. Hardware 选择免费的 CPU。

### 2. 设置 Secrets 和 Variables

进入 Space 的 `Settings`，找到 `Variables and secrets`。

建议先用 Demo 模式跑通：

Variables:

```env
APP_ENV=huggingface
LOG_LEVEL=INFO
DATABASE_URL=sqlite+aiosqlite:////tmp/me1ody.db
EMBEDDING_BACKEND=hash
DEMO_MODE=true
CORS_ORIGINS=["*"]
RATE_LIMIT_PER_MINUTE=6
RATE_LIMIT_PER_DAY=80
```

Secrets:

```env
PUBLIC_TEST_TOKEN=你发给同学的测试密码
TAVILY_API_KEY=你的 Tavily Key
DEEPSEEK_API_KEY=你的 DeepSeek Key
```

Demo 模式不会消耗 Tavily / DeepSeek 额度。确认部署正常后，再把：

```env
DEMO_MODE=false
```

### 3. 推送代码到 Space

Hugging Face Space 本质也是一个 Git 仓库。创建 Space 后，页面会给出一个仓库地址，通常类似：

```text
https://huggingface.co/spaces/你的用户名/me1ody-ai-search-backend
```

在本地项目根目录执行：

```powershell
git remote add hf https://huggingface.co/spaces/你的用户名/me1ody-ai-search-backend
git push hf main
```

如果提示需要登录，可以使用 Hugging Face 的 Access Token 作为密码。

部署完成后，后端健康检查地址类似：

```text
https://你的用户名-me1ody-ai-search-backend.hf.space/api/ready
```

浏览器打开后应该返回：

```json
{"status":"ready","environment":"huggingface","database":"ok"}
```

## 二、部署前端到 Vercel

### 1. 导入 GitHub 仓库

1. 打开 Vercel。
2. 点击 `Add New` -> `Project`。
3. 选择 GitHub 仓库：`me1ody-ai-search`。
4. Vercel 会读取根目录的 `vercel.json`。

项目已经配置：

```json
{
  "buildCommand": "cd frontend && npm ci && npm run build",
  "outputDirectory": "frontend/dist",
  "framework": "vite"
}
```

### 2. 设置前端环境变量

在 Vercel 项目环境变量中添加：

```env
VITE_API_BASE_URL=https://你的用户名-me1ody-ai-search-backend.hf.space
```

注意不要在末尾加 `/`。

### 3. 部署并测试

Vercel 部署完成后，打开前端地址。

1. 点击右上角钥匙图标。
2. 输入你设置的 `PUBLIC_TEST_TOKEN`。
3. 搜索一个问题，例如：`RAG 是什么`。

如果后端是 Demo 模式，应该能看到完整的检索链路、来源、回答和引用审计。

## 三、发给同学测试

发给同学两个信息：

```text
前端地址：https://你的-vercel-项目.vercel.app
测试密码：你的 PUBLIC_TEST_TOKEN
```

不要把 Hugging Face 后端地址和 API Key 发给别人。

## 四、注意事项

- Hugging Face 免费 CPU Space 可能会冷启动，第一次打开会慢一些。
- 当前数据库使用 SQLite，适合同学短期测试；长期使用建议改成托管 Postgres。
- 如果真实搜索消耗太快，可以临时把后端 `DEMO_MODE=true`。
- 如果遇到跨域问题，确认后端变量 `CORS_ORIGINS=["*"]`。
- 如果前端提示测试密码错误，确认 Vercel 的 `VITE_API_BASE_URL` 指向的是正确后端，并且前端右上角保存了正确密码。

## 五、推荐上线顺序

1. 后端 Hugging Face Space 先设 `DEMO_MODE=true`。
2. 推送代码到 Hugging Face，确认 `/api/ready` 正常。
3. 前端部署到 Vercel，设置 `VITE_API_BASE_URL`。
4. 前端输入测试密码，确认 Demo 搜索正常。
5. 再把后端改成 `DEMO_MODE=false`，测试真实 Tavily + DeepSeek 搜索。
