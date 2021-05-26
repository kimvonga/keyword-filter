import numpy as np
import linecache
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.layout import LAParams
import io
from rake_nltk import Rake
from nltk.corpus import words
import string
from IPython.display import display_html
from itertools import chain,cycle

my_exclusions = ['--', '–', 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'okay', 'et', 'cetera']
exclusion_list = words.words() + my_exclusions

def display_side_by_side(*args,titles=cycle([''])):
    '''
    Pulled from stackoverflow by @ntg
    Displays dataframes side by side and allows setting titles for each dataframe
    '''
    html_str=''
    for df,title in zip(args, chain(titles,cycle(['</br>'])) ):
        html_str+='<th style="text-align:center"><td style="vertical-align:top">'
        html_str+=f'<h2>{title}</h2>'
        html_str+=df.to_html().replace('table','table style="display:inline"')
        html_str+='</td></th>'
    display_html(html_str,raw=True)
    return None

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

    company = ' '.join(my_list[date_ind+1: quarter_ind])
    quarter = ' '.join(my_list[quarter_ind:quarter_ind+2]).split()
    quarter = quarter[1]+' '+quarter[0]

    return company, quarter

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

        footer_ends = []
        for j in range(len(my_para)):
            if my_para[j] == 'FactSet':
                if my_para[j+1] == 'CallStreet,' and my_para[j+2] == 'LLC':
                    footer_ends += [j+2]

        if len(footer_ends) > 0:
            for footer_end in footer_ends[::-1]:
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

def checkForms(word, ref_list):
    '''
    checks if word is present in ref_list but as another form.
    returns True if word is in ref_list and returns False otherwise
    '''
    # check for plural forms
    if word in ref_list:
        return True
    if word[-1] == 's':
        if word[:-1] in ref_list:
            return True
    if word[-2:] == 'es':
        if word[:-2] in ref_list:
            return True
    if word[-3:] == 'ies':
        if word[:-3]+'y' in ref_list:
            return True
    # check for past tense
    if word[-2:] == 'ed':
        if word[:-2] in ref_list or word[:-1] in ref_list:
            return True
    if word[-3:] == 'ned':
        if word[:-3] in ref_list:
            return True
    # check for present participle
    if word[-3:] == 'ing':
        if word[:-3]+'e' in ref_list or word[:-3]+'y' in ref_list or word[:-3] in ref_list:
            return True
    # check comparative forms
    if word[-2:] == 'er':
        if word[:-2] in ref_list or word[:-2]+'e' in ref_list:
            return True
    if word[-3:] == 'ier':
        if word[:-3]+'y' in ref_list:
            return True
    if word[-3:] == 'est':
        if word[:-3] in ref_list or word[:-3]+'e' in ref_list:
            return True
    if word[-4:] == 'iest':
        if word[:-4]+'y' in ref_list:
            return True

    return False

def combinePlurals(pairs):
    '''
    Goes through list of potential keywords and removes redundant plural forms
    Input and Output are list of pairs [('keyword', rank), ...]
    for finding new keywords from Rake
    '''
    words = list([i[0] for i in pairs])
    rank = list([i[1] for i in pairs])
    
    duplicate_indices = []
    for i in range(len(words)):
        my_word = words[i]
        if my_word[-1] == 's' or my_word[-2:] == 'es' or my_word[-3:] == 'ies':
            s_match = [j for j in range(len(words)) if words[j] == my_word[:-1]]
            es_match = [j for j in range(len(words)) if words[j] == my_word[:-2]]
            ies_match = [j for j in range(len(words)) if words[j] == my_word[:-3]+'y']
            if len(s_match) != 0:
                rank[s_match[0]] += rank[i]
                duplicate_indices += [i]
            elif len(es_match) != 0:
                rank[es_match[0]] += rank[i]
                duplicate_indices += [i]
            elif len(ies_match) != 0:
                rank[ies_match[0]] += rank[i]
                duplicate_indices += [i]

    if len(duplicate_indices) != 0:
        duplicate_indices = -np.sort(-np.array(duplicate_indices))
        for i in duplicate_indices:
            del words[i], rank[i]

    return [(words[i], rank[i]) for i in range(len(words))]

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
        self.company, self.quarter = findCompanyQuarter(words[:100])
        self.management_paras, self.qa_paras = pullCleanManagementQA(words, self.company)
        del words

    def keywordsByQuestionerManual(self, keywords):
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

    def keywordsByManagementManual(self, keywords):
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

    def keywordsByQuestionerRake(self):
        '''
        Goes through Q&A and finds keywords through Rake and outputs their rank according to Rake
        Returns two dictionaries where the value in the key:value pairs are the names of the question asker
        and in the second dictionary, the value is the number of people who mentioned that keyword
        '''
        return keyword_dict, keyword_count

    def keywordsByManagementRake(self):
        '''
        Finds keywords mentioned by management and outputs their rank according to Rake
        '''
        my_company = self.company

        r = Rake()
        r.extract_keywords_from_text(' '.join(self.management_paras))
        a = r.get_word_degrees()

        names = []
        for i in self.management_paras:
            my_words = removePunctuation(i.split()[:20], ref=string.punctuation)
            if my_words[0].lower() != 'operator':
                names += [my_words[0].lower(), my_words[1].lower()]
                for i in range(2, len(my_words)):
                    if my_words[i].lower() not in exclusion_list:
                        names += [my_words[i].lower()]
                    else:
                        break
        names = list(set(names))

        a = sorted(a.items(), key=lambda x: -x[1])

        # removes words with low degrees
#        for i in range(1,len(a)):
#            if a[-i][1] > 5:
#                my_ind = -i
#                break
#        a = a[:my_ind]

        indices = []
        for i in range(len(a)):
            if not checkForms(a[i][0], exclusion_list) and not a[i][0].isnumeric() and a[i][0] not in my_company.lower().split() and a[i][0] not in names:
                my_val = 0
                for c in a[i][0]:
                    if c in string.punctuation:
                        my_val += 1
                if my_val == 0:
                    indices += [i]

        return combinePlurals([a[i] for i in indices])













