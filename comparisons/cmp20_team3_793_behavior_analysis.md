这次运行的核心问题是：Ken 从记忆提出一个没有出生日期文档支持的候选，Bob 和 Eric 读到后沿着同一候选验证，最终把彼此的同意当成了额外证据。Eric 第一个提交，团队回答 23/07；本地标准答案是 29/02。

分析范围：三个 Agent 的全部已落盘工具调用、11 条公共留言、关键推理步骤、结果与评测文件，以及本地数据集中的对应标注文档。下述时间是运行开始后的相对时间；JSONL 的 time 是该步落盘时间，不代表这一步开始思考的时间。没有重新运行原实验，也没有用外网补充原 Agent 当时没有获得的证据。

**运行规模与结果。**

| Agent | 元数据步数 / 已落盘步数 | search | 发留言 | 读留言 | bash | 结束状态 |
|---|---:|---:|---:|---:|---:|---|
| Bob | 45 / 44 | 103 | 2 | 7 | 1 | 被取消 |
| Eric | 41 / 41 | 120 | 4 | 11 | 1 | 首个 finish，成为团队答案 |
| Ken | 31 / 30 | 86 | 5 | 6 | 2 | 被取消 |

总耗时 639.8 秒，约 10 分 40 秒。309 次搜索全部返回 5 条结果，没有工具输出以 Error: 开头；已落盘回复的 stop_reason 全部为 tool_calls。因而这次记录显示的是相关证据没有检索到、后续推断失控，不能据此认定检索服务报错或模型被截断。

配置上限是每人 60 步、整题 30 分钟，结束时均未达到。因此 Eric 的提交是主动判断，不是被本次配置的步数或时间上限强制触发。

三人共检索到 466 篇不同文档。309 个查询中有 305 个不同字符串，问题主要是语义和方向重复，不是原样重复同一查询。1545 个返回条目中，约 69.8% 是已经出现过的文档。三个 Agent 都获得过的文档有 90 篇。

运行记录报告 input_tokens 合计 21,676,892，output_tokens 合计 296,758。这是各次请求累计 usage，包含重复发送的上下文，不是独立阅读了两千多万 token 的新材料，也不能直接当作未考虑缓存的费用。三人已落盘 reasoning 合计约 106 万字符，存在明显的反复枚举与反复犹豫。

来源：[结果文件](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/results/793.json)、[评测文件](/mnt/data2/users/puning.yang/Explore/evals_deepseek-flash/cmp20_team3_deepseek-flash/results/793_eval.json)。

**Ken：最积极分享线索，也最先把没有证据的记忆变成团队共同候选。**

Ken 前期主要做了三件事：搜索两个孩子同生日的报道；枚举小说叙述者姓名并与婴儿出生组合；从医院改名日期倒推生日。他公开提出过女王纪念命名、医院并购更名、George Floyd 抗议后移除旧名称等方向。05:10 的留言 #7 提供了具体 docid 85902，并请求队友检查是否存在医院改名。这是早期少数可以继续追查的具体文档线索。

但他的搜索边界过早集中在医院于 2021—2022 年改名，问题只说出生事件截至 2021 年已经发生，并没有给出如此窄的改名区间。三人后来都在相似的日期窗口、名人家庭和叙述者名单之间来回搜索，没有形成明确的任务划分。

关键转折在 Ken 第 17 步，落盘时间 05:39。他在枚举 Frances 这一名字时，声称记得 Fallon 家两个女儿分别出生于 2013-07-23 和 2014-07-23，并反复用“我记得”“这是广为人知的事实”强化这个记忆。这个候选出现在本步搜索之前，不是搜索返回的出生报道给出的。他随后运行 Python 得到：2014-07-23 + 539 天 = 2016-01-13，并开始猜测 Roosevelt Hospital / Mount Sinai West。

第 20 步尤其值得看。他已经明确写出，语料没有确认 Fallon 的事实或医院改名，候选也可能错误；但同一步仍发布了“Strong candidate found”的留言 #8，把两个生日作为事实列出。附上的 96765、48312 是与 Conversations with Friends 有关的文档，并不能证明两个孩子的生日。

这条留言既要求队友核实同生日，也要求核实医院，说明他知道仍有待查之处。但表达层次有偏差：两个孩子同生日被写成既定事实，医院被突出为主要待核实环节。队友于是更容易接受家庭身份，把精力转到医院，而没有先验证最基础的出生日期。

之后 Ken 没有完全停止探索。他继续查 Fallon、Roosevelt、UCLA Santa Monica，也查 Stonewall Jackson Memorial Hospital / Carilion Rockbridge Community Hospital 等替代医院，并再次用 Python 做倒推日期。他提出候选前搜索 41 次，从第 17 步起又搜索 45 次，却没有获得对应家庭的出生日期或出生医院证据。

沟通上的问题是：06:31 发布候选之后，他直到结束再无新留言；后续大量怀疑与替代想法留在自己的推理里。最后第 30 步还把 29/02 列入可能的特殊生日，但没有据此执行新查询或公开提醒。运行记录显示他进入第 31 步后被取消，不能据此判断其未落盘内容会做什么。

对 Ken 最需要关注的是：候选生成本身有创造性，证据等级却在分享时被抬高；发现证据不足以后，没有把降置信度和撤回条件同步给队友。

关键位置：[Ken 第 17 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Ken.jsonl:17)、[第 20 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Ken.jsonl:20)、[第 30 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Ken.jsonl:30)、[留言 #8](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/board.txt:48)。

**Bob：原本持有与候选冲突的记忆，读到队友结论后没有解决冲突就改口。**

Bob 前期同样在同生日新闻、叙述者名字、医院改名之间搜索，还尝试英国 NHS、女王纪念命名、澳大利亚 Lady Cilento Children's Hospital 更名等方向。他 03:21 才发第一条留言 #4，主要重述“改名日期减去 539 天”的方法，没有带来一个已验证的新候选。他总共发两条留言，第二条已经接近提交结束。

最值得关注的是第 10 步，约 01:38。他枚举脱口秀主持人的孩子时写道：

> Jimmy Fallon: Winnie (July 2013), Frances (Dec 2014). No.

这说明他当时记得两个孩子出生月份不同，并据此排除了 Fallon。仅凭这条记忆不能完成外部事实核验，但它至少构成了一个必须核实的内部冲突。

第 28 步，约 07:05，Bob 读到 Ken 的留言 #8。紧接着第 29 步，他开始接受 Frances 出生于 2014-07-23 的说法，并说自己认为这一日期正确。期间没有新检索文档解决“Dec 2014”与“July 23, 2014”的冲突，他也没有把这个冲突发到留言板。

他之后确实进行了核查：搜索 Fallon 出生报道、代孕地点、Roosevelt / Mount Sinai West、UCLA Santa Monica；到第 39 步还自行搜索 Conversations with Friends，返回 48312、1381、91784 等文档；第 42 步用 Python 复核了日期运算。接受候选后共有 36 次搜索，因此不能简单说他完全没有验证动作。

问题在于，验证动作没有带来两个孩子同生日的证据，结论却继续升温。他把注意力集中在出生医院和改名日期，最后在 10:25 的留言 #10 写“CONFIDENT CANDIDATE”，把“两个孩子同生日”称为广泛报道的事实，又说最后只剩医院这一处未核实。他早期关于 Frances 出生于 12 月的记忆就此消失。

Bob 第 43 步还开始“回忆”Mount Sinai 曾于 2016-01-13 发布相关改名公告，但没有文档支撑。这体现了一个危险趋势：先由假定生日算出一个目标日期，再逐渐把这个目标日期体验为自己记得的历史事件。

他第 44 步调用 read_messages(wait_seconds=30)，直接读到了 Eric 的最终候选 #11；之后进入第 45 步时被取消，没有实际调用 finish。

对 Bob 最需要关注的是：他原本有潜在的反证线索，却在团队候选出现后没有保护和核实它；自己的搜索只支持了文学关联的一部分，公共结论却变成了对整个候选的强背书。

关键位置：[Bob 第 10 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Bob.jsonl:10)、[读到候选的第 28 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Bob.jsonl:28)、[接受候选的第 29 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Bob.jsonl:29)、[留言 #10](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/board.txt:71)。

**Eric：搜索最多，曾想到正确日期方向，最后却把同源意见当成独立确认并提交。**

Eric 共搜索 120 次、读留言 11 次，是两项调用最多的人。他前期尝试了同生日新闻、医院改名、叙述者名字等方向，并找到 CBS 的一个相似故事：一对夫妻与他们的第一个孩子同生日。他在留言 #6 明确指出那是第一个孩子，与题目要求不符。这次排除是合理的。

第 14 步，约 03:13，Eric 已经明确想到正确答案方向。他写到：如果两个孩子都是闰日出生，会是很罕见的新闻；直接写出了 29/02，并考虑第二个孩子出生于 2020-02-29、医院在 2021 年 8 月改名的可能性。

然而，这一步实际执行的是“539 days”、same day as their first child、same birthday as their first 等通用查询。通读全部 120 个查询，没有针对 leap、February 29、29 February 或 29/02 的查询。他也没有把闰日这个有区分度的假设发给队友。这是本次最明显的“想到了，但没有转化成行动”的遗漏。

第 25 步，约 07:01，Eric 读到 Ken 的候选 #8。第 26 步起开始计算 2014-07-23 + 539 天并围绕 Fallon 与 Mount Sinai West 搜索；从读到候选的这一阶段起又做了 46 次搜索。

08:26 的留言 #9 仍保留了重要怀疑：两个孩子的精确出生日期需要确认，出生医院不明，医院改名日期无法确认；他还提出代孕地点可能不在纽约，从而影响所猜医院的合理性。这些怀疑本应让候选保持低证据等级。这里的代孕法规说法是 Eric 在日志里的主张，本分析没有对其作法律事实核验。

到第 40 步，他仍承认没有找到家庭出生信息或医院文档，却不断用“这两个生日我有把握”“医院只是确认性线索”说服自己接受 23/07。他还把由假定生日推出的 2016-01-13 称为精确吻合，尽管没有一个独立查得的医院改名日期可以与之比较。

10:35，Eric 先发留言 #11，再调用 read_messages(wait_seconds=30)。因为 Bob 的留言 #10 已经存在，这次读取直接返回，不会额外等待 30 秒。他约四秒后在第 41 步提交，置信度 72%。因此他执行了“发候选、检查留言”的形式步骤，但并没有获得新的独立出生日期证据。

第 41 步最关键的一句是：

> Bob independently reached the same conclusion (23/07).

这个判断与信息流不符。Bob 已经在第 28 步读过 Ken 的候选，他的最终同意不能被视为又一个独立生成的同生日事实来源。两人独立算出了同一个加法结果，不能等同于独立确认加法输入是真实生日。

最终答案还把之前公开承认不确定的医院关系写成“与医院改名时期相符”。最终引用的 96765、48312 都不能证明两个孩子的生日、出生医院或医院改名日期。Eric 是实际提交者，因此他在提交前将这些缺口收窄为“只有医院一处未核实”，直接决定了团队错误答案。

关键位置：[Eric 第 14 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Eric.jsonl:14)、[第 25 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Eric.jsonl:25)、[第 40 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Eric.jsonl:40)、[第 41 步](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/Eric.jsonl:41)、[留言 #9](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/traces/793/board.txt:59)。

**三个人如何互相影响。**

| 时间 | 事件 | 对团队判断的影响 |
|---|---|---|
| 01:38 左右 | Bob 记得 Frances 在 12 月出生，排除 Fallon | 潜在冲突留在个人推理中 |
| 03:13 左右 | Eric 明确提出 29/02 / 闰日可能性 | 没有对应查询，也未分享 |
| 05:39 左右 | Ken 从记忆生成 Fallon 同生日假设并计算日期 | 一个无出生文档支持的故事开始成形 |
| 06:31 | Ken 发布 #8，称找到强候选 | 团队出现共同锚点 |
| 07:01 / 07:05 左右 | Eric / Bob 先后读到 #8 | 二人搜索都转向 Fallon 和医院 |
| 08:26 | Eric 发布 #9，仍承认日期和医院待核实 | 没有要求在确认前暂停接受候选 |
| 10:25 | Bob 发布 #10，称 CONFIDENT CANDIDATE | 同源意见变成对候选的强背书 |
| 10:35 | Eric 发 #11，并读到 Bob 的背书 | 把 Bob 视为独立确认 |
| 10:39 左右 | Eric 调用 finish | 团队任务结束，其余二人被取消 |

这次没有形成基于新证据的三方确认。更准确的信息流是：Ken 的记忆假设进入留言板，Bob 和 Eric 接受这个假设并寻找支持，随后 Bob 的支持被 Eric 当成了独立验证。三个人都做了额外搜索，但搜索并没有补齐他们在公共结论里声称已确定的出生事实。

**证据质量和工具条件，需要分别看。**

1. 最基本的实体关系没有文档支持：两个孩子的出生日期相同、第二个孩子的出生医院、该医院的确切改名日期，三项都未获得对应证据。三人却逐渐把缺口描述成“只剩医院待查”。
2. 最终两篇引用 96765、48312 的可见片段讲的是 Conversations with Friends 的影视改编及 Frances 这一角色；片段没有明确说她是小说叙述者。即便文学关联成立，也不足以建立 Fallon 家庭与题干之间的关系。
3. 日期运算本身正确，但输入没有被证明。用假定出生日期算出目标改名日期，再说目标日期与猜测医院“吻合”，不构成独立验证。
4. 本次配置是 BM25、每次 5 条、每条最多前 512 token，get_document=false。Agent 没有获取全文的工具，因此不能把未打开全文当成它们的违规。但三篇标注文档根本未被检索到，全文截断也不能单独解释本次失败。
5. Agent 多次把“搜索没有返回”解释成“语料里没有”。这两个结论并不等价。本地数据里实际有完整的相关证据。
6. 三人的前期方向高度相似，没有落实谁负责找家庭、谁负责医院、谁负责文学线索和反证。公开计划很多，清晰的任务认领、核验结果和排除清单很少。
7. 结束条件是首个 finish 立即结束全队，没有独立的证据检查。该机制让 Eric 的错误提交结束任务，但不能推断多等一会儿就一定能答对：Bob 已明确表示准备提交相同答案，Ken 也没有公开给出新的反证。

相关实现：[运行配置](/mnt/data2/users/puning.yang/Explore/runs/cmp20_team3_deepseek-flash/config.yaml:65)、[片段截取实现](/mnt/data2/users/puning.yang/Explore/BrowseComp-Plus/searcher/tools.py:38)、[首个提交结束任务](/mnt/data2/users/puning.yang/Explore/teamboard/team.py:75)、[提交前的提示词要求](/mnt/data2/users/puning.yang/Explore/prompts/system.md:12)。

**本地标准证据显示的真实线索，以及题干自身的一处问题。**

标注为相关的三篇文档是 29584、44381、92422，三人均未检索到。评测中的 retrieval recall、citation precision 和 citation recall 都是 0。这里的引用指标是相对标注文档计算，不能单凭 precision=0 就断言每篇被引文档内容都不真实。

- 29584：Brooklyn couple welcomes second Leap Day baby in family。Dane 和 Lindsay Demchak 的第二个孩子 Scout 在 2020-02-29 出生，哥哥 Omri 在 2016-02-29 出生；医院是 Coney Island Hospital。它直接支持答案 29/02。
- 44381：Scout Finch。明确写 Scout 是 To Kill a Mockingbird 的叙述者和主人公，支持名字线索。
- 92422：Coney Island Hospital renamed in honor of Ruth Bader Ginsburg。支持该医院的改名关系。

但 92422 的文章头部和正文日期都是 2021-08-06，写的是医院现在改名。2020-02-29 至 2021-08-06 实际是 524 天；加 539 天得到的是 2021-08-21。也就是说，本地标注证据与题干“539 天”之间存在 15 天的差异，需要核查题目构造或其采用的改名日期依据。这里能够确认的是本地文档的日期不一致，尚未对外部医院历史作独立核验。

这不影响两个孩子生日由出生报道直接确定为 29/02，也不能支持团队提出的 23/07；但它意味着后续设计自动核验规则时，不宜把该题的 539 天当成完全可靠的筛选条件。

来源：[相关文档标注](/mnt/data2/users/puning.yang/Explore/BrowseComp-Plus/topics-qrels/qrel_evidence.txt:102)、[本地题目及证据原文，第 20 行](/mnt/data2/users/puning.yang/Explore/BrowseComp-Plus/data/browsecomp_plus_decrypted.jsonl:20)。这一步是分析者事后读取标注作复盘，原 Agent 的 trace 没有显示它们获得过这些文档。

**如果据此改进实验，优先观察四件事。**

1. 每个公共候选必须分别标明“已检索事实、个人记忆、推测”，让同生日、名字关联、医院关系各自带上支持它的片段，避免一个局部相关 docid 替整条故事背书。
2. 给核查者明确的反证任务。比如 Bob 一旦记得 Frances 生于 12 月，就应公开这个冲突并核实；Eric 的闰日假设应立即转成少量有区分度的查询，而不是继续通用改写。
3. 把新增证据作为升高置信度的条件。Python 日期加法、队友重复同一生日、反复“回忆”同一个细节，都不应增加对出生事实的置信度。
4. 提交时逐项检查哪些关键关系有证据、哪些仍有冲突；同时记录题干自身可能有误的约束。具体结束机制可以再设计，但这次最先需要纠正的是证据等级与独立性的判断。
