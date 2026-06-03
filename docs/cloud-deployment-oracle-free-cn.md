# Worldpanel Data QC Assistant 免费云服务器部署说明

## 推荐架构

第一版共享生产环境建议使用：

- Oracle Cloud Always Free VM：运行 Python 后台、文件解析、AI 审核、LibreOffice Slides 渲染。
- Cloudflare Tunnel 或服务器公网 IP：提供 HTTPS 访问入口。
- 共享访问密码：所有拥有密码的人可以登录使用。
- 本地 SQLite：先保存项目、运行记录、上传文件和导出报告。

Supabase 暂时不作为主部署平台。它适合后续保存数据库、用户、项目和文件，但 Supabase Edge Functions 不适合直接跑当前 QC 引擎，因为它有内存、CPU 和运行时长限制，也不能安装 LibreOffice 这类系统组件。

## 为什么不用 Supabase 单独部署

当前工具需要完成这些任务：

- 上传较大的 Excel、PPTX、PDF 文件。
- 解析 `.xlsx`、`.xls`、`.pptx`、`.pdf`。
- 调用大模型做数据逻辑、市场常识、标注和 Slides 视觉检查。
- 将 PPTX 页面渲染为图片，再交给模型做视觉审核。
- 后台持续运行，并在页面显示进度。

Supabase 可以支持数据库、认证、存储和短任务函数，但不适合作为这个 Python 检查引擎的运行环境。后续稳定后，可以把 SQLite 迁移到 Supabase Postgres，把上传文件迁移到 Supabase Storage。

## 云服务器准备

创建一台 Oracle Cloud Always Free Ubuntu VM。

建议规格：

- Ubuntu 22.04 或 24.04。
- ARM Ampere A1 或免费 x86 VM。
- 至少 2GB 内存，处理大 PPT 时更建议 4GB。
- 磁盘建议 50GB 以上。

## 上传代码

在服务器上创建目录并上传本项目代码到任意临时目录，例如：

```bash
/home/ubuntu/worldpanel-qc-source
```

进入项目目录：

```bash
cd /home/ubuntu/worldpanel-qc-source
```

运行安装脚本：

```bash
sudo bash deploy/cloud/install_ubuntu.sh
```

脚本会安装：

- Python 和虚拟环境。
- LibreOffice：用于 `.xls` 转换和 PPTX 转 PDF。
- poppler-utils：用于 PDF 页面转 PNG。
- Python 依赖。
- systemd 服务 `worldpanel-qc`。

## 配置密码和模型

编辑服务器环境变量：

```bash
sudo nano /etc/worldpanel-qc.env
```

需要填写：

```bash
WORLDPANEL_QC_ACCESS_PASSWORD=共享访问密码
WORLDPANEL_QC_LLM_ENDPOINT=http://218.241.201.171:28180/jdgpt/v1/chat/completions
WORLDPANEL_QC_LLM_MODEL=gpt-5.4
WORLDPANEL_QC_LLM_TOKEN=模型密钥
WORLDPANEL_QC_LLM_ENABLED=1
WORLDPANEL_QC_LLM_OCR_ENABLED=1
```

不要把真实模型密钥写进 Git 或共享文档。

## 启动服务

```bash
sudo systemctl enable --now worldpanel-qc
sudo systemctl status worldpanel-qc
```

本机健康检查：

```bash
curl http://127.0.0.1:8877/api/health
```

如果返回正常，说明后台已经启动。

## 开放给所有拥有密码的人

### 方案 A：Cloudflare 临时隧道

适合先快速上线，但每次重启隧道后 URL 可能变化。

安装 cloudflared 后运行：

```bash
cd /opt/worldpanel-qc
bash deploy/cloud/start_cloudflare_tunnel.sh
```

把终端中显示的 `https://...trycloudflare.com` URL 和共享密码发给同事。

### 方案 B：固定域名或固定公网 IP

适合正式长期使用。

可以用公司已有域名配置到这台服务器，或使用 Cloudflare Named Tunnel。这样 URL 可以固定，不会随重启变化。

## 运维命令

查看状态：

```bash
sudo systemctl status worldpanel-qc
```

查看日志：

```bash
sudo journalctl -u worldpanel-qc -n 100
```

重启：

```bash
sudo systemctl restart worldpanel-qc
```

停止：

```bash
sudo systemctl stop worldpanel-qc
```

## 已支持的云端能力

- `.xlsx` Excel 检查。
- `.xls` 通过 LibreOffice 转换后检查。
- `.pptx` 结构化文字、表格、图表数值检查。
- `.pptx` 页面通过 LibreOffice 转 PDF，再通过 poppler 转 PNG，支持 Slides 视觉审核。
- `.pdf` 文本层和低文本页检查。
- AI 数据逻辑和市场常识审核。
- 共享密码登录。
- 运行进度条和预计剩余时间。

## 后续增强

当使用人数变多后，建议再做：

- SQLite 迁移到 Supabase Postgres。
- 上传文件迁移到 Supabase Storage 或对象存储。
- 用户从共享密码升级为个人账号。
- 加任务队列，避免多人同时跑大文件时互相影响。
