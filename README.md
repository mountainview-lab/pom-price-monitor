# POM价格监控系统 - 云端版

自动采集隆众资讯网POM价格数据，生成可视化仪表盘，支持飞书通知。

## 部署步骤

### 第一步：创建GitHub仓库

1. 打开 https://github.com/new
2. 仓库名称：`pom-price-monitor`
3. 选择 **Public**（公开）
4. 点击 **Create repository**

### 第二步：上传代码

**方式1：使用GitHub网页上传**
1. 在仓库页面点击 "uploading an existing file"
2. 把 `pom-cloud` 文件夹里的所有文件拖进去
3. 点击 **Commit changes**

**方式2：使用Git命令行**
```bash
cd pom-cloud
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/你的用户名/pom-price-monitor.git
git push -u origin main
```

### 第三步：配置GitHub Secrets

1. 进入仓库 → Settings → Secrets and variables → Actions
2. 点击 **New repository secret**
3. Name: `FEISHU_WEBHOOK`
4. Value: `https://open.feishu.cn/open-apis/bot/v2/hook/7f7dafb3-e08d-438b-a662-485f9ee1cf12`
5. 点击 **Add secret**

### 第四步：部署到Vercel

1. 打开 https://vercel.com
2. 点击 **Add New...** → **Project**
3. 选择你的GitHub仓库 `pom-price-monitor`
4. 点击 **Deploy**
5. 等待部署完成，获得公网地址（如 `https://pom-price-monitor.vercel.app`）

### 第五步：测试

1. 进入GitHub仓库 → Actions
2. 点击 **Daily POM Price Scrape**
3. 点击 **Run workflow** → **Run workflow**
4. 等待执行完成
5. 访问Vercel地址查看仪表盘

---

## 项目结构

```
pom-price-monitor/
├── .github/
│   └── workflows/
│       └── scrape.yml    # GitHub Actions定时任务
├── data/
│   └── prices.json       # 价格数据
├── index.html            # 仪表盘页面
├── scraper.py            # 爬虫脚本
├── vercel.json           # Vercel配置
└── README.md
```

## 自动更新

- **每天18:00**（北京时间）自动抓取数据
- 抓取后自动更新仪表盘
- 自动发送飞书通知

## 手动触发

在GitHub仓库页面：
Actions → Daily POM Price Scrape → Run workflow
