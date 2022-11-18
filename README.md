# keyword-filter
Filters .pdf for particular and new keywords. Written in python

3/1/2021 - v 1.0.0
- Updated functions to use the class Transcript() and moved functions to keyword_lib.py.
- Restructured notebook to read all .pdf files in a given directory and then created a widget allowing the user
  to select which file to process. Widget also displays the report as a table.
- Removed save/export, will think about putting it back in as a button.

5/25/2021 - v2.0.0
- Added Rake() to Transcript() allowing notebook to find new keywords. Currently works for management section only.
- Also added widget to plot occurences of known keywords mentioned either by management or questioners.
- Tabular report of keywords broken into quartiles to isolate more important keywords from others.
