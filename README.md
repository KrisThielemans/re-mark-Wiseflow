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
