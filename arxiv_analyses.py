import re
import pickle
import json
import nltk
from bs4 import BeautifulSoup
from urllib import request

title_pattern = re.compile(r'\s(for|with)\s', re.I)


class PaperData:
    def __init__(self, web_url=None):
        self.web_url = web_url
        self.abs_list = []
        self.title_list = None
        self.abs_urls = None
        self.pdf_urls = None
        if web_url is not None:
            self.content = self.__get_pages(web_url).dl

    def __get_pages(self, web_url):
        r = request.urlopen(web_url).read()
        content = BeautifulSoup(r, features='html.parser')
        return content

    def get_title(self):
        title_list = self.content.find_all("div", attrs={'class': 'list-title'})
        self.title_list = [title.get_text().strip()[7:] for title in title_list]
        return self.title_list

    def get_hyperlink(self):
        abs_urls = self.content.find_all("a", attrs={'title': 'Abstract'})
        self.abs_urls = ['https://arxiv.org' + url['href'].strip() for url in abs_urls]
        self.abs_urls.append('https://arxiv.org/abs/1902.01069')

        pdf_urls = self.content.find_all("a", attrs={'title': 'Download PDF'})
        self.pdf_urls = ['https://arxiv.org' + url["href"].strip() + '.pdf' for url in pdf_urls]

        return self.abs_urls, self.pdf_urls

    def get_abstract(self):
        if self.abs_urls is None: _, _ = self.get_hyperlink()
        try:
            with open('./data/saved_abs.p', 'rb') as f:
                self.abs_list = pickle.load(f)
        except:
            for url in self.abs_urls:
                content = self.__get_pages(url)
                abs_ = content.find('blockquote', attrs={'abstract'}).get_text().strip()[11:]
                self.abs_list.append(re.sub(r'\n', ' ', abs_))
            with open('./data/saved_abs.p', 'wb') as f:
                pickle.dump(self.abs_list, f)

        return self.abs_list


class Analyses(PaperData):
    def __init__(self, web_url=None):
        super(Analyses, self).__init__(web_url)

    def easy_title_process(self):
        if self.title_list is None: _ = self.get_title()
        results = {}
        split_patern = re.compile(r'\s(using|a|an|the|)\s|\:|a\s', re.I)
        for title in self.title_list:
            title_r = []
            try:
                tokens = nltk.word_tokenize(title)
            except:
                print(title)
                print(type(title))
                quit()
            tag = nltk.pos_tag(tokens)
            _, pos_list = zip(*tag)
            prep_index = [i for i, pos in enumerate(pos_list) if pos == 'IN']
            conj_index = [i for i, pos in enumerate(pos_list) if pos == 'CC']
            if len(prep_index) < 2 and len(conj_index) == 0:
                if 'for' in tokens:
                    title_split = title.split(' for ')
                    method = split_patern.split(title_split[0])[-1]
                    task = split_patern.split(title_split[1])[0]
                    title_r.extend(['method: ' + method, 'task: ' + task])
                elif 'with' in tokens:
                    title_split = title.split(' with ')
                    task = split_patern.split(title_split[0])[-1]
                    method = split_patern.split(title_split[1])[0]
                    title_r.extend(['method: ' + method, 'task: ' + task])
                if len(title_r) > 0:
                    results[title] = title_r
        return results

    def __levenshtein_distance(self, string_one, string_two):
        if len(string_one) < len(string_two): return self.__levenshtein_distance(string_two, string_one)

        # TO DO: normalizing the score of edit distance that take no effects of ranking
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

    def title_process_ed(self):
        pass

    def abs_process(self):
        if len(self.abs_list) < 1: _ = self.get_abstract()
        if self.title_list is None: _ = self.get_title()
        num_pattern = re.compile(r'%|\d+%|\d+\.\d+')
        key_pattern = re.compile(r"accuracy|score|precision|recall", re.I)
        results = {}
        print(self.abs_list[-1])
        for index, abs in enumerate(self.abs_list):
            lines = re.split(r'\.|,', abs)
            informative_line = [line for line in lines if len(num_pattern.findall(line)) > 0]
            if len(informative_line) > 0:
                results['informative_%s' % index] = informative_line

            key_line = [line for line in informative_line if key_pattern.search(line) is not None]
            key_list = [key_pattern.findall(line) for line in key_line]
            num_list = [num_pattern.findall(line) for line in key_line]

            assert len(key_list) == len(num_list)
            if len(key_list) > 0:
                result = list(zip(key_list, num_list))
                results['total_results_%s'%index] = result

        return results

    def pdf_process(self):
        pass


if __name__ == '__main__':
    link = Analyses('https://arxiv.org/list/cs.AI/recent')
    # print(link.easy_title_process())
    # print(link.title_process())
    # print(link.abs_process())

    with open('./data/sample.json', 'w', encoding='utf-8') as f:
        json.dump((link.easy_title_process(), link.title_process()), f, indent=4)
