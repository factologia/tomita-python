# -*- codong: utf-8 -*-

from functools import partial
from operator import itemgetter
from os.path import dirname, join

import pytest

from parse_firstline import ParseFirstline

__author__ = 'tonal'

FIX_PATH = dirname(__file__)
join_fix = partial(join, FIX_PATH)

def test_start_stop_firstline():
  with ParseFirstline(conf_path=join_fix('config_firstline.proto')) as parser:
    pass

@pytest.fixture
def parser():
  return ParseFirstline(conf_path=join_fix('config_firstline.proto'))

def load_facts(facts_name):
  with open(join_fix(facts_name)) as inp:
    data = eval(inp.read().strip())
    return data

def test_firstline(parser):
  data = load_facts('fix_firstline.py.txt')
  #parser = ParseFirstline()
  for text, facts in data:
    rsp_facts = tuple(parser.text2facts(text))
    assert facts == rsp_facts, text

@pytest.mark.parametrize('skip_empty_doc', [True, False])
def test_firstline_iter(parser, skip_empty_doc):
  data = load_facts('fix_firstline.py.txt')
  #parser = ParseFirstline()
  i = 0
  for i, ((text, facts), rsp_facts) in enumerate(
    parser.text2facts_iter(data, itemgetter(0), skip_empty_doc=skip_empty_doc),
    1
  ):
    rsp_facts = tuple(rsp_facts)
    assert facts == rsp_facts, text
  if skip_empty_doc:
    assert i == sum(1 for _, facts in data if facts)
  else:
    assert i == len(data)
