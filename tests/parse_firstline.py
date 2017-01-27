# -*- codong: utf-8 -*-
__author__ = 'tonal'

from lxml import etree

from tomita_parser import TomitaParser

class ParseFirstline(TomitaParser):

  def __init__(
    self, exe_path='tomita-linux64', conf_path='config_firstline.proto',
    empty_timeout=.1
  ):
    super().__init__(
      exe_path=exe_path, conf_path=conf_path, empty_timeout=empty_timeout)

  def text2facts(self, text: str):
    xml = super().text2facts(text)
    if xml is () or xml is None:
      return xml
    yield from self.parse_facts(xml)

  def parse_facts(self, xml):
    for elt in xml.xpath('//FirstLine'):
      floor = elt.find('Line')
      floor = floor.get('val')
      yield floor

  def text2facts_iter(self, doc_iter, doc2text=None, *, skip_empty_doc=True):
    parse_facts = self.parse_facts
    for (doc, xml) in super().text2facts_iter(
      doc_iter, doc2text, skip_empty_doc=skip_empty_doc
    ):
      if xml is None:
        yield doc, ()
      else:
        yield doc, parse_facts(xml)
