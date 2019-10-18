import re
import pickle
import json
import nltk
from bs4 import BeautifulSoup
from urllib import request

# df = pd.read_csv('Sota_Evaluations.csv')
# url = df['paperurl']
# u = np.array(url)
# _, pos_list = zip(*tag)
# prep_index = [i for i, pos in enumerate(pos_list) if pos=='IN']

title_pattern = re.compile(r'\s(for|with)\s', re.I)


class PaperData:
    def __init__(self, web_url):
        self.web_url = web_url
        self.content = self.__get_pages(web_url).dl
        self.abs_list = []
        self.title_list = None
        self.abs_urls = None
        self.pdf_urls = None

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
            with open('./saved_abs.p', 'rb') as f:
                self.abs_list = pickle.load(f)
        except:
            for url in self.abs_urls:
                content = self.__get_pages(url)
                abs_ = content.find('blockquote', attrs={'abstract'}).get_text().strip()[11:]
                self.abs_list.append(re.sub(r'\n', ' ', abs_))
            with open('./saved_abs.p', 'wb') as f:
                pickle.dump(self.abs_list, f)

        return self.abs_list


class Analyses(PaperData):
    def __init__(self, web_url):
        super(Analyses, self).__init__(web_url)

    def easy_title_process(self):
        if self.title_list is None: _ = self.get_title()
        results = {}
        split_patern = re.compile(r'\s(to|of|using|on|in|and|a|an|the)\s')
        for title in self.title_list:
            title_r = []
            tokens = nltk.word_tokenize(title)
            if 'for' in tokens:
                title_split = title.split(' for ')
                method = split_patern.split(title_split[0])[-1]
                task = split_patern.split(title_split[1])[0]
                title_r.append((method, task))
            elif 'with' in tokens:
                title_split = title.split(' with ')
                task = split_patern.split(title_split[0])[-1]
                method = split_patern.split(title_split[1])[0]
                title_r.append((method, task))
            if len(title_r) > 0:
                results[title] = title_r
        return results

    # test,using pos for extraction
    def title_process(self):
        if self.title_list is None: _ = self.get_title()
        results = {}
        for title in self.title_list:
            title_results = []
            if title_pattern.findall(title) is not None:
                key_list = title_pattern.findall(title)
                tokens = nltk.word_tokenize(title)
                key_index = [index for index, value in enumerate(tokens) if value in key_list]
                tag = nltk.pos_tag(tokens)
                # print(tag)

                for index in key_index:
                    pre_words = []
                    post_words = []
                    for i in range(index-1, -1, -1):
                        if tag[i][1] in ['NNP', 'JJ', 'VBD']:
                            pre_words.append(tokens[i])
                        else:
                            break
                    for j in range(index+1, len(tokens)):
                        if tag[j][1] in ['NNP', 'JJ', 'VBD']:
                            post_words.append(tokens[j])
                        else:
                            break

                    if len(pre_words) > 0 and len(post_words) > 0:
                        pre_words.reverse()
                        title_results.append((' '.join(pre_words), ' '.join(post_words)))
            if len(title_results) > 0:
                results[title] = title_results
        return results

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
    # print(link.title_process())
    # print(link.abs_process())

    with open('./sample.json', 'w', encoding='utf-8') as f:
        json.dump((link.easy_title_process(), link.title_process()), f, indent=4)
