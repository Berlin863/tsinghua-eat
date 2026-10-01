# 今天吃什么 —— 小红书清华美食版

用 Playwright 采集小红书上的清华美食推荐帖, 通过随机问卷估计你今天的偏好,
输出 **食堂 + 菜品 Top5**。数据只保存在本地。

## 快速开始

```bash
pip install -r requirements.txt

# 1) 采集(首次会打开浏览器让你扫码登录, 之后复用登录态)
python main.py scrape

# 2) 解析帖子 -> data/food_db.json
python main.py build

# 3) 开饭! (随机抽题 -> Top5)
python main.py
```

`python main.py update` = build + recommend 一步到位。

## 网页版(可发 GitHub Pages)

```bash
python main.py export          # 生成 docs/data.js(完整版, 本地用)
# 双击 docs/index.html 即可离线使用, 手机浏览器打开也行
python main.py export --public # 发布公网前重导出: 去掉帖子标题/链接/ID
```

网页是纯静态的(问卷+打分逻辑的 JS 移植, 无后端), 采集仍然只在本地 Python 里做。
发到 GitHub Pages:

```bash
git init && git add . && git commit -m "今天吃什么"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main && git push -u origin main
# 仓库 Settings → Pages → Source: Deploy from a branch → 分支 main, 目录 /(docs)
# 1~2 分钟后访问 https://<你的用户名>.github.io/<仓库名>/
```

注意: GitHub Pages 免费版要求**公开仓库**; `.gitignore` 已排除登录态(browser_profile/)、
原始帖子(data/posts.json)和本地 food_db, 公开版 data.js 只含聚合统计数字。

## 工作原理

```
xhs_scraper.py   Playwright 采集: 真实 Edge/Chrome + 持久化登录态,
                 真人节奏滚动/停顿, 每帖增量保存到 data/posts.json;
                 帖子正文+评论都会读(评论靠拦截页面自然加载的接口响应)
      |
food_parser.py   文本解析: 识别食堂(含别名)+菜品(130种种子词典, 最长匹配),
                 同句"就近配对"得到 食堂-菜品 对; 正文权重 1.0、评论 0.5、
                 避雷差评 -1.0(手动语料的 negative_desc 字段);
                 统计提及/点赞/时效, 还能发现种子库之外的高频食堂
      |
question_bank.py 78 道题、8 个维度的偏好问题库; 每次分层随机抽 12 题,
                 每个选项映射到偏好向量的权重(辣/酸/米面/预算/位置...)
      |
recommender.py   打分 = 0.55*口味匹配(内积) + 0.45*小红书热度,
                 再乘 场景/预算/就近/清真/尝鲜 修正 + 高斯随机抖动,
                 多样性去重后输出 Top5(同一食堂最多 2 条)
```

食堂基础信息来自清华大学饮食服务中心官网(18 个食堂 + 清青系列特色窗口),
即使一篇帖子都没采, 也能靠种子库冷启动推荐; 采集之后由真实帖子数据接管。

## 命令细节

```
python main.py scrape --keywords "清华食堂,清芬园,紫荆美食"   # 自定义关键词
python main.py scrape --max-per-kw 10 --max-total 40          # 更保守的上限
python main.py scrape --backfill-comments   # 给评论为空的旧帖补采评论
python main.py recommend --questions 16 --top 5               # 多问几题
python main.py recommend --auto                               # 随机作答(测试)
```

推荐界面里: `r` = 同一份偏好重新掷骰(推荐会变化), `q` = 重新问一轮。

## 防封禁策略(以及为什么这样做)

不破解任何检测, 而是**当一个安静的真人用户**:

- 本机真实 Edge/Chrome 浏览器 + `browser_profile/` 持久化用户目录, 登录态可长期复用
- 移除 `--enable-automation` 自动化标记
- 所有操作之间 2~9 秒随机停顿, 小步滚动、偶尔回滚、鼠标随机晃动
- **硬上限**: 每个关键词最多 15 帖、单次运行最多 60 帖; 想采更多就隔几小时再跑
- 遇到滑块/安全验证**不绕过**, 停下来等你在浏览器里手动完成
- 搜索结果"所有帖子"客观上拿不全(平台只返回排序后的部分结果),
  换不同关键词多跑几次可以逐步扩大覆盖

## 合规提醒

- 仅限个人学习研究使用, 采集内容归小红书及原作者所有, 请勿二次分发数据
- 保持默认的克制频率; 数据只留在本地 `data/` 目录
- 想更"官方"可以删掉 scraper, 只用种子库也能跑推荐

## 目录结构

```
main.py            入口 CLI
xhs_scraper.py     采集器
food_parser.py     帖子 -> food_db.json
question_bank.py   78 题偏好问卷库
recommender.py     偏好估计 + 打分 + Top5
seed_data.py       官方食堂信息 + 130 种菜品属性词典
data/manual_posts.json  手动补充语料(避雷写 negative_desc)
data/posts.json    采集到的帖子
data/food_db.json  解析后的推荐语料
browser_profile/   浏览器持久化配置(登录态)
```
