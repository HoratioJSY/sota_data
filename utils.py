import re
import sys
import json
import numpy as np
import urllib.request
from bs4 import BeautifulSoup


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
    def abs_filter(total_abs, evidence=False):

        try:
            with open("./data/metric_tag.json", 'r') as f:
                metric_name = json.load(f)
        except BaseException as e:
            print('failed to load metric tags\n', e)
            quit()

        # token_list = ' '.join(metric_name).lower().translate(str.maketrans("（）()", "    ")).split()
        metric_name.extend(['sota', 'state(\s|-)of(\s|-)the(\s|-)art', 'benchmark', 'experiment', 'experimental'])

        filter_pattern = re.compile(r'\s(%s)\s' % ('|'.join(metric_name)), re.I)
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

            return filtered_abs, filtered_lines, metric_name
        else:
            filtered_abs = [(url_, abs_) for url_, abs_ in total_abs.items() if filter_pattern.search(abs_) is not None]
            return filtered_abs, metric_name


class ContentReader(object):

    @staticmethod
    def arxiv_vanity_reader(url):
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/78.0.3904.70 Safari/537.36'}

        pattern = re.compile(r'\d+\.[\dv]+')
        if url.find('arxiv') > -1:
            err_num = 1
            while True:
                try:
                    key_phrase = pattern.search(url)
                    key_phrase = key_phrase.group()
                    if key_phrase is not None:
                        u = 'https://www.arxiv-vanity.com/papers/' + key_phrase
                        print(u)
                        request_ = urllib.request.Request(url=u, headers=headers)
                        r = urllib.request.urlopen(request_, timeout=120).read()
                        content = BeautifulSoup(r, features='html.parser')
                        return content
                except BaseException as e:
                    print(e)
                    if err_num < 5:
                        err_num += 1
                        continue
                    else:
                        break
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

        base_url = "https://arxiv.org/e-print/"
        pattern = re.compile(r'\d+\.[\dv]+')
        if url.find('arxiv') > -1:
            err_num = 1
            while True:
                try:
                    key_phrase = pattern.search(url)
                    key_phrase = key_phrase.group()
                    if key_phrase is not None:
                        u = base_url + key_phrase

                        urllib.request.urlretrieve(u, './data/papers.tar.gz', reporthook=ContentReader.reporthook)
                        tar = tarfile.open('./data/papers.tar.gz', 'r')
                        # print(tar.getnames())
                        data = {}
                        for name in tar.getnames():
                            if re.search(r'\.tex', name, re.I) is not None:
                                data[name] = tar.extractfile(name).read().decode('utf-8')
                        return data
                except BaseException as e:
                    print(e)
                    if err_num < 5:
                        err_num += 1
                        continue
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
    def get_informative_table(content_xml, key_name):
        table_list = content_xml.find_all("figure", attrs={'class': 'ltx_table'})
        table_content = {}
        for table in table_list:
            try:
                table_array = []
                bold_array = []
                captions = table.find_all('figcaption')[-1].get_text().strip().replace('\n', ' ')

                if re.search(r'\s(%s)(\s|\,|\.\()' % '|'.join(key_name), captions, re.I) is not None and \
                                re.search(r'\s(ablation)(\s|\,|\.\()', captions, re.I) is None:
                    table = table.find('table')
                    if ContentProcess.regular_table_check(table):
                        for row_index, row in enumerate(table.find_all('tr')):
                            # table_array.append([' '.join([span.get_text().strip().replace('\n', ' ')
                            #                               for span in element.find_all(attrs={"class":'ltx_text'})])
                            #                     for element in row.find_all(class_='ltx_td')])
                            table_array.append([element.get_text().strip().replace('\n', ' ')
                                                for element in row.find_all(class_='ltx_td')])
                            for column_index, element in enumerate(row.find_all(class_='ltx_td')):
                                if element.find(class_="ltx_font_bold") is not None \
                                        and row_index > 0 \
                                        and column_index > 0:
                                    item_one = "Best-%s: %s" % (table_array[0][0], table_array[row_index][0])
                                    item_two = "Best-%s: %s" % (
                                    table_array[0][column_index], table_array[row_index][column_index])
                                    bold_array.append([item_one, item_two])

                        table_content[captions] = [table_array, bold_array]

            except BaseException as e:
                print(e)
                continue
        return table_content