import re
import json
import nltk
import time
import sqlite3
import urllib.request
import numpy as np
from tqdm import tqdm
from bs4 import BeautifulSoup
from fuzzywuzzy import process
from selenium import webdriver
from sota_paper_selection import SotaSelection
from utils import Distance, AbsUtils, ContentReader, ContentProcess




class Analyses:
    """
    get information from title, abstract, paper content
     - task and method from paper title
     - metric, datasets, value from abstraction
     - table, best methods and value from paper content
    """
    def __init__(self):
        self.conn = sqlite3.connect('./test.db')

    def title_process(self):

        cursor_t = self.conn.cursor()
        title_list = cursor_t.execute('SELECT ID, Paper FROM PaperSelection')

        cursor_task = self.conn.cursor()
        cursor_task.execute('''CREATE TABLE IF NOT EXISTS TitleProcess
                            (ID TEXT PRIMARY KEY,
                            Paper TEXT,
                            Method TEXT,
                            Task TEXT,
                            TaskRecommend TEXT)''')

        split_patern = re.compile(r'\s(using|a|an|the|)\s|\:|a\s', re.I)

        cursor_task.execute('SELECT TaskTag FROM Tags')
        task_list = [i[0] for i in cursor_task.fetchall()]

        for title_item in title_list:
            title_r = {}
            try:
                tokens = nltk.word_tokenize(title_item[-1])
            except:
                print(title_item[-1])
                print(type(title_item[-1]))
                quit()

            tag = nltk.pos_tag(tokens)
            _, pos_list = zip(*tag)
            prep_index = [i for i, pos in enumerate(pos_list) if pos == 'IN']
            conj_index = [i for i, pos in enumerate(pos_list) if pos == 'CC']

            if len(prep_index) < 2 and len(conj_index) == 0:
                if 'for' in tokens:
                    title_split = title_item[-1].split(' for ')
                    method = split_patern.split(title_split[0])[-1]
                    task = split_patern.split(title_split[1])[0]
                    title_r["method"] = method
                    title_r["task"] = task
                elif 'with' in tokens:
                    title_split = title_item[-1].split(' with ')
                    task = split_patern.split(title_split[0])[-1]
                    method = split_patern.split(title_split[1])[0]
                    title_r["method"] = method
                    title_r["task"] = task

            recommend = process.extract(title_item[-1], task_list, limit=1)
            recommend = dict(recommend)

            for k, v in recommend.items():
                if v > 80:
                    title_r["recommend"] = k

            try:
                self.conn.execute('INSERT INTO TitleProcess VALUES (?, ?, ?, ?, ?)',
                                  (title_item[0], title_item[-1], title_r.get('method'),
                                   title_r.get('task'), title_r.get("recommend")))
            except:
                self.conn.execute("""UPDATE TitleProcess SET Paper = (?),
                                                             Method = (?),
                                                             Task = (?),
                                                             TaskRecommend = (?)
                                                             WHERE ID = (?)""",
                                  (title_item[-1], title_r.get('method'), title_r.get('task'),
                                   title_r.get("recommend"), title_item[0]))

        self.conn.commit()

    def abs_extraction(self, recommend=False):

        cursor_t = self.conn.cursor()
        abs_list = cursor_t.execute('SELECT ID, Abstract FROM PaperSelection')
        # self.conn.execute('DROP TABLE AbstractProcess')
        cursor_m = self.conn.cursor()
        cursor_m.execute('''CREATE TABLE IF NOT EXISTS AbstractProcess
                                    (InformativeLines TEXT PRIMARY KEY,
                                    ID TEXT,
                                    Skip TEXT,
                                    Metric TEXT,
                                    RecommendM TEXT,
                                    RecommendD TEXT)''')

        cursor_m.execute('SELECT TaskTag FROM Tags')
        metric_name = [i[0] for i in cursor_m.fetchall() if i[0] is not None]

        cursor_d = self.conn.cursor()
        cursor_d.execute('SELECT DatasetTag FROM Tags')
        dataset_name = [i[0] for i in cursor_d.fetchall() if i[0] is not None]

        num_pattern = re.compile(r'\d+%|\d+\.\d+%|\d+\.\d+')
        key_pattern = re.compile("\s(%s)(\s|\,|\.)" % ('|'.join(metric_name)), re.I)
        data_pattern = re.compile('(%s)' % "|".join(dataset_name), re.I)

        for abs_item in abs_list:

            lines = re.split(r'\.\s', abs_item[-1])

            informative_line = [line for line in lines
                                if num_pattern.search(line) is not None
                                and key_pattern.search(line) is not None]

            if len(informative_line) > 0:

                for index, infor_line in enumerate(informative_line):
                    one_result = {"Txt": infor_line}
                    key_list = [i.group()[1:-1] for i in key_pattern.finditer(infor_line)]
                    num_list = [i.group() for i in num_pattern.finditer(infor_line)]
                    valid_key_list, valid_value_list = Distance.string_distance(infor_line, key_list, num_list)

                    if data_pattern.search(infor_line) is not None:
                        dataset_list = [i.group() for i in data_pattern.finditer(infor_line)]
                        _, valid_d_list = Distance.string_distance(infor_line, valid_value_list, dataset_list)

                        try:
                            assert len(valid_d_list) == len(valid_value_list)
                            matched = zip(valid_key_list, valid_value_list, valid_d_list)
                        except:
                            matched = zip(valid_key_list, valid_value_list)
                    else:
                        matched = zip(valid_key_list, valid_value_list)

                    one_result['metric'] = str(list(matched))

                    if recommend:
                        metric_recommend = process.extract(infor_line, metric_name, limit=4)
                        one_result["recommend metric"] = dict(metric_recommend)

                        dataset_recommend = process.extract(infor_line, dataset_name, limit=4)
                        one_result["recommend dataset"] = dict(dataset_recommend)

                    if re.search(r'\s(by|than|over)\s', infor_line, re.I) is not None:
                        r_tokens = ',\/:;-=+*#()~'
                        str_list = infor_line.translate(str.maketrans(r_tokens, ' ' * len(r_tokens))).split()
                        by_index = [index for index, string in enumerate(str_list)
                                    if string == 'by'
                                    or string == 'than'
                                    or string == 'over']
                        num_index = [str_list.index(value) for value in valid_value_list]
                        min_d = [min([abs(i - j) for j in num_index]) for i in by_index]
                        if True in (np.array(min_d) < 5): one_result['Need Skip?'] = 'True'
                    else:
                        one_result['Need Skip?'] = "False"

                    if one_result.get('Need Skip?') is None: one_result['Need Skip?'] = 'True'
                    try:

                        self.conn.execute('INSERT INTO AbstractProcess VALUES (?, ?, ?, ?, ?, ?)',
                                          (one_result.get('Txt'), abs_item[0], one_result.get('Need Skip?'),
                                           one_result.get('metric'), one_result.get("recommend metric"),
                                           one_result.get("recommend dataset")))
                    except:
                        self.conn.execute("""UPDATE AbstractProcess SET ID = (?),
                                                                     Skip = (?),
                                                                     Metric = (?),
                                                                     RecommendM = (?),
                                                                     RecommendD = (?)
                                                                     WHERE InformativeLines = (?)""",
                                          (abs_item[0], one_result.get('Need Skip?'),
                                           one_result.get('metric'), one_result.get("recommend metric"),
                                           one_result.get("recommend dataset"), one_result.get('Txt')))
            else:
                self.conn.execute('INSERT INTO AbstractProcess (ID) VALUES (?)', (abs_item[0],))
        self.conn.commit()

    def content_process(self):

        cursor_u = self.conn.cursor()
        url_list = cursor_u.execute('SELECT ID, URL FROM PaperSelection')
        # self.conn.execute('DROP TABLE AbstractProcess')
        cursor_m = self.conn.cursor()
        cursor_m.execute('''CREATE TABLE IF NOT EXISTS ContentProcess
                                            (ID TEXT PRIMARY KEY,
                                            HTML TEXT)''')

        for u_ in url_list:
            content_vanity = ContentReader.arxiv_vanity_reader(u_[-1])
            with open("./data/table_key_tag.json", 'r') as f:
                key_name = json.load(f)

            if content_vanity is None:
                try:
                    content_raw = ContentReader.raw_data_reader(u_[-1])

                    if content_raw is not None:
                        informative_table, html_list = ContentProcess.get_informative_table(content_raw, key_name, raw_data=True)
                    else:
                        informative_table = []
                        html_list = []
                except:
                    continue
            else:
                informative_table, html_list = ContentProcess.get_informative_table(content_vanity, key_name)

            if len(html_list) > 2:
                html_page = "\n".join(html_list)
                self.conn.execute('INSERT INTO ContentProcess VALUES (?, ?)',
                                  (u_[0], html_page))
                self.conn.commit()


if __name__ == "__main__":
    a = Analyses()
    a.content_process()