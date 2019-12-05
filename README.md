## arXiv 论文数据源提取与分析

- Paper Filtering
- Paper Information Extraction

### Paper Filtering

Filtering papers by sota information mainly depends on abstract process, if one paper's abstract contains some keywords, it will be selected and its table will be output by HTML.

- Input：

  - arXiv daily update： https://arxiv.org/list/cs.AI/recent

- Output data：

  - Paper title
  - Paper url
  - Paper abstract

- Output: 

  - Filtered paper
    - Strict mode: filtering by "state of the art" like keywords.
    - Non strict mode: filtering by "state of the art" like keywords and metrics keywords.

  - Filtered reason: the sentences that including keywords.
  - Table extraction: illustrating informative table by  HTML.
  - Sota items in table (not necessary).

- Sample:
```json
{"https://arxiv.org/abs/1911.08935": {
        "paper": "Rule-Guided Compositional Representation Learning on Knowledge Graphs",
        "dateline": "Submitted on 20 Nov 2019",
        "Selected Reason": [
            "Extensive experimental results illustrate that RPJE outperforms other state-of-the-art baselines on KG completion task, which also demonstrate the superiority of utilizing logic rules as well as paths for improving the accuracy and explainability of representation learning."
        ],
        "informative table": "https://horatiojsy.github.io/table/7",
        "Table 8: Link prediction results on FB15K-237.": [
            [
                "Best-Models: RPJE",
                "Best-MR: 207"
            ],
            [
                "Best-Models: RPJE",
                "Best-MRR: 0.470"
            ],
            [
                "Best-Models: RPJE",
                "Best-Hits@10(%): 62.5"
            ]
        ]
    }}
```




- Challenges:
  - If we should filtering sota papers by paper content (considering latex file downloading time)
  - Errors in HTML paper, some latex tags can't transform to XML tags, such as front color, cite format, superscript  and subscript etc.
- LaTex source code downloading time can not control, if web environment is not good, downloading time would longer than 5 min.
  

### Paper Information Extraction

- Title processing
- Abstract processing
- Content processing (table)

#### Title processing

Extracting "Task" and "Method" which paper's title may contained, and recommend similar existing task.

- Input: Title list
- Output:
  - Paper title
  - Method, Task, Task recommendation

- Sample:

```json
{"Regularized Evolution for Image Classifier Architecture Search": [
        "method: Regularized Evolution",
        "task: Image Classifier Architecture Search",
        "task recommendation: Neural Architecture Search 0.6153846153846154"
    ]}
```



- Challenges:
  - Extracting mainly by "for" and "with", constrained by num of prep.<2 and conj.==0. Mode and condition are too strict to extracting enough results.
  - For task recommendation, first we should find a valid threshold or enlarge the margin of different task; second, edit distance is sensitive for string length, such as "Machine Reading" is close to "Metric Learning" than "Machine Reading Comprehension". Third, word embedding may be suitable for computing similarity.

#### Abstract processing

Extracting lines that contained performance information, and get the "metric" and "performance value".

- Input: abstract list
- Output:
  - Informative lines
  - All metrics and values
  - Paired metric and value
  - If value are relative performance
  - Dataset (if extracted )
  - Metrics recommendation (not good)

- Sample:

```json
{"https://arxiv.org/abs/1810.04805v2": {
        "informative_line: ": [
            "It obtains new state-of-the-art results on eleven natural language processing tasks, including pushing the GLUE score to 80.5% (7.7% point absolute improvement), MultiNLI accuracy to 86.7% (4.6% absolute improvement), SQuAD v1.1 question answering Test F1 to 93.2 (1.5 point absolute improvement) and SQuAD v2.0 Test F1 to 83.1 (5.1 point absolute improvement)."
        ],
        "results: ": [
            [
                "GLUE",
                "accuracy",
                "F1",
                "F1"
            ],
            [
                "80.5%",
                "7.7%",
                "86.7%",
                "4.6%",
                "1.1",
                "93.2",
                "1.5",
                "2.0",
                "83.1",
                "5.1"
            ],
            [
                [
                    "GLUE",
                    "80.5%"
                ],
                [
                    "accuracy",
                    "86.7%"
                ],
                [
                    "F1",
                    "93.2"
                ],
                [
                    "F1",
                    "83.1"
                ]
            ]
        ],
        "Need Skip?": "No"
    }}
```



- Challenges:
  - Some metrics and values are implicit, such as one metric paired with two values, these implicit results were hard to solve. 
  - In most case, paired metric and value by distance in string is ok, but these are also some failed examples, such as "F1-score and AUC equal to 0.91 and 0.93".

#### Content processing (table)

Extracting evaluation table which contained performance information, if table labeled best results, extracting and output it.

- Input: arXiv URL list
- Output:
  - Table captions
  - Table content
  - Best table items
- Two kinds of Samples:

```json
{"https://arxiv.org/abs/1906.02448": {
        "Table 2: Factor analysis on Zh→En translation, the results are average BLEU scores on MT03∼06 datasets.": [
            [
                "Systems: RNNsearch",
                "Average: 37.73"
            ],
            [
                "Systems: RNNsearch+ word oracle",
                "Average: 38.94"
            ],
            [
                "Systems: RNNsearch+ word oracle+ noise",
                "Average: 39.50"
            ],
            [
                "Systems: RNNsearch+ sentence oracle",
                "Average: 39.56"
            ],
            [
                "Systems: RNNsearch+ sentence oracle+ noise",
                "Average: 40.09"
            ],
            [
                "Best-Systems: RNNsearch+ sentence oracle+ noise",
                "Best-Average: 40.09"
            ]
        ],
        "Table 3: Case-sensitive BLEU scores (%) on En→De task. The “‡” indicates the results are significantly better (p<0.01) than RNNsearch and Transformer.": [
            [
                "Systems: RNNsearch",
                "newstest2014: 25.82"
            ],
            [
                "Systems: RNNsearch+ SS-NMT",
                "newstest2014: 26.50"
            ],
            [
                "Systems: RNNsearch+ MIXER",
                "newstest2014: 26.76"
            ],
            [
                "Systems: RNNsearch+ OR-NMT",
                "newstest2014: 27.41‡"
            ],
            [
                "Systems: Transformer (base)",
                "newstest2014: 27.34"
            ],
            [
                "Systems: Transformer (base)+ SS-NMT",
                "newstest2014: 28.05"
            ],
            [
                "Systems: Transformer (base)+ MIXER",
                "newstest2014: 27.98"
            ],
            [
                "Systems: Transformer (base)+ OR-NMT",
                "newstest2014: 28.65‡"
            ],
            [
                "Best-Systems: RNNsearch+ OR-NMT",
                "Best-newstest2014: 27.41‡"
            ],
            [
                "Best-Systems: Transformer (base)+ OR-NMT",
                "Best-newstest2014: 28.65‡"
            ]
        ]
    }}
```

```json
{"https://arxiv.org/abs/1906.02448": [
        "informative table: http://jiangsiyuan.com/table/0",
        {
            "Table 2: Factor analysis on Zh→En translation, the results are average BLEU scores on MT03∼06 datasets.": [
                [
                    "Best-Systems: RNNsearch+ sentence oracle+ noise",
                    "Best-Average: 40.09"
                ]
            ],
            "Table 3: Case-sensitive BLEU scores (%) on En→De task. The “‡” indicates the results are significantly better (p<0.01) than RNNsearch and Transformer.": [
                [
                    "Best-Systems: RNNsearch+ OR-NMT",
                    "Best-newstest2014: 27.41‡"
                ],
                [
                    "Best-Systems: Transformer (base)+ OR-NMT",
                    "Best-newstest2014: 28.65‡"
                ]
            ]
        }
    ]}
```



- Challenge:
  - Too many table format to extracting useful information.
  - Downloading time should be considered.

