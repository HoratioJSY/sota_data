import re
import sys
import json
import pandas as pd
from bs4 import BeautifulSoup
from urllib import request
from tqdm import tqdm


class ArxivReader(object):
    """
    methods for reading paper content, including:
     - pdf reader by open source lib
     - XML reader by arxiv vanity
     - LaTex source code reader
    """
    @staticmethod
    def py2pdf_reader():
        from PyPDF2 import PdfFileReader

        reader = PdfFileReader('./data/attention.pdf')

        page_text = [reader.getPage(i).extractText().strip() for i in range(reader.getNumPages())]

        with open('./data/pdf_txt.txt', 'w', encoding='utf-8') as f:
            f.write(' '.join(page_text))

    @staticmethod
    def pdfminer_reader():
        from pdfminer.converter import TextConverter
        from pdfminer.pdfpage import PDFPage
        from pdfminer.layout import LAParams
        from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter

        laparams = LAParams()

        output = open('./data/pdfminer_txt.txt', 'w', encoding='utf-8')
        rsrcmgr = PDFResourceManager(caching=True)
        device = TextConverter(rsrcmgr, output, laparams=laparams)

        with open('./data/attention.pdf', 'rb') as f:
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page in PDFPage.get_pages(f, caching=True, check_extractable=True):
                interpreter.process_page(page)
        device.close()
        output.close()

    @staticmethod
    def tabular_reader(url):
        import tabula
        df = tabula.read_pdf(url, pages='all', guess=True,
                             pandas_options={'header': None}, multiple_tables=True)
        return df

    @staticmethod
    def arxiv_vanity_reader(url):
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/78.0.3904.70 Safari/537.36'}

        pattern = re.compile(r'\d+\.[\dv]+')
        if url.find('arxiv') > -1:
            try:
                key_phrase = pattern.search(url)
                key_phrase = key_phrase.group()
                if key_phrase is not None:
                    u = 'https://www.arxiv-vanity.com/papers/' + key_phrase
                    print(u)
                    request_ = request.Request(url=u, headers=headers)
                    r = request.urlopen(request_, timeout=60).read()
                    content = BeautifulSoup(r, features='html.parser')
                    return content
            except BaseException as e:
                print(e)
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

        # headers = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) ' \
        #           'AppleWebKit/537.36 (KHTML, like Gecko) ' \
        #           'Chrome/78.0.3904.70 Safari/537.36'
        # subprocess.run(['wget', '-U', headers,'-O', './data/papers.zip', 'https://arxiv.org/e-print/1910.10685v2'])

        base_url = "https://arxiv.org/e-print/"
        pattern = re.compile(r'\d+\.[\dv]+')
        if url.find('arxiv') > -1:
            try:
                key_phrase = pattern.search(url)
                key_phrase = key_phrase.group()
                if key_phrase is not None:
                    u = base_url + key_phrase

                    urllib.request.urlretrieve(u, './data/papers.tar.gz', reporthook=ArxivReader.reporthook)
                    tar = tarfile.open('./data/papers.tar.gz', 'r')
                    # print(tar.getnames())
                    data = {}
                    for name in tar.getnames():
                        if re.search(r'\.tex', name, re.I) is not None:
                            data[name] = tar.extractfile(name).read().decode('utf-8')
                    return data
            except BaseException as e:
                print(e)
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


def get_informative_table(content_xml, key_name):
    table_list = content_xml.find_all("figure", attrs={'class':'ltx_table'})
    table_content = {}
    plus_pattern = re.compile(r'(\s+|^)(\+|-)(.+)')
    for table in table_list:
        try:
            table_array = []
            bold_array = []
            captions = table.find_all('figcaption')[-1].get_text().strip().replace('\n', ' ')

            if re.search(r'\s(%s)(\s|\,|\.\()' % '|'.join(key_name), captions, re.I) is not None and\
                re.search(r'\s(ablation)(\s|\,|\.\()', captions, re.I) is None:
                table = table.find('table')
                if regular_table_check(table):
                    column_tree = construct_column_tree(table)
                    for row_index, row in enumerate(table.find_all('tr')):
                        table_array.append([element.get_text().strip().replace('\n', ' ')
                                            for element in row.find_all(class_='ltx_td')])

                        # process different rank of first column
                        if plus_pattern.search(table_array[-1][0]) is not None:
                            rank = column_tree.get(table_array[-1][0])
                            for index in range(len(table_array)-2, -1, -1):
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
                                # bold_array.append(["Best-" + ": ".join(i) for i in zip(table_array[0], table_array[row_index])])
                                # break
                    table_content[captions] = [table_array, bold_array]

        except BaseException as e:
            print(e)
            continue
    return table_content


def raw_content_process(content_raw):
    table_pattern = re.compile(r'\\begin{table}.+\\end{table}')
    for key, value in content_raw.items():
        table_num = len(table_pattern.findall(value))
        print(table_num)
    pass


def get_paper_txt():
    df = pd.read_csv('./data/Sota_Evaluations.csv')
    df = df.dropna(axis=0)
    url = ['https://arxiv.org/abs/1906.02448']
    url.extend(df['paperurl'])

    results = {}
    for u in url[0:5]:
        content_xml = ArxivReader.arxiv_vanity_reader(u)
        if content_xml is None:
            continue
            # content_raw = ArxivReader.raw_data_reader(u)
            # raw_content_process(content_raw)
            # merged_table = content_raw
        else:
            with open("./data/table_key_tag.json", 'r') as f:
                key_name = json.load(f)
            informative_table = get_informative_table(content_xml, key_name)

            merged_table = {}
            for one_caption, one_table in informative_table.items():
                merged_ = []
                for row in one_table[0][1:]:
                    merged_.append([": ".join(i) for i in zip(one_table[0][0], row)])
                if len(one_table[-1]) > 0:
                    merged_.extend(one_table[-1])
                merged_table[one_caption] = merged_

        if len(merged_table) > 0:
            results[u] = merged_table
        else:
            results[u] = 'no informative table'
    with open("./data/sample.json", 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    get_paper_txt()