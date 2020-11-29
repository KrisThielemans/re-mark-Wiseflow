"""
Parse Wiseflow marked multiple-choice question and re-mark

This set of functions allows parsing HTML output from Wiseflow for one or more students,
write a CSV file counting the answers, and apply a new marking scheme.

This assumes that Wiseflow marking was already completed for a multiple-choice exam.
As Wiseflow currently doesn't allow setting a different mark-scheme, it can be used
to re-mark.

An example marking function is given, but you would have to write your own.

The file can be used as a script like this:

    python3 re-mark-Wiseflow output.csv file1.htm file2.html file3.html ....

Output will be multiple csv files (one per student), and a summary in output.csv

The file can also be used as a module. Most functions are documented.

CAVEATS and problems:
- I have not been able to scrape directly from URL due to permissions.
- This relies on Wiseflow formatting of the HTML, which can break with different versions of Wiseflow of course.
- Python3 is required

Author: Kris Thielemans
"""
#%% imports
from bs4 import BeautifulSoup
# regular expressions
import re
# CSV writer
import csv
#%% function to 
def get_cookies(ff_cookies):
    """create a cookiejar from a Firefox file

    create a CookieJar object from a Firefox sqlite file

    Parameters:
    -----------
    ff_cookies: filename

    Returns:
    -------
    a http.CookieJar object
    """
    import sqlite3
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    con = sqlite3.connect(ff_cookies)
    cur = con.cursor()
    cur.execute("SELECT host, path, isSecure, expiry, name, value FROM moz_cookies")
    for item in cur.fetchall():
        c = http.cookiejar.Cookie(0, item[4], item[5],
            None, False,
            item[0], item[0].startswith('.'), item[0].startswith('.'),
            item[1], False,
            item[2],
            item[3], item[3]=="",
            None, None, {})
        #print(c)
        cj.set_cookie(c)
    return cj
#%% get a cookjar from default Firefox file
def get_cookie_jar():
    import os
    import pathlib
    import shutil
    # This doesn't work (it uses the wrong directory)
    # cookiejar = browsercookie.firefox()
    ff_path=pathlib.Path(os.path.expanduser('~/.mozilla/firefox/'))
    ff_path=list(ff_path.rglob('*.default-release/'))
    if ff_path is None:
        raise RuntimeError('Firefox cookie file not found')
    ff_cookies=ff_path[0] / 'cookies.sqlite'
    ff_cookies_copy='cookies.sqlite'
    shutil.copyfile(ff_cookies, ff_cookies_copy)
    return get_cookies(ff_cookies_copy)
#%% create a beautifulsoup object for one file/URL (for one student)
def soup_from_URL(url, cookiejar):
    import requests
    s = requests.Session()
    s.cookies = cookiejar
    response=s.get(url)
    #response = requests.get(url, cookies=cookiejar)
    return BeautifulSoup(response.content, 'html.parser')

def soup_from_file(filename):
    with open(filename) as fp:
        soup = BeautifulSoup(fp, 'html.parser')
    return soup
# %%
def find_name(soup):
    """find student name"""
    name=soup.find("div", attrs={"ng-if": re.compile("selectedParticipant.*!selectedGroup")})
    if name is None:
        raise RuntimeError("student name not found")
    return ' ' .join(name.div.text.split())

# %%
class resultsForOneQuestion:
    """
    A class that stores results for one question

    Attributes:
    -----------
        correct : int
            number of correctly selected answers (green)
        incorrect=0 # red
            number of incorrectly selected answers (red)
        valid_not_selected
            number of correct answer, but not selected (yellow)
        answers
            total number of answers
        valid
            total number of correct answers
    """
    def __init__(self, ul):
        """count results for one question

            Parameters
            ----------
            ul: a Beautiful object that should have results from one question only
        """    
        self.correct=0
        self.incorrect=0
        self.valid_not_selected=0
        self.answers=0
        self.valid=0

        for x in ul.find_all("li",class_="lrn-mcq-option"):
            c= x.get('class')
            #print(c)
            self.answers+=1
            if 'lrn_correct' in c:
                self.correct+=1
            if 'lrn_incorrect' in c:
                self.incorrect+=1
            if 'lrn_valid' in c:
                self.valid_not_selected+=1
        self.valid=self.correct + self.valid_not_selected
    def __str__(self):
        return ("#answers=%d #correct_answers=%d #correct=%d #incorrect=%d" % 
            (self.answers, self.valid, self.correct, self.incorrect))
#%%
def list_questions_html(soup):
    res=soup.find_all("ul",class_="lrn-response-validate-wrapper")
    if not res:
        raise RuntimeError("No questions found")
    return res
#%%
def list_questions(soup):
    return [resultsForOneQuestion(r) for r in list_questions_html(soup)]
# %% marking scheme
def mark_question(results):
    if results.valid == 1:
        if results.correct==1 and results.incorrect==0:
            return 1
        else:
            return 0
    else:
        return results.correct*1 - results.incorrect*.25

#%%
def marks_as_table(question_list, mark_scheme=mark_question):
    """ return marks for one student as a table

    Parameters:
    ----------
    question_list: as found by list_of_questions
    mark_scheme: function to compute a mark for one question

    Returns:
    a list of lists, with each element being [answers, valid_answers, correct, incorrect, mark]
    """
    return [ [r.answers, r.valid, r.correct, r.incorrect, mark_scheme(r)] for r in question_list]

def write_CSV(filename, marks_as_table):
    fields=['answers', 'valid answers', 'correct', 'incorrect', 'mark']

    with open(filename, 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
        csvwriter.writerows(marks_as_table)
#%%
def export_student_to_CSV(name, marks):
    """export to name.csv""" 
    # name of csv file (replacing spaces with _)
    filename = name.replace(" ", "_") + ".csv"
    #print("Writing to:", filename)
    write_CSV(filename, marks)

def total_mark(marks):
    max_marks=sum(( row[1] for row in marks))
    mark=sum(( row[-1] for row in marks))
    return [max_marks, mark, mark / max_marks * 100]

def mark_student(soup):
    name=find_name(soup)
    qs=list_questions(soup)
    marks=marks_as_table(qs)
    export_student_to_CSV(name, marks)
    return [name] +  total_mark(marks)
#%%
def process_student(filename_or_URL):
    """calls mark_student on one student HTML file

    Creates a BeautifulSoup object and calls mark_student.

    If the filename_or_URL starts with "https://", attempt to get Firefox cookies
    before reading from the URL.

    Parameters:
    ----------
    filename_or_URL: either a local filename, or a URL

    Returns:
    --------
    return-value of mark_student
    """
    if filename_or_URL[0:8] == "https://":
        cookiejar=get_cookie_jar()
        soup=soup_from_URL(filename_or_URL, cookiejar)
    else:
        soup=soup_from_file(filename_or_URL)
    #for q in list_questions(soup):
    #    print(q, "mark=",mark_question(q))
    return mark_student(soup)
# %%
def process_students(output_filename, filenames):
    all_marks=[process_student(filename) for filename in filenames]
    if not output_filename is None:
        fields=['Name', 'Max mark', 'Mark','Percentage']
        with open(output_filename, 'w') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(fields)
            csvwriter.writerows(all_marks)
#%%
if __name__ =="__main__":
    import sys
    output_filename=sys.argv[1]
    filenames=sys.argv[2:]
    process_students(output_filename, filenames)
#%%
#process_student('test3.html')
# %%

# %%
