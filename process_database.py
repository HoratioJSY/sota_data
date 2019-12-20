import re
import json
import nltk
import time
import sqlite3
import numpy as np
from multiprocessing import Pool
from fuzzywuzzy import process
from sota_paper_selection import SotaSelection
from utils import Distance, AbsUtils, ContentReader, ContentProcess


class Analyses:
    """
    get information from title, abstract, paper content
     - task and method from paper title
     - metric, datasets, value from abstraction
     - table from paper content
    """
    def __init__(self):
        self.conn = sqlite3.connect('./test.db')

    @staticmethod
    def dumps_object(object):
        object_str = json.dumps(object)
        assert type(object_str) == str
        return object_str

    def title_process(self):
        start = time.time()
        cursor_t = self.conn.cursor()
        title_list = cursor_t.execute("""SELECT ID, Paper FROM PaperSelection 
                                         WHERE TitProcess IS NULL""")

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

            recommend = process.extract(title_item[-1], task_list)
            recommend = [i for i in recommend if i[-1] > 80]

            if len(recommend) > 0:
                recommend = dict(recommend)
                title_r["recommend"] = self.dumps_object(recommend)
                self.conn.execute('UPDATE PaperSelection SET TitProcess=(?) WHERE ID=(?)', ('Exist', title_item[0]))
            else:
                title_r["recommend"] = None
                self.conn.execute('UPDATE PaperSelection SET TitProcess=(?) WHERE ID=(?)', ('NoExist', title_item[0]))

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
        print(f'Titles\' Process have been Done: {time.time()-start:.3f}s')

    def abs_process(self, recommend=True):

        start = time.time()
        cursor_t = self.conn.cursor()
        abs_list = cursor_t.execute('SELECT ID, Abstract FROM PaperSelection WHERE AbsProcess IS NULL')
        # self.conn.execute('DROP TABLE AbstractProcess')
        cursor_m = self.conn.cursor()
        cursor_m.execute('''CREATE TABLE IF NOT EXISTS AbstractProcess
                                    (InformativeLines TEXT PRIMARY KEY,
                                    ID TEXT,
                                    Skip INT2,
                                    Metric TEXT,
                                    RecommendM TEXT,
                                    RecommendD TEXT)''')

        cursor_m.execute('SELECT MetricTag FROM Tags')
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
                            matched = dict(zip(valid_d_list, dict(zip(valid_key_list, valid_value_list))))
                        except:
                            matched = dict(zip(valid_key_list, valid_value_list))
                    else:
                        matched = dict(zip(valid_key_list, valid_value_list))

                    matched = self.dumps_object(matched)
                    one_result['metric'] = matched

                    if recommend:
                        metric_recommend = process.extract(infor_line, metric_name, limit=4)
                        metric_recommend = dict(metric_recommend)
                        one_result["recommend metric"] = self.dumps_object(metric_recommend)

                        dataset_recommend = process.extract(infor_line, dataset_name, limit=4)
                        dataset_recommend = dict(dataset_recommend)
                        one_result["recommend dataset"] = self.dumps_object(dataset_recommend)

                    if re.search(r'\s(by|than|over)\s', infor_line, re.I) is not None:
                        r_tokens = ',\/:;-=+*#()~'
                        str_list = infor_line.translate(str.maketrans(r_tokens, ' ' * len(r_tokens))).split()
                        by_index = [index for index, string in enumerate(str_list)
                                    if string == 'by'
                                    or string == 'than'
                                    or string == 'over']
                        try:
                            num_index = [str_list.index(value) for value in valid_value_list]
                        except BaseException as e:
                            new_valid_value_list = [process.extract(value, str_list, limit=1)[0][0] for value in valid_value_list]
                            num_index = [str_list.index(value) for value in new_valid_value_list]

                        min_d = [min([abs(i - j) for j in num_index]) for i in by_index]
                        if True in (np.array(min_d) < 5): one_result['Need Skip?'] = True
                    else:
                        one_result['Need Skip?'] = False

                    if one_result.get('Need Skip?') is None: one_result['Need Skip?'] = False

                    try:

                        self.conn.execute("""INSERT INTO AbstractProcess 
                                             (InformativeLines, ID, Skip, Metric, RecommendM, RecommendD) 
                                             VALUES (?, ?, ?, ?, ?, ?)""",
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
                self.conn.execute('UPDATE PaperSelection SET AbsProcess=(?) WHERE ID=(?)', ('Exist', abs_item[0]))
            else:
                self.conn.execute('UPDATE PaperSelection SET AbsProcess=(?) WHERE ID=(?)', ('NoExist', abs_item[0]))
        self.conn.commit()
        print(f'Abstracts\' Process have been Done: {time.time()-start:.3f}s')

    def content_process(self, url_list=None, index=None):

        start = time.time()

        if url_list is None and index is None:
            cursor_u = self.conn.cursor()
            url_list = cursor_u.execute('SELECT ID, URL FROM PaperSelection WHERE ConProcess IS NULL')
        else:
            print(f'content processing {index} begin, need to process {len(url_list)} items.')

        cursor_t = self.conn.cursor()
        cursor_t.execute('''CREATE TABLE IF NOT EXISTS ContentProcess
                                            (ID TEXT PRIMARY KEY,
                                            HTML TEXT)''')

        cursor_t.execute('SELECT TableTag FROM Tags')
        key_name = [i[0] for i in cursor_t.fetchall() if i[0] is not None]

        for u_ in url_list:
            content_vanity = ContentReader.arxiv_vanity_reader(u_[-1])

            if content_vanity is None:
                try:
                    content_raw = ContentReader.raw_data_reader(u_[-1])

                    if content_raw is not None:
                        _, html_list = ContentProcess.get_informative_table(content_raw, key_name, raw_data=True)
                    else:
                        html_list = []
                except:
                    self.conn.execute('UPDATE PaperSelection SET ConProcess=(?) WHERE ID=(?)', ('NoExist', u_[0]))
                    continue
            else:
                _, html_list = ContentProcess.get_informative_table(content_vanity, key_name)

            if len(html_list) > 2:
                html_page = "\n".join(html_list)
                try:
                    self.conn.execute('INSERT INTO ContentProcess VALUES (?, ?)', (u_[0], html_page))
                except:
                    self.conn.execute('UPDATE ContentProcess SET HTML=(?) WHERE ID =(?)', (html_page, u_[0]))
                self.conn.execute('UPDATE PaperSelection SET ConProcess=(?) WHERE ID=(?)', ('Exist', u_[0]))
            else:
                self.conn.execute('UPDATE PaperSelection SET ConProcess=(?) WHERE ID=(?)', ('NoExist', u_[0]))
            self.conn.commit()

        if index is not None:
            print(f'Contents\' Processing {index} have been Done: {time.time()-start:.3f}s')
        else:
            print(f'Contents\' Process have been Done: {time.time()-start:.3f}s')

    def content_split(self, processing_num):
        cursor_u = self.conn.cursor()
        cursor_u.execute('SELECT URL FROM PaperSelection WHERE ConProcess IS NULL')
        url_list = [i[0] for i in cursor_u.fetchall() if i[0] is not None]
        if len(url_list) > 10:
            item_num = len(url_list) // processing_num
            final_list = []

            for p_num in range(processing_num-1):
                final_list.append(url_list[p_num*item_num: (p_num+1)*item_num])
            final_list.append(url_list[(processing_num-1)*item_num:])
            return final_list
        else:
            return url_list


# def start(index, analyzer, url_list=None):
#     if index == 0:
#         analyzer.title_process()
#     elif index == 1:
#         analyzer.abs_process()
#     elif index > 1:
#         analyzer.content_process(url_list, index)
#     return None


def main():
    try:
        sota = SotaSelection('https://arxiv.org/list/cs/pastweek?skip=0&show=50')
        results = sota.paper_selection()
        if results is not None:
            sota.push_database(results)
    except:
        pass

    analyzer = Analyses()
    url_list = analyzer.content_split(4)

    process_pool = Pool(2+len(url_list))

    for i in range(2+len(url_list)):
        if i == 1:
            process_pool.apply_async(func=analyzer.title_process, args=())
        elif i == 2:
            process_pool.apply_async(func=analyzer.abs_process, args=())
        else:
            process_pool.apply_async(func=analyzer.content_process, args=(url_list[i-2], i-2))

    process_pool.close()
    process_pool.join()
    process_pool.terminate()


if __name__ == "__main__":
    main()
    # analyzer = Analyses()
    # analyzer.content_process()