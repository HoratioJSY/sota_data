### arXiv 论文数据源提取与分析

- input：

- - arxiv更新论文 - AI分类： https://arxiv.org/list/cs.AI/recent

- output：

- - task, method【bottom line】
  - dataset, evaluations(metric, metric value)；paper, date
  - code

- procedure:

- - 更新论文追踪与检测

  - 论文核心内容爬取【可以先进行这一步】

  - - from abstract only

    - from full content

    - - paragraphs
      - forms

示例 1：Federated Transfer Reinforcement Learning for Autonomous Driving

* 标题识别：*Method*：Federated Transfer Reinforcement Learning；*Task*：Autonomous Driving
* 摘要/正文识别：fail

示例 2：Training Multiscale-CNN for Large Microscopy Image Classification in One Hour

* 标题识别：*Method*：Multiscale-CNN；*Task*：Large Microscopy Image Classification
* 摘要识别：accuracy，99%，one hour；
* 正文识别：Broad Bioimage Benchmark Collection BBBC021 image set

示例 3：ALBERT: A Lite BERT for Self-supervised Learning of Language Representations

* 标题识别：*Method*：ALBERT, A Lite BERT；*Task*：Self-supervised learning of language representations
* 摘要识别：fail
* 正文识别：RACE, accuracy, 89.4%；GLUE, score, 89.4；SQUAD 2.0，F1 score, 92.2