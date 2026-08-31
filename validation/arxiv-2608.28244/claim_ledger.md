# Claim ledger — arXiv:2608.28244

| ID | Claim | 位置 | 主要证据 | 判定 | 建议 |
|----|-------|------|----------|------|------|
| C01 | deterministic pipeline improves workflow construction | abstract; `main.tex:284-292` | paired B/C: 7→19 raw, 11→43 normalized | 支持，但 magnitude 对 scorer version/normalization 敏感 | v1.2.1 重算；per-family 展开 |
| C02 | local release is inspectable and validation-gated | abstract; `main.tex:399-407` | architecture, approval path, run records, 440-test claim | 支持 | 修 release tag 后更强 |
| C03 | explicit user facts are restored before execution | `local_agent_body.tex:36-44` | 36/47 units corrected；same-response design | 部分支持；没有 field-level authority table | 增加 correction type ledger |
| C04 | no tested unsafe payload was retained before approval | abstract; `agent_evaluation.tex:189-191` | executable-code boundary cases；7/12 safe non-execution；其余 sanitized | 对测试集支持，不代表 OS containment | 当前 scope wording 合理 |
| C05 | valid-request intent preserved in 57/62 cases | `agent_evaluation.tex:177-180` | predefined outcomes on 62 usable cases | 支持；case selection 非随机 | 给 case-level artifacts / family table |
| C06 | local model routing to MadAnalysis is not demonstrated | abstract; `agent_evaluation.tex:259-267` | 0/2 preserved requested analysis stage | 支持且披露充分 | 保持，不要用 backend availability 暗示 routing capability |
| C07 | repeated cross sections agree at about 0.3% | `agent_evaluation.tex:231-235` | 844.3/841.7 and 505.7/504.1 | 数值支持；原因归属过强 | 改为 consistent with MC variation |
| C08 | system is not an autonomous/scientifically self-validating agent | abstract; conclusion | 57/96 problematic cases reach approval；runtime 4/7 | 强支持 | 这是稿件最可信的 scope boundary |
| C09 | novelty is deterministic artifact construction under local small-model interpretation | intro `main.tex:185-200` | narrative contrast to adjacent systems | 部分支持 | capability matrix + shared task comparison |
