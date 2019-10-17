import pandas as pd
import numpy as np
import re
from bs4 import BeautifulSoup
from urllib import request

# df = pd.read_csv('Sota_Evaluations.csv')
# url = df['paperurl']
# u = np.array(url)


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

        pdf_urls = self.content.find_all("a", attrs={'title': 'Download PDF'})
        self.pdf_urls = ['https://arxiv.org' + url["href"].strip() + '.pdf' for url in pdf_urls]

        return self.abs_urls, self.pdf_urls

    def get_abstract(self):
        if self.abs_urls is None: _, _ = self.get_hyperlink()
        for url in self.abs_urls:
            content = self.__get_pages(url)
            abs_ = content.find('blockquote', attrs={'abstract'}).get_text().strip()[11:]
            self.abs_list.append(re.sub(r'\n', ' ', abs_))

        return self.abs_list


link = PaperData('https://arxiv.org/list/cs.AI/recent')
# print(link.get_title())
print(link.get_abstract())


class Analyces(PaperData):
    def __init__(self, web_url):
        super(Analyces, self).__init__(web_url)

    def title_process(self):
        pass

    def abs_process(self):
        pass