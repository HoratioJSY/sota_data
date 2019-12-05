import os
import re
import sys
import json
import time
import pandas as pd
from bs4 import BeautifulSoup
from urllib import request
from tqdm import tqdm
from selenium import webdriver


class ArxivReader(object):
    """
    methods for reading paper content, including:
     - XML reader by arxiv vanity
     - LaTex source code reader
    """

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
                    request_ = request.Request(url=u, headers=headers)
                    r = request.urlopen(request_, timeout=60).read()
                    content = BeautifulSoup(r, features='html.parser')
                    return content
        except:
            pass
            # pattern = re.compile(r'\d+\.[\dv]+')
            # if url.find('arxiv') > -1:
            #     key_phrase = pattern.search(url)
            #     key_phrase = key_phrase.group()
            #     if key_phrase is not None:
            #         u = 'https://www.arxiv-vanity.com/papers/' + key_phrase
            #         driver = webdriver.Chrome()
            #         driver.get(u)
            #         time.sleep(10)
            #         content = driver.find_element_by_xpath("//*").get_attribute("outerHTML")
            #         content = BeautifulSoup(content, features='html.parser')
            #         driver.close()
            #         return content
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
        import urllib.request

        base_url = "https://arxiv.org/e-print/"
        pattern = re.compile(r'\d+\.[\dv]+')
        if url.find('arxiv') > -1:
            key_phrase = pattern.search(url)
            key_phrase = key_phrase.group()
            if key_phrase is not None:
                u = base_url + key_phrase

                # urllib.request.urlretrieve(u, './data/papers.tar.gz', reporthook=ArxivReader.reporthook)
                tar = tarfile.open('./data/papers.tar.gz', 'r')
                # print(tar.getnames())
                data = {}
                for name in tar.getnames():
                    if re.search(r'\.tex', name, re.I) is not None:
                        tmp_data = tar.extractfile(name).read().decode('utf-8').replace('\n', '@$@$@')
                        if re.search(r'{table}.+?{table}', tmp_data, re.I) is not None:
                            try:
                                with open('./tmp.tex', 'w', encoding="utf-8") as f:
                                    f.write(tmp_data.replace('@$@$@', '\n'))
                                print(name)
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


def regular_table_check(table):
    # check if every row kept same num of elements
    coloumn_num = [len(i.find_all(class_='ltx_td')) for i in table.find_all(class_='ltx_tr')]
    coloumn_num = len(set(coloumn_num))
    if coloumn_num == 1:
        return True
    else:
        return False


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


def get_informative_table(content, key_name, raw_data=False):

    if raw_data:
        table_list = []
        for key, value in content.items():
            table_list.extend(value.find_all("figure", attrs={'class':'ltx_table'}))
    else:
        table_list = content.find_all("figure", attrs={'class':'ltx_table'})
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
            if re.search(r'\s(%s)(\s|\,|\.|\()' % '|'.join(key_name), captions, re.I) is not None and\
                re.search(r'\s(ablation)(\s|\,|\.\()', captions, re.I) is None:
                table_html.append(str(table))

                table = table.find('table')
                if regular_table_check(table):
                    column_tree = construct_column_tree(table)
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
                                item_two = "Best-%s: %s" % (table_array[0][column_index], table_array[row_index][column_index])
                                bold_array.append([item_one, item_two])
                    if len(bold_array) > 0:
                        table_content[captions] = bold_array
        except BaseException as e:
            print(e)
            continue
    table_html.append(html_file[-1])
    return table_content, table_html


def get_paper_txt():
    df = pd.read_csv('./data/Sota_Evaluations.csv')
    df = df.dropna(axis=0)
    url = ['https://arxiv.org/abs/1906.02448']
    # url = ['https://arxiv.org/abs/1508.05326v1']
    url.extend(df['paperurl'])

    results = {}
    for index, u in enumerate(tqdm(url[0:1])):
        content_vanity = ArxivReader.arxiv_vanity_reader(u)
        with open("./data/table_key_tag.json", 'r') as f:
            key_name = json.load(f)

        if content_vanity is None:
            content_raw = ArxivReader.raw_data_reader(u)
            if content_raw is None: continue
            informative_table, html_list = get_informative_table(content_raw, key_name, raw_data=True)
        else:
            informative_table, html_list = get_informative_table(content_vanity, key_name)

        if len(informative_table) > 0:
            with open("./data/html/%d.html" % index, 'w', encoding='utf-8') as f:
                f.write("\n".join(html_list))
            results[u] = ["informative table: %d.html"%index]
            results[u].append(informative_table)
        elif len(html_list) > 2:
            with open("./data/html/%d.html" % index, 'w', encoding='utf-8') as f:
                f.write("\n".join(html_list))
            results[u] = ["informative table: %d.html"%index]
        else:
            results[u] = 'no informative table'
    with open("./data/sample.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    get_paper_txt()