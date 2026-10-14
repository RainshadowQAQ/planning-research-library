---
title: 真实规划案例参数与资料链研究
type: domain
topic: planning-case-evidence
decision: 确定场地字段可提取性、跨文件核验要求和具体缺件
source: 五份用户工作案例与本轮取得的官方资料
status: complete
preset: standard-token-limited
validation: normal
created: 2026-09-21
updated: 2026-09-21
verified_claims: 1
unverified_claims: 9
disputed_claims: 0
overturned_claims: 0
---

# 真实规划案例参数与资料链研究

## 结论

五份文件已经足够定义产品工作流：助手应先产出带证据的场地资料表，再把跨文件矛盾和缺件交给从业者处理。没有必要要求用户另行发明“边界、时点或质量门槛”。真正需要补齐的是对应地段、对应版本和对应审批阶段的原件。[1][2][3][4][5]

参数必须保存为“来源主张”，而不是场地唯一事实。面积、GFA、PR、高度都需要同时保存范围、阶段、日期、单位和出处。Y/NE-KTS/17 已证明同一方案至少有总场地面积与发展面积两个合理分母；A/YL-KTN/1131 又证明数值翻倍可能只是纠正旧计算，而非实体扩建。[6][7]

OZP／Notes、规划许可、建筑批准和契约／豁免是四条独立证据链。任何一条都不能代替另外三条。BO／Lands 的主要问题不是缺少公开政策，而是个案的 approved plans、occupation permit、lease／Conditions、registered instruments 及 executed waiver 尚未取得。[11][12][13]

## 字段与时间口径

| 案例 | 官方证据核实到的内容 | 产品应怎样记录 | 未解决项 |
|---|---|---|---|
| Y/NE-KTS/17 | 2023 年会议文件载明场地约 10,072㎡，含约 1,954㎡政府土地；发展面积约 9,888㎡，住用 GFA 约 23,732㎡，PR 2.4 以发展面积为分母。文件还说明早期资料被后续提交取代。[6] | Site Area、Government Land、Development Area 分字段；PR 保存分母、方案版本及近似符号；旧提交标 superseded | 现行图则及最终审批／执行状态未在本轮核实 |
| A/YL-KTN/1131／828 | /1131 载明约 86㎡、总楼面约 110㎡；55→110㎡是纠正两层建筑此前未完全计入，场地边界、布局及高度相同。该文件自身把上一许可失效日分别写成 24 和 25 June 2025。[7] | 变化原因独立字段；“total floor area”不自动改名为法定 GFA；冲突日期并列待核 | /1131 最终决定与 /828 原决定通知尚未核实 |
| A/YL-KTN/535 | 2019 官方文件把 /535 同时列为曾获批准的 hobby farm／caravan camp 及后来因未履行条件而撤销的个案。[8] | 批准、撤销为独立事件；不能只显示 Approved | 精确批准／撤销日期、失效条件需原决定及撤销通知 |
| A/NE-TKL/785 | 文件载明 D.D.84、约 744.5㎡，其中约 680㎡政府土地；另有约 18.6㎡ G/IC 小部分在评估中按轻微边界调整处理。[9] | DD、政府土地比例及混合分区脚注不可省略；申请上限不当作实测现状 | /785 最终决定、/565 原申请参数需另取原件 |
| Y/NE-LYT/9 | 2009 会议记录显示先延期，随后仅“部分同意”；本轮未由官方文件核实工作表中的 852.16㎡、161.4㎡、PR 0.2。[10] | 记录程序阶段与部分批准范围；未核实数值不可进入确认字段 | 主文件／申请表、具体获同意边界和参数 |
| 沙田／东涌学生宿舍比较 | 2026 DEVB 公布沙田约 0.11ha、PR 9.5、120mPD、GFA 约 10,000㎡；东涌约 0.25ha、PR 9、160mPD、GFA 约 23,000㎡。它们是 EOI／拟议卖地参数，并非已批项目。[14] | 资料性质标 EOI；“约”面积不能单独用来重算精确 GFA | Annex A 的精确地盘面积、最终卖地章程与完成的法定程序 |
| 17–18 Chung Shan Terrace | S/KC/32 的官方说明提到 Chung Shan Terrace R(B)1 区域维持现有规模或最高 PR 2.0、SC 66.6%，但未证明其与目标 17–18 号的确切边界相同。[15] | 地区层级的图则说明只能列为候选适用资料；须以地段／申请边界叠合后确认 | 273.95／464.5㎡口径、PR 8.28、地段身份、现行 Notes、批准图则及豁免原件均未核实 |

## 可自动提取与必须覆核的界线

可以自动生成候选字段：完整申请编号、文件类型及日期、地段／DD 原文、图则版本、约数和不等号、面积及政府土地分项、用途、参数名称和单位、条件原文、部门意见、程序事件，以及原文页码／区域。每项均保留文件哈希和出处。

以下不得自动升格为场地事实：当前有效状态、申请参数是否获批、total floor area 是否等于某法定 GFA 定义、混合分区的准确面积、不同面积的边界关系、旧个案是否仍可作有效先例，以及规划批准是否满足建筑或契约要求。没有找到文件表示“缺资料”，不是“不适用”。

质量门槛可直接从真实工作定义：不串案、不漏单位／约数／脚注、不混申请与决定、不把历史资料当现行资料；每个确认字段能回到原文；矛盾值并列；计算值显示分子、分母、范围和公式。准确率百分比应在建立人工金标准后测量，不应成为开始工作的前置问题。

## OZP 与 Notes 资料链

每个场地至少要形成：研究边界 → 图则编号及版本状态 → 地图上的分区 → 对应 Notes／Remarks → 规划意向 → 对研究用途的 Column 1／2 或其它控制 → 人工确认。

版本必须按阶段命名，例如 approved、draft、proposed amendment、explanatory statement 和 EOI。沙田研究本轮同时遇到 S/ST/36、37、38、39 的不同程序材料，足以说明只抄一个图则号会造成时间错误。[16][17] 东涌 S/I-TCE/2 的一般 Notes 能证明 Notes 属图则组成部分，但本轮没有完整核实 C(1) 的用途表和 Remarks，不能据此断言学生宿舍的完整规划路径。[18]

## BO／Lands 资料链

建筑资料应按确切地址／PRN／楼宇身份，在 BRAVO 或 Building Information Centre 取得 occupation permit、最新 approved general building plans，以及与拟议转换相关的批准／修订图。BRAVO 提供符合范围的私楼最新批准图、结构计算及相关记录；找不到线上记录时仍可能存在纸本记录。[11]

土地资料应先用 IRIS 由地址或地段查 PRN，取得 current／historical register、Government Lease／New Grant／Conditions、memorial 及未记注册文件资料；之后才判断需向业主或 DLO 索取什么个案文件。[12] LandsD 对 waiver 的公开说明只证明豁免是暂时放宽契约限制、获批时可附条件及费用，不能证明某场地已有豁免。[13]

A/YL-KTN/1131 本身也显示这四条证据链不能合并：文件载明 Block Government Lease 的农业用途／建构限制、一个地段已有 STW、其它地段存在租契违规；即使规划申请获批，相关 STW 仍须另行申请或修改且不保证批准。[7]

## 具体缺件清单

| 优先 | 缺件 | 解决什么问题 | 取得途径 |
|---|---|---|---|
| 1 | A/K1/265 的冻结官方文件集及研究时点 | 建立首个字段与高亮金标准 | 现有本地原件，逐份记录哈希和版本；本轮未把其它案例数值代入 |
| 1 | 各案例原 decision／revocation／lapse 通知 | 区分建议、决定、撤销、有效期 | TPB 个案页、会议记录或决定通知；按完整编号分别保存 |
| 1 | 目标场地确切地段／申请边界 | 对应 OZP、Notes、政府土地及面积口径 | 申请图、Lot Index、IRIS PRN／register；人工核对边界 |
| 1 | 当前及研究时点适用的 OZP map、Notes、Remarks、ES | 核实分区、规划意向、用途及参数上限 | TPB／PlanD 官方版本记录；保存 approved／draft 状态 |
| 2 | 17–18 Chung Shan Terrace 的 OP、approved plans、转换／修订批准 | 核实楼宇批准用途、范围和 GFA／楼层 | BRAVO／BIC1、BIC3、BIC4；可能需注册、付费或纸本检索 [11] |
| 2 | 该址 lease／Conditions、register、相关 memorial | 核实地段、契约用途及 273.95／464.5㎡范围 | IRIS 付费 ad-hoc search；先由地址／lot 解析 PRN [12] |
| 2 | executed special waiver、附图、修订和有效期 | 判断豁免是否存在及覆盖什么 | 业主／获授权代表及 LandsD／DLO；公开政策不能替代 [13] |
| 2 | DD114／Autocamper 各 lot 的 lease、STW／短租或政府土地同意文件 | 区分规划许可与土地许可、核实建筑和通道范围 | IRIS、持有人及相关 DLO；按 lot 建 manifest |
| 3 | Y/NE-LYT/9 主文件及同意范围；/535 原决定与撤销；/565 原文件 | 补齐工作表内尚未由官方原件验证的数字和时间 | TPB 原案件档案；取得失败保持缺件，不用相似案替代 |

付费查询前先生成 request manifest：地址、PRN、lot／DD、所需文件、覆盖日期、预计费用和待解决问题。软件可以追踪请求和导入用户取得的官方副本；不应静默购买、操作私人账户或把未取得解释成不存在。BRAVO 当前页面列有查阅及副本费用，实际下单前必须重查。[19]

## 对产品与规格的建议

1. 以 SiteFact、ApplicationEvent、ApplicabilityRecord 和 ResearchIssue 分别保存参数主张、申请事件、适用性及缺口；高亮只是证据入口。
2. 为字段增加 `scope_kind`、`source_stage`、`asserted_by`、`approximation`、`denominator`、`supersedes` 和 `conflict_reason`；这比新增更多自由文本备注更重要。
3. 先用可提取文字的官方 PDF 建立金标准；对地图、扫描 Notes 和图则只在必要字段无法读取时启用 OCR，并保存 OCR 覆盖范围及人工覆核状态。
4. 下一步无需再问用户抽象的技术门槛；应制作 A/K1/265 样板资料表，再据实际漏项确定 OCR、模型与资源配置。

## 未解决问题

- A/K1/265 的具体研究时点仍未由本轮输入指定；默认“现行”必须在每次检索时写明截至日期。
- 本轮没有购买或登录 BRAVO／IRIS，因此 Chung Shan Terrace 与农村个案的建筑／土地原件仍属缺件。
- 没有完成每个案例的现行法定状态审计；本报告定义证据链与缺件，不给出发展或法律可行性结论。
- 单一官方来源的多数事实未取得独立发布者交叉验证，按本研究的 normal 验证标准保持 medium／unverified。

## 来源附录

| ID | 支持的内容 | 发布者与链接 | 文件／发布日期 | 查阅日 | 置信度 |
|---|---|---|---|---|---|
| [1] | AGR 案例比较的用户工作形式 | [用户提供 AGR potential study.docx](/Users/huangtommy/Desktop/DS/DD/Autocamper%20Planning%20Research/AGR%20potential%20study.docx) | 未核实 | 2026-09-21 | 仅证明工作材料内容 |
| [2] | 历次申请、用途及参数的用户工作形式 | [用户提供 Autocamper planning research.docx](/Users/huangtommy/Desktop/DS/DD/Autocamper%20Planning%20Research/Autocamper%20planning%20research.docx) | 未核实 | 2026-09-21 | 仅证明工作材料内容 |
| [3] | 场地参数和图则／建筑图的用户工作形式 | [用户提供 Chung Shan Terrace 文件](/Users/huangtommy/Desktop/DS/DD/Chung%20Shan%20Terrace/17%20Chung%20Shan%20Terrace%20-%20Invitation%20for%20Operator.docx) | 未核实 | 2026-09-21 | 仅证明工作材料内容 |
| [4] | 规划案例、条件和拒绝理由的用户工作形式 | [用户提供 DD114 Planning Research.docx](/Users/huangtommy/Desktop/DS/DD/Kam%20Sheung%20Road,%20Tai%20Lam/DD114%20Planning%20Research.docx) | 未核实 | 2026-09-21 | 仅证明工作材料内容 |
| [5] | 跨场地参数比较的用户工作形式 | [用户提供 Compare Table.docx](/Users/huangtommy/Desktop/DS/DD/Tung%20Chung%20Student%20Hostel%20Bid/Compare%20Table.docx) | 未核实 | 2026-09-21 | 仅证明工作材料内容 |
| [6] | Y/NE-KTS/17 面积、GFA、PR 分母和版本 | [TPB 主文件](https://www.tpb.gov.hk/uploads/page/meetings/RNTPC/Y_NE-KTS_17/Y_NE-KTS_17_MainPaper.pdf) | 2023-10-27 会议 | 2026-09-21 | 中；单一官方来源 |
| [7] | A/YL-KTN/1131 参数、历史、Lands 意见及建议条件 | [TPB 主文件](https://www.tpb.gov.hk/uploads/page/meetings/20250801/A_YL-KTN_1131_MainPaper.pdf) | 2025-08 | 2026-09-21 | 高：本轮再次逐行核实；个案最终决定除外 |
| [8] | A/YL-KTN/535 批准后撤销的历史 | [TPB A/YL-KTN/665 主文件](https://www.tpb.gov.hk/en/papers/RNTPC/FSYLE/A-YL-KTN-665/A_YL_KTN_665_Mainpaper.pdf) | 2019-07-05 | 2026-09-21 | 中；回顾性官方来源 |
| [9] | A/NE-TKL/785 边界、政府土地及混合分区 | [TPB 主文件](https://www.tpb.gov.hk/uploads/page/meetings/RNTPC/A_NE-TKL_785/A_NE-TKL_785_MainPaper.pdf) | 2025-01-10 | 2026-09-21 | 中；单一官方来源 |
| [10] | Y/NE-LYT/9 部分同意的程序阶段 | [TPB 第 400 次 RNTPC 会议记录](https://www.tpb.gov.hk/en/meetings/RNTPC/Minutes/m400rnt_e.pdf) | 2009-08-07 | 2026-09-21 | 中；官方记录 |
| [11] | BRAVO 记录范围及纸本退路 | [Buildings Department BRAVO FAQ](https://bravo.bd.gov.hk/faq) | 未注明 | 2026-09-21 | 中；官方渠道 |
| [12] | IRIS 的 register、instrument、PRN 和付费搜索渠道 | [Land Registry IRIS 服务](https://www.landreg.gov.hk/en/services/services_b_2.htm) | 未注明 | 2026-09-21 | 中；官方渠道 |
| [13] | Waiver 的一般性质、条件和费用 | [Lands Department Waivers](https://www.landsd.gov.hk/en/land-disposal-transaction/land-transaction/waivers.html) | 未注明 | 2026-09-21 | 中；官方政策，非个案证明 |
| [14] | 沙田／东涌 EOI 参数及程序状态 | [Development Bureau press release](https://www.devb.gov.hk/en/publications_and_press_releases/press/index_id_15384.html) | 2026-01-20 | 2026-09-21 | 中；官方 EOI 来源 |
| [15] | S/KC/32 中 Chung Shan Terrace 的地区控制 | [政府提交立法会的 S/KC/32 文件](https://www.legco.gov.hk/yr2023/english/brief/skc32_20231013-e.pdf) | 2023-10-13 | 2026-09-21 | 中；非目标地段级结论 |
| [16] | 沙田 C(1) 历史改划参数 | [TPB S/ST/36 主文件](https://www.tpb.gov.hk/en/uploads/RNTPC/paper/S_ST_36_MainPaper.pdf) | 2023-10 | 2026-09-21 | 中；历史阶段 |
| [17] | S/ST/39 法定程序仍在推进的证据 | [TPB Paper 11057](https://www.tpb.gov.hk/uploads/page/meetings/20260424/R_S_ST_39_MainPaper.pdf) | 2026-04 | 2026-09-21 | 中；程序文件 |
| [18] | S/I-TCE/2 Notes 是图则组成部分 | [政府提交立法会的 S/I-TCE/2 文件](https://www.legco.gov.hk/yr16-17/english/brief/sitce2_20170217-e.pdf) | 2017-02-17 | 2026-09-21 | 中；C(1) 条文未完整提取 |
| [19] | BRAVO 当前列示费用 | [Buildings Department BRAVO fees](https://bravo.bd.gov.hk/charges) | 未注明 | 2026-09-21 | 中；下单前应刷新 |

## 时效地图

- 规划、建筑及土地个案状态：每次形成“现行”结论时重新核实；本报告不缓存为长期现行事实。
- 政府记录取得渠道及费用：最迟 2027-03-21 重查；实际下单前立即刷新。
- 历史会议文件中的原文主张不会因时间改变，但其适用性须按新的研究时点重新判断。
- 最早需要重查的是任何被用于“截至现在”的状态；不能以本报告日期代替用户研究时点。
