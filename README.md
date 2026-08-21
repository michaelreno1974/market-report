# 手机端每日市场快报 · 云端部署说明

电脑关机后，由 GitHub 云端定时生成数据并发布，手机浏览器随时查看。零费用、零第三方依赖（Python 标准库 + curl）。

## 目录结构
```
cloud/
├── index.html            # 手机 H5 页面（GitHub Pages 托管）
├── build_data.py         # 云端数据脚本（生成 report.json）
├── report.json           # 数据文件（工作流每次自动更新）
└── .github/workflows/
    └── daily-report.yml  # 定时任务（工作日 10/11/14/15/17:15 五次）
```

## 一次性部署步骤（约 15 分钟，之后电脑可关机）

1. **注册 GitHub 账号**（若没有）：https://github.com 免费注册。

2. **创建仓库**：New repository，名字如 `market-report`，选 Public 或 Private 均可（Private 也可开 Pages）。

3. **上传代码**：把 `cloud/` 目录下所有文件上传到仓库根目录（index.html、build_data.py、report.json、.github/ 整个文件夹）。

4. **开启 GitHub Pages**：仓库 Settings → Pages → Source 选 `Deploy from a branch`，分支 `main`、根目录 `/` → Save。等 1-2 分钟后访问：
   `https://<你的用户名>.github.io/market-report/`
   手机浏览器打开此地址即看到快报，可"添加到主屏幕"获得近似 App 体验。

5. **确认定时任务生效**：仓库 Actions 页签可见 `daily-market-report` 工作流，cron 已配置工作日 5 次。首次可点 `Run workflow` 手动触发一次验证。

## 更新频率
- 工作日（周一至周五）北京时间：10:00、11:00、14:00、15:00、17:15
- 17:15 那次为收盘完整数据（含股指期货持仓、资金流、推荐）
- 盘中为当时实时快照

## 修改与维护
- **调整频率**：编辑 `.github/workflows/daily-report.yml` 的 cron（UTC 时间 = 北京时间 - 8 小时）。
- **查看数据源**：build_data.py 顶部函数对应各数据接口（腾讯行情/板块、新浪国际行情/全市场榜、中金所期货持仓）。
- **出问题排查**：Actions 页签看运行日志；report.json 是否成功提交；Pages 是否发布成功。

## 说明
- 数据源为公开接口，页面与报告含免责声明，仅供参考，不构成投资建议。
- 属水板块标签为个人偏好维度，与基本面无关。
- 免费额度：GitHub Actions 每月 2000 分钟，本方案约 165 分钟/月，充足。
