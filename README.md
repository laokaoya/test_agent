# 🎯 AI儿童英语陪伴产品测试平台

一个专业的AI产品测试和评测平台，用于评估AI与儿童英语互动的质量，支持自动化测试、数据分析和可视化。

---

## 📁 项目结构

```
test_agent/
├── README.md                 # 项目说明文档（本文件）
├── app.py                    # Flask主程序
├── .env                      # 环境变量配置（需自行创建）
├── requirements.txt          # Python依赖包（待生成）
│
├── config/                   # 📋 配置文件目录
│   ├── preset_children.json  # 预设测试角色配置
│   └── preset_criteria.json  # 预设评分标准配置
│
├── data/                     # 💾 数据文件目录
│   ├── test_results.json     # 测试结果（JSON格式，完整数据）
│   └── test_results.csv      # 测试结果（CSV格式，简化版）
│
├── docs/                     # 📚 文档目录
│   ├── AI儿童英语陪伴产品评测体系.md
│   ├── 内测通过标准_快速参考卡.md
│   ├── 如何添加内置角色.md
│   ├── 如何添加内置评分标准.md
│   ├── 数据可视化仪表盘使用说明.md
│   ├── 数据存储说明.md
│   ├── CSV数据字典.md
│   ├── 自动测试使用说明.md
│   └── 角色模板.txt
│
├── scripts/                  # 🔧 脚本目录
│   ├── restart.ps1           # PowerShell自动重启脚本
│   └── start_web.py          # Python启动脚本
│
└── templates/                # 🎨 HTML模板目录
    ├── index.html            # 主测试页面
    └── dashboard.html        # 数据可视化仪表盘
```

---

## 🚀 快速开始

### 1. 环境准备

**系统要求：**
- Python 3.8+
- Windows / macOS / Linux

**安装依赖：**
```bash
pip install flask requests python-dotenv google-generativeai
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# Dify API配置
DIFY_API_KEY=your_dify_api_key_here
DIFY_API_URL=https://your-dify-api-url/v1/chat-messages

# Gemini API配置
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. 启动应用

**方式1：直接运行**
```bash
python app.py
```

**方式2：使用启动脚本**
```bash
python scripts/start_web.py
```

**方式3：使用PowerShell脚本（Windows）**
```powershell
.\scripts\restart.ps1
```

### 4. 访问应用

- **主测试页面：** http://localhost:5000
- **数据仪表盘：** http://localhost:5000/dashboard

---

## 📖 核心功能

### 1️⃣ **自动化测试**
- 模拟5种典型儿童角色（害羞型、话多型、好奇型、自信型、抗拒型）
- 自动生成儿童回复并与AI对话
- 支持自定义对话轮数（默认3轮）
- 自动循环测试功能

### 2️⃣ **多维度评分**
- 13项专业评测指标
- Gemini AI严格评分（从儿童视角）
- 角色体验评分（0-100分）
- 加权平均分计算

### 3️⃣ **数据可视化**
- 实时概览统计
- 各角色表现对比（柱状图）
- 评分指标雷达图
- 评分趋势分析（折线图）
- 最近测试记录

### 4️⃣ **数据记录**
- JSON完整结构化数据
- CSV简化表格数据
- 自动追加保存
- 支持Excel打开

---

## 🎭 预设测试角色

| 角色 | 年龄 | 类型 | 难度 | 测试目的 |
|------|------|------|------|----------|
| 🐻 小熊 | 5岁 | 害羞型 | ⭐⭐⭐⭐⭐ | 测试能否让沉默孩子开口 |
| 👧 Yoyo | 6岁 | 话多型 | ⭐⭐⭐ | 测试话题管理与逻辑引导 |
| 🧒 乐乐 | 7岁 | 好奇型 | ⭐⭐⭐⭐ | 测试能否捕捉兴趣点延伸 |
| 👸 Emma | 8岁 | 自信型 | ⭐⭐ | 测试主导型孩子的平衡互动 |
| 🙅 豆豆 | 6岁 | 抗拒型 | ⭐⭐⭐⭐⭐ | 测试能否打破初期拒绝 |

**自定义角色：** 可通过编辑 `config/preset_children.json` 添加新角色

---

## 📊 评测指标体系

### 13项核心指标

| 指标 | 权重 | 说明 |
|------|------|------|
| 互动吸引力 | 1.5 | 能否吸引孩子注意力 |
| 鼓励开口能力 | 1.3 | 能否让孩子愿意开口 |
| 提问引导能力 | 1.2 | 能否通过提问引导表达 |
| 情感支持表达 | 1.2 | 能否提供情感支持 |
| 教学效果 | 1.2 | 能否有效传递知识 |
| 话题连贯性 | 1.1 | 对话是否连贯流畅 |
| 年龄适配度 | 1.1 | 是否适合孩子年龄 |
| 词汇拓展引导 | 1.0 | 能否引导学习新词 |
| 句式引导能力 | 1.0 | 能否引导丰富句式 |
| 回复丰富度 | 1.0 | 回复是否生动丰富 |
| 创意激发能力 | 1.0 | 能否激发想象力 |
| 耐心等待能力 | 1.0 | 是否给予思考时间 |
| 错误纠正技巧 | 0.9 | 能否温和纠正错误 |

**自定义标准：** 可通过编辑 `config/preset_criteria.json` 添加新标准

---

## ✅ 内测通过标准

### 核心标准

```
✅ 加权平均分 ≥ 7.0
✅ 单项最低分 ≥ 5.0
✅ 角色体验评分 ≥ 60
✅ 互动吸引力 ≥ 7.5（一票否决）
✅ 鼓励开口能力 ≥ 7.0（一票否决）
✅ 5种角色中至少4种通过（必须包括小熊和豆豆）
✅ 多轮测试通过率 ≥ 80%
```

详见：`docs/内测通过标准_快速参考卡.md`

---

## 📈 数据可视化仪表盘

### 功能模块

1. **概览统计卡片**
   - 累计测试数
   - 今日测试数
   - 总通过率
   - 平均评分

2. **各角色表现对比**（柱状图）
   - 对比5种角色的评分
   - 识别适配性差的角色

3. **评分指标雷达图**
   - 展示13项指标
   - 一眼识别优势短板

4. **评分趋势分析**（折线图）
   - 按日期展示变化
   - 监控时间维度表现

5. **各指标平均分**（横向柱状图）
   - 快速识别需改进指标

6. **最近测试记录**（表格）
   - 最近10条详情
   - 通过/未通过状态

详见：`docs/数据可视化仪表盘使用说明.md`

---

## 🔧 配置说明

### 角色配置

编辑 `config/preset_children.json`：

```json
{
  "role_id": {
    "id": "role_id",
    "name": "角色名",
    "age": 6,
    "type": "角色类型",
    "traits": "## 角色性格\n- 特点1\n- 特点2\n...",
    "opening": "Hello!"
  }
}
```

详见：`docs/如何添加内置角色.md`

### 评分标准配置

编辑 `config/preset_criteria.json`：

```json
{
  "criteria_id": {
    "id": "criteria_id",
    "name": "标准名称",
    "description": "标准描述",
    "prompt": "评分指引...",
    "weight": 1.0
  }
}
```

详见：`docs/如何添加内置评分标准.md`

---

## 📊 数据分析

### 读取JSON数据

```python
import json
import pandas as pd

# 读取完整数据
with open('data/test_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 转换为DataFrame
df = pd.json_normalize(data)

# 分析平均分趋势
df['scores.average'].plot()

# 按角色类型分组
df.groupby('child.type')['scores.average'].mean()
```

### 读取CSV数据

```python
import pandas as pd

# 读取CSV
df = pd.read_csv('data/test_results.csv', encoding='utf-8-sig')

# 查看基本信息
print(df.info())
print(df.describe())

# 按角色类型统计
df.groupby('角色类型')['评分_平均分'].mean()
```

详见：`docs/数据存储说明.md` 和 `docs/CSV数据字典.md`

---

## 🛠️ 常见问题

### Q1: 启动后显示"无法连接到Dify"？
**A:** 检查 `.env` 文件中的 `DIFY_API_KEY` 和 `DIFY_API_URL` 是否正确。

### Q2: Gemini评分失败？
**A:** 检查 `.env` 文件中的 `GEMINI_API_KEY` 是否正确，并确认网络可以访问Gemini API。

### Q3: 数据文件在哪里？
**A:** 
- JSON完整数据：`data/test_results.json`
- CSV简化数据：`data/test_results.csv`

### Q4: 如何添加新的测试角色？
**A:** 编辑 `config/preset_children.json`，参考 `docs/如何添加内置角色.md`

### Q5: 如何自定义评分标准？
**A:** 编辑 `config/preset_criteria.json`，参考 `docs/如何添加内置评分标准.md`

### Q6: 如何重启应用？
**A:** 运行 `scripts/restart.ps1`（Windows）或手动停止Python进程后重新运行 `python app.py`

---

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| [AI儿童英语陪伴产品评测体系](docs/AI儿童英语陪伴产品评测体系.md) | 完整评测体系和通过标准 |
| [内测通过标准_快速参考卡](docs/内测通过标准_快速参考卡.md) | 快速查看版通过标准 |
| [数据可视化仪表盘使用说明](docs/数据可视化仪表盘使用说明.md) | 仪表盘功能详解 |
| [自动测试使用说明](docs/自动测试使用说明.md) | 自动循环测试功能 |
| [数据存储说明](docs/数据存储说明.md) | JSON和CSV数据结构 |
| [CSV数据字典](docs/CSV数据字典.md) | CSV列名说明 |
| [如何添加内置角色](docs/如何添加内置角色.md) | 角色配置指南 |
| [如何添加内置评分标准](docs/如何添加内置评分标准.md) | 标准配置指南 |
| [角色模板](docs/角色模板.txt) | 角色Markdown模板 |

---

## 🔄 版本历史

### v1.0 (2025-10-18)
- ✅ 完整的评测体系（13项指标）
- ✅ 5种预设测试角色
- ✅ 自动化测试功能
- ✅ 数据可视化仪表盘
- ✅ 自动循环测试
- ✅ 双重数据记录（JSON + CSV）
- ✅ 角色体验评分（0-100分）
- ✅ 完整的文档体系

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📧 联系方式

如有问题或建议，请通过以下方式联系：
- 查看文档目录下的详细说明
- 提交GitHub Issue
- 联系开发团队

---

## 📄 许可证

本项目仅供内部测试使用。

---

**感谢使用AI儿童英语陪伴产品测试平台！🎉**

