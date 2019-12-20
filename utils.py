import re
import sys
# import json
import time
import numpy as np
import sqlite3
import urllib.request
from bs4 import BeautifulSoup
from selenium import webdriver


class Distance(object):
    def __init__(self):
        pass

    @staticmethod
    def levenshtein_distance(string_one, string_two):
        if len(string_one) < len(string_two): return Distance.levenshtein_distance(string_two, string_one)
        # TO DO: a method to normalizing score that take no effects of ranking
        if len(string_two) == 0: return len(string_one)

        previous_row = range(len(string_two) + 1)
        for index_1, chr_1 in enumerate(string_one):
            # current_raw[o] equals to chr num in string two
            current_row = [index_1 + 1]

            for index_2, chr_2 in enumerate(string_two):
                insertions = previous_row[index_2 + 1] + 1
                deletions = current_row[index_2] + 1

                # 1 for true, 0 for false
                substitutions = previous_row[index_2] + (chr_1 != chr_2)
                current_row.append(min(insertions, deletions, substitutions))

            # after loop, the length of current_raw must equals to len(s2)+1
            previous_row = current_row
        return previous_row[-1]

    @staticmethod
    def string_distance(string, key_list, value_list):
        key_position = sorted(list(set([np.mean(i.span()) for key in key_list
                                        for i in re.finditer(key, string)])))
        value_position = sorted(list(set([np.mean(i.span()) for value in value_list
                                          for i in re.finditer(value, string)])))

        if len(key_list) >= len(value_list):
            index = [np.argmin(np.abs([i - j for j in key_position])) for i in value_position]
            return [key_list[i] for i in index], value_list
        else:
            index = [np.argmin(np.abs([i - j for j in value_position])) for i in key_position]
            return key_list, [value_list[i] for i in index]


class AbsUtils(object):
    def __init__(self):
        pass

    @staticmethod
    def abs_filter(total_abs, evidence=False, strict_mode=False):
        conn = sqlite3.connect('./test.db')
        cursor_s = conn.cursor()
        cursor_s.execute('SELECT TableTag FROM Tags')
        sota_name = [i[0] for i in cursor_s.fetchall() if i[0] is not None]
        conn.close()

        if strict_mode: sota_name = []

        sota_name.extend(['sota', 'state(\s|-)of(\s|-)the(\s|-)art'])

        filter_pattern = re.compile(r'\s(%s)\s' % ('|'.join(sota_name)), re.I)
        filtered_abs = []
        filtered_lines = []

        # whether we should output evidence lines that filtering abstract
        if evidence:
            for url_, abs_ in total_abs.items():
                lines = re.split(r'\.\s', abs_)
                evidence_line = [line for line in lines if filter_pattern.search(line) is not None]
                if len(evidence_line) > 0:
                    filtered_abs.append((url_, abs_))
                    filtered_lines.append(evidence_line)
            assert len(filtered_abs) == len(filtered_lines)

            return filtered_abs, filtered_lines, sota_name
        else:
            filtered_abs = [(url_, abs_) for url_, abs_ in total_abs.items() if filter_pattern.search(abs_) is not None]
            return filtered_abs, sota_name


class ContentReader(object):

    @staticmethod
    def arxiv_vanity_reader(url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) '
                                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                                     'Chrome/78.0.3904.70 Safari/537.36'}

            pattern = re.compile(r'\d+\.[\dv]+')
            if url.find('arxiv') > -1:
                key_phrase = pattern.search(url)
                key_phrase = key_phrase.group()
                if key_phrase is not None:
                    u = 'https://www.arxiv-vanity.com/papers/' + key_phrase
                    print(u)
                    request_ = urllib.request.Request(url=u, headers=headers)
                    r = urllib.request.urlopen(request_, timeout=60).read()
                    content = BeautifulSoup(r, features='html.parser')
                    return content
        except:
            pattern = re.compile(r'\d+\.[\dv]+')
            if url.find('arxiv') > -1:
                key_phrase = pattern.search(url)
                key_phrase = key_phrase.group()
                if key_phrase is not None:
                    u = 'https://www.arxiv-vanity.com/papers/' + key_phrase
                    driver = webdriver.Chrome()
                    driver.get(u)
                    time.sleep(7)
                    content = driver.find_element_by_xpath("//*").get_attribute("outerHTML")
                    content = BeautifulSoup(content, features='html.parser')
                    driver.close()

                    if len(content) > 1 or \
                        content.find('body').get_text().find('doesn\'t have LaTeX source code') > -1:
                        return content
                    else:
                        return None

    @staticmethod
    def reporthook(block_num, block_size, total_size):
        readsofar = block_num * block_size
        if total_size > 0:
            percent = readsofar * 1e2 / total_size
            s = "\r%5.1f%% %*d / %d" % (
                percent, len(str(total_size)), readsofar, total_size)
            sys.stderr.write(s)
            # near the end
            if readsofar >= total_size:
                sys.stderr.write("\n")
        # total size is unknown
        else:
            sys.stderr.write("read %d\n" % (readsofar,))

    @staticmethod
    def raw_data_reader(url):
        import tarfile
        import os
        import urllib.request

        base_url = "https://arxiv.org/e-print/"
        pattern = re.compile(r'\d+\.[\dv]+')
        if url.find('arxiv') > -1:
            key_phrase = pattern.search(url)
            key_phrase = key_phrase.group()
            if key_phrase is not None:
                u = base_url + key_phrase

                urllib.request.urlretrieve(u, './data/papers.tar.gz', reporthook=ContentReader.reporthook)
                tar = tarfile.open('./data/papers.tar.gz', 'r')
                # try:
                #     tar = tarfile.open('./data/papers/%s.tar.gz' % key_phrase, 'r')
                # except:
                #     return None
                data = {}
                for name in tar.getnames():
                    if re.search(r'\.tex', name, re.I) is not None:
                        tmp_data = tar.extractfile(name).read().decode('utf-8', "ignore").replace('\n', '@$@$@')
                        if re.search(r'{table}.+?{table}', tmp_data, re.I) is not None:
                            try:
                                with open('./tmp.tex', 'w', encoding="utf-8") as f:
                                    f.write(tmp_data.replace('@$@$@', '\n'))
                                os.system('latexml --dest=./tmp.xml ./tmp.tex')
                                os.system('latexmlpost --dest=./tmp.html --nopictureimages --nographicimages --novalidate tmp.xml')
                                with open('./tmp.html', 'r', encoding="utf-8") as f:
                                    r = f.read()
                                data[name] = BeautifulSoup(r, features='html.parser')
                            except:
                                continue
                # os.remove('./tmp.html')
                # os.remove("./tmp.tex")
                # os.remove("./tmp.xml")
                if len(data) > 0:
                    return data
                else:
                    return None


class ContentProcess(object):
    @staticmethod
    def regular_table_check(table):
        # check if every row kept same num of elements
        coloumn_num = [len(i.find_all(class_='ltx_td')) for i in table.find_all(class_='ltx_tr')]
        coloumn_num = len(set(coloumn_num))
        if coloumn_num == 1:
            return True
        else:
            return False

    @staticmethod
    def construct_column_tree(table):
        column_tree = {}
        first_column = [row.find(class_='ltx_td').get_text().replace('\n', ' ')
                        for row_index, row in enumerate(table.find_all('tr'))
                        if row_index > 0]
        for i in first_column:
            if re.search(r'^\s+', i) is not None:
                column_tree[i.strip()] = len(re.search(r'^\s+', i).group())
            else:
                column_tree[i.strip()] = 0

        span_num = column_tree.values()
        if len(set(span_num)) == 1:
            for key, value in column_tree.items():
                column_tree[key] = 0
        else:
            num_index = sorted(list(set(span_num)))
            for key, value in column_tree.items():
                column_tree[key] = num_index.index(value)
        return column_tree

    @staticmethod
    def get_informative_table(content, key_name, raw_data=False):

        if raw_data:
            table_list = []
            for key, value in content.items():
                table_list.extend(value.find_all("figure", attrs={'class': 'ltx_table'}))
        else:
            table_list = content.find_all("figure", attrs={'class': 'ltx_table'})
        table_content = {}
        plus_pattern = re.compile(r'(\s+|^)(\+|-)(.+)')

        with open('./data/test.html', 'r', encoding='utf-8') as f:
            html_file = f.read().split('<!---split-position--->')
        table_html = []
        table_html.append(html_file[0])

        for table in table_list:
            try:
                table_array = []
                bold_array = []
                captions = table.find_all('figcaption')[-1].get_text().strip().replace('\n', ' ')

                if re.search(r'\s(%s)(\s|,|\.|\()' % '|'.join(key_name), captions, re.I) is not None and \
                                re.search(r'\s(ablation)(\s|\,|\.\()', captions, re.I) is None:
                    table_html.append(str(table))

                    table = table.find('table')
                    if table is None: continue
                    if ContentProcess.regular_table_check(table):
                        column_tree = ContentProcess.construct_column_tree(table)
                        for row_index, row in enumerate(table.find_all('tr')):
                            table_array.append([element.get_text().strip().replace('\n', ' ')
                                                for element in row.find_all(class_='ltx_td')])

                            # process different rank of first column
                            if plus_pattern.search(table_array[-1][0]) is not None:
                                rank = column_tree.get(table_array[-1][0])
                                for index in range(len(table_array) - 2, -1, -1):
                                    if column_tree.get(table_array[index][0], 5) < rank:
                                        table_array[-1][0] = table_array[index][0] + table_array[-1][0]
                                        column_tree[table_array[-1][0]] = rank
                                        break

                            for column_index, element in enumerate(row.find_all(class_='ltx_td')):
                                if element.find(class_="ltx_font_bold") is not None \
                                        and row_index > 0 \
                                        and column_index > 0:
                                    item_one = "Best-%s: %s" % (table_array[0][0], table_array[row_index][0])
                                    item_two = "Best-%s: %s" % (
                                    table_array[0][column_index], table_array[row_index][column_index])
                                    bold_array.append([item_one, item_two])
                        if len(bold_array) > 0:
                            table_content[captions] = bold_array
            except BaseException as e:
                print(e)
                continue
        table_html.append(html_file[-1])
        return table_content, table_html