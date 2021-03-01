import numpy as np
import linecache
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.layout import LAParams
import io
from rake_nltk import Rake

def pdfparser(data):
    '''
    Converts .pdf to one long string
    '''
    fp = open(data, 'rb')
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    codec = 'text'
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, laparams=laparams)
    # Create a PDF interpreter object.
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    # Process each page contained in the document.

    for page in PDFPage.get_pages(fp):
        interpreter.process_page(page)
        data =  retstr.getvalue()

    return data

def findCompanyQuarter(my_list):
    '''
    Reads company name along with its abbreviation
    Input should be first 100 words of file as a list of strings
    Outputs as a string and financial quarter, e.g. 'Amgen, Inc, (AMGN)' 'Q1 2020'
    '''
    for i in range(len(my_list)):
        if len(my_list[i]) > 8:
            if my_list[i][-4:].isnumeric() and my_list[i][-5] == '-' and my_list[i][-8:-5].isalpha():
                date_ind = i
                break

    for i in range(date_ind, len(my_list)):
        if my_list[i] in ['Q1', 'Q2', 'Q3', 'Q4']:
            quarter_ind = i
            break

    return ' '.join(my_list[date_ind+1: quarter_ind]), ' '.join(my_list[quarter_ind:quarter_ind+2])


def removePunctuation(my_list, ref=',.?!:;\''):
    '''
    Given a list of strings, removes any punctuation found in the list regardless of its position
    Returns as list of strings
    '''
    ref = list(ref)

    my_list = list(' '.join(my_list))
    indices = [i for i in range(len(my_list)) if my_list[i] in ref]

    for i in range(len(indices)):
        del my_list[indices[-(i+1)]]


    return ''.join(my_list).split()

def removeHeaderFooter(qa_paras, company):
    '''
    Removes header/footer found between pages.
    Input should be list of paragraphs and company name, ref findCompany()
    Outputs as list of paragraphs
    '''
    len_footer = len(company.split()) + 16

    for i in range(len(qa_paras)):
        my_para = qa_paras[i].split()

        footer_end = 0
        for j in range(len(my_para)):
            if my_para[j] == 'FactSet':
                if my_para[j+1] == 'CallStreet,' and my_para[j+2] == 'LLC':
                    footer_end = j+2
                    break

        if footer_end > 0:
            if len(my_para) == footer_end+1:
                my_para = my_para[:footer_end-len_footer+1]
            else:
                my_para = my_para[:footer_end-len_footer+1] + my_para[footer_end+1:]
            qa_paras[i] = ' '.join(my_para)

    return qa_paras

def checkKeyword(my_list, keyword):
    '''
    Checks if a given keyword or pair of keywords is found in the list of strings.
    Returns either True or False
    '''
    def checkPlurals(my_str, keyword):
        if keyword == my_str:
            return True
        elif keyword+'s' == my_str:
            return True
        elif keyword+'es' == my_str:
            return True
        elif keyword[:-1]+'ies' == my_str:
            return True
        elif keyword+'\'s' == my_str:
            return True
        else:
            return False

    if len(keyword.split()) == 1:
        for i in range(len(my_list)):
            if checkPlurals(my_list[i], keyword):
                return True
        return False

    if len(keyword.split()) > 1:
        len_pair = len(keyword.split())

        my_dict = {}
        for i in range(len_pair):
            a = my_list[i:]+(len_pair-len(my_list[i:])%len_pair)*['padding']
            my_dict['l'+str(i+1)] = np.reshape(a, (int(len(a)/len_pair), len_pair))

        for i in range(len_pair):
            for j in range(len(my_dict['l'+str(i+1)])):
                if checkPlurals(' '.join(my_dict['l'+str(i+1)][j]), keyword):
                    return True
        return False


def searchPairs(my_list, search_pair):
    '''
    Searches list of words for pair of search words and returns the index
    at which the pair begins
    '''
    len_pair = len(search_pair.split())

    my_dict = {}
    for i in range(len_pair):
        a = my_list[i:]+(len_pair-len(my_list[i:])%len_pair)*['padding']
        my_dict['l'+str(i+1)] = np.reshape(a, (int(len(a)/len_pair), len_pair))

    indices = []
    for i in range(len_pair):
        for j in range(len(my_dict['l'+str(i+1)])):
            if ' '.join(my_dict['l'+str(i+1)][j]).lower() == search_pair.lower():
                indices += [int(len_pair*j+i)]

    return indices

def pullCleanManagementQA(words, company):
    '''
    Given directory of file and filename, reads .pdf and pulls management discussion section
    and Q&A section while removing header/footer
    Returns as list of paragraphs, first for management and then for qa 
    '''
    # isolates sections
    management_section = words[searchPairs(words, 'management discussion section')[0]:searchPairs(words, 'question and answer section')[0]]
    qa_section = words[searchPairs(words, 'question and answer section')[0]:]

    # separates sections into paragraphs
    management_paras = []
    start, stop = 0, -1
    for i in range(len(management_section)):
        if management_section[i][:5] == '.....':
            stop = i
            management_paras += [' '.join(management_section[start:stop])]
            start = stop + 1
    del management_paras[0]

    qa_paras = []
    start, stop = 0, -1
    for i in range(len(qa_section)):
        if qa_section[i][:5] == '.....':
            stop = i
            qa_paras += [' '.join(qa_section[start:stop])]
            start = stop + 1
    del qa_paras[0]

    # Removes header/footer from Q&A paragraphs
    management_paras = removeHeaderFooter(management_paras, company)
    qa_paras = removeHeaderFooter(qa_paras, company)

    return management_paras, qa_paras

#   +-----------+
#   |           |
#   |  Classes  |
#   |           |
#   +-----------+

class Transcript:
    def __init__(self, my_dir, filename):
        self.my_dir = my_dir
        self.filename = filename
        words = pdfparser(self.my_dir+self.filename).split()
        self.company, self.quarter = findCompanyQuarter(words[:50])
        self.management_paras, self.qa_paras = pullCleanManagementQA(words, self.company)
        del words

    def keywordsByQuestioner(self, keywords):
        '''
        Goes through Q&A and counts the number of questions that mention a given keyword
        Returns two dictionaries where the value in key:value pairs are the names of the question asker
        and in the second dictionary, the value is the number of people who have mentioned that keyword
        '''
        keyword_dict = {i:[] for i in keywords}

        for i in range(len(self.qa_paras)):
            my_para = removePunctuation([n.lower() for n in self.qa_paras[i].split()])

            # determine if question paragraph and pull name
            if 'q' not in my_para:
                continue
            else:
                for j in range(len(my_para)):
                    if my_para[j] == 'q':
                        name = 'q' if j==0 else ' '.join(self.qa_paras[i].split()[:j])
                        break

                # search through paragraph for keywords
                for j in range(len(keywords)):
                    if checkKeyword(my_para, keywords[j]):
                        keyword_dict[keywords[j]] += [name]

        # remove duplicate names
        keyword_count = {}
        for i in range(len(keywords)):
            keyword_dict[keywords[i]] = list(set(keyword_dict[keywords[i]]))
            if len(keyword_dict[keywords[i]]) > 0:
                keyword_count[keywords[i]] = len(keyword_dict[keywords[i]])
            else:
                del keyword_dict[keywords[i]]
        keyword_dict = sorted(keyword_dict.items(), key=lambda x: -len(x[1]))
        keyword_count = sorted(keyword_count.items(), key=lambda x: -x[1])

        return keyword_dict, keyword_count

    def keywordsByManagement(self, keywords):
        '''
        Counts number of times a keyword is mentioned in the management discussion section
        '''
        keyword_count = {i:0 for i in keywords}

        my_list = removePunctuation(' '.join(self.management_paras).lower().split())
        for i in range(len(keywords)):
            if len(keywords[i].split()) == 1:
                for j in range(len(my_list)):
                    if my_list[j].lower() == keywords[i]:
                        keyword_count[keywords[i]] += 1
            elif len(keywords[i].split()) > 1:
                len_pair = len(keywords[i].split())

                for j in range(len_pair):
                    temp_list = my_list[j:]+(len_pair-len(my_list[j:])%len_pair)*['p@dding']
                    temp_list = np.reshape(temp_list, (int(len(temp_list)/len_pair), len_pair))

                    for k in range(len(temp_list)):
                        if ' '.join(temp_list[k]).lower() == keywords[i]:
                            keyword_count[keywords[i]] += 1

        for i in range(len(keywords)):
            if keyword_count[keywords[i]] == 0:
                del keyword_count[keywords[i]]

        return sorted(keyword_count.items(), key=lambda x: -x[1])




