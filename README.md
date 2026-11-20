# docqa —— 带检索的文档问答

把一个 markdown 文档切块、按问题打分选出最相关的几块，拼进提示词让 DeepSeek 回答，每句标出依据的块号。

这是 Python 8 周计划第 7 周的项目，用来把 requests、文件读写、字符串处理串成一条完整链路。

## 怎么跑

环境：Windows + Anaconda Python 3.9，依赖 `requests`；测试额外要 `pytest`。

```powershell
# 设 DeepSeek API key
$env:DEEPSEEK_API_KEY = "sk-..."

# 提问
python main.py
# 用户：How does the context manager work?
```

中文提问会先翻译成英文再检索，回答用中文。

## 目录

```
docqa/
├── main.py               # 主程序：切块、打分、选块、调模型
├── check_v1.py           # 10 题基准评测，直接跑会调 10 次 API
├── expected.json         # 评测标准：每题的关键词和正确块号
├── test_main.py          # 单元测试（17 个，不联网）
└── data/
    └── harness_survey.md # 语料：一篇 agent harness 综述
```

## 流程

1. `get(text)`：按 `##` / `###` 切块。没有章名、正文为空的块丢掉，所以块号从 1 开始。
2. `split_words`：转小写、只留 `[a-z]+`、去停用词。
3. `score`：Σ(词频 × IDF) + 标题词频 × IDF × 3，再除以 √正文词数做长度归一。
4. `pick`：从第 2 名开始，相邻两块分数比值 ≥ 1.5 就算断层，取断层前的 top-k；k 限定在 2~6。跳过第 1 名是因为它常常是章引导块（分数高但内容泛），只取它会答不全；从第 2 名开始看，保证至少取到 2 块。
5. 拼提示词：每块写成 `[块号] 章名 节名 正文`，要求模型只依据资料、每句标 `[数字]`、找不到就说「资料里没有找到」。
6. `chat`：调 `deepseek-chat`，`temperature=0`。

检索分整体偏低且没有明显断层时，程序会打一条预警，并在提示词前加一句「资料可能不相关」。

## 评测

- `python check_v1.py`：10 题（8 题英文、2 题中文）。每题判两件事：回答是否引用了正确块号、关键词命中率是否 ≥ 0.6。最近一整轮 10 题全过；但模型输出不稳定（有一题在 True/False 之间来回翻过），看趋势不看单轮。
- `python -m pytest -q`：17 个单元测试，覆盖 7 个不调 API 的函数，不联网、不依赖当前目录。

## 已知限制

- 检索是词面匹配，同义改写（vocabulary mismatch）会漏。
- 中文提问靠翻译链，翻译错了就查不到。
- 只有一篇语料，换文献要重新验证打分假设。
- 回答质量一半在检索、一半在模型本身。
