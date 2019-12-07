## arXiv 论文数据源提取与分析

- [Paper Filtering](#paper-filtering)
- [Paper Information Extraction](#paper-information-extraction)
- [Paper Counting](#paper-counting)
- [Sota Data Completing](#sota-data-completing)
- [Sota Data Deduplication](#sota-data-deduplication)

### Paper Filtering

Filtering papers by sota information mainly depends on abstract process, if one paper's abstract contains some keywords, it will be selected and its table will be output by HTML.

- Input：

  - arXiv daily update： [https://arxiv.org/list/cs.AI/recent](https://arxiv.org/list/cs.AI/recent)

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

### Paper Counting

Counting Papers' num by key words, such as algorithms name and research domain.

- Input: key words by English.
- Output structure:
  - "TechField"
    - "total_counts for all keywords in TechField"
    - "keywords"
      - "total_counts for all years"
      - "every year paired with paper counts"
- Sample output (for one keywords):

```json
{"Cross-entropy": {
            "total counts": 58000,
            "1984": 32,
            "1985": 38,
            "1986": 37,
            "1987": 61,
            "1988": 79,
            "1989": 104,
            "1990": 108,
            "1991": 106,
            "1992": 130,
            "1993": 174,
            "1994": 183,
            "1995": 216,
            "1996": 252,
            "1997": 345,
            "1998": 361,
            "1999": 390,
            "2000": 386,
            "2001": 398,
            "2002": 457,
            "2003": 488,
            "2004": 605,
            "2005": 741,
            "2006": 771,
            "2007": 900,
            "2008": 961,
            "2009": 1000,
            "2010": 1190,
            "2011": 1230,
            "2012": 1280,
            "2013": 1520,
            "2014": 1850,
            "2015": 2470,
            "2016": 4040,
            "2017": 7560,
            "2018": 13500,
            "2019": 13500,
            "2020": 11
        }}
```



- Challenges
  - Search keywords on Semantic Scholar, rather than Google Scholar, due to the reCAPTCHA.
  - Although we used multi-processing, scraping data by Selenium was slowly.

### Sota Data Completing

Completing URL by papers' title or some keywords.

- Input:
  - Papers' title.
  - Methods' name, issuing date, research domain, datasets' name, metrics' value.
- Output:
  - Papers' title (if not exist).
  - Papers' URL.
- Two kinds of samples (by title and by keywords):

```json
{"Recurrent Neural Network-Based Sentence Encoder with Gated Attention for Natural Language Inference": {
        "Recurrent Neural Network-Based Sentence Encoder with Gated Attention for Natural Language Inference": [
            "https://www.semanticscholar.org/paper/Recurrent-Neural-Network-Based-Sentence-Encoder-for-Chen-Zhu/ceb7dddbd0c51f511c4ba97d328b48fd10d2a7fc",
            "https://arxiv.org/pdf/1708.01353.pdf"
        ]
    }}
```

```json
"BERT-Base (single model)": {
        "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding": [
            "https://www.semanticscholar.org/paper/BERT%3A-Pre-training-of-Deep-Bidirectional-for-Devlin-Chang/df2b0e26d0599ce3e70df8a9da02e51594e0e992",
            "https://arxiv.org/pdf/1810.04805.pdf"
        ]
    }
```



- Challenges:
  - For Keywords searching, metrics' value, issuing year, datasets' name were used as constrains, many keywords which can find correct title have been filtered. 

### Sota Data Deduplication

Find items in sota data which are deduplicated. Construct set which all items kept same metrics' value, and then filtering them by dataset's name, i.e. delete items which are not in same dataset.

- Input: sota data.
- Output: deduplicated items.
- Samples:

| id                                   | task               | dataset  | model                         | metric                         |
| ------------------------------------ | ------------------ | -------- | ----------------------------- | ------------------------------ |
| 33fa1371-c055-496d-b412-4a0026c41475 | Question Answering | bAbi     | Recurrent Relational Networks | {'Mean Error Rate': '0.46'}    |
| 6a3c145a-9efc-4c0e-98f4-36acabb3c1b0 | Question Answering | bAbi     | RR                            | {'Mean Error Rate': '0.46'}    |
| b6233f4b-fb80-44d8-ae2d-a38b70cc001a | Question Answering | SQuAD2.0 | {Bert-Span} (single model)    | {'EM': '80.35', 'F1': '83.33'} |
| be3c18a5-4977-46f0-9c22-00b078767c7b | Question Answering | SQuAD2.0 | Unnamed submission by zw4     | {'EM': '80.35', 'F1': '83.33'} |





