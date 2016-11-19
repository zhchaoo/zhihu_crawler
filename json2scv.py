#!/usr/bin/python

import ast
import collections
import csv

results = {}
with open('result.txt', 'r') as f:
    for item in f.readlines():
        if item and len(item) > 3 and item[0] == '{':
            if item[-2] == '}':
                end_index = -1
            elif item[-3] == '}':
                end_index = -2
            else:
                continue
            question_item = ast.literal_eval(item[:end_index])
            if question_item.has_key("url_token"):
                results[int(question_item["url_token"])] = question_item
    f.close()

# sort result by key.
sorted_results = collections.OrderedDict(sorted(results.items()))

with open('result.csv', 'w') as f:
    result_writer = csv.writer(f)
    # write head
    result_writer.writerow(["url_token", "title", "answer_num", "answer_top", "follow_num", "tag_list", "visitor_num"])
    # write result
    for item in sorted_results.values():
        try:
            result_writer.writerow([item["url_token"], item["title"], item["answer_num"],item["answer_top"],
                                    item["follow_num"], '|'.join(item["tag_list"]), item["visitor_num"]])
        except KeyError, e:
            print e
    f.close()

