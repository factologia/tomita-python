# -*- codong: utf-8 -*-
import os
from os import path as osp
import select
import subprocess
import sys

from lxml import etree

__author__ = 'tonal'

class ErrorTomitaInit(subprocess.CalledProcessError):
  pass

class TomitaParser(subprocess.Popen):

  def __init__(
    self, exe_path='tomita-linux64', conf_path='config.proto',
    empty_timeout=.1
  ):
    conf_path = osp.abspath(conf_path)
    conf_dir = osp.dirname(conf_path)
    self.empty_timeout = empty_timeout
    PIPE = subprocess.PIPE
    super().__init__(
      [exe_path, conf_path], bufsize=0, stdin=PIPE, stdout=PIPE, stderr=PIPE,
      cwd=conf_dir, universal_newlines=False)
    o_no = self._stdout_no = self.stdout.fileno()
    _set_non_blocking(o_no)
    e_no = self._stderr_no = self.stderr.fileno()
    _set_non_blocking(e_no)
    stderr, stdout = self.stderr, self.stdout
    err_out = b''
    with select.epoll() as pool_obj:
      pool_obj.register(e_no, select.EPOLLIN | select.EPOLLPRI)
      pool_obj.register(o_no, select.EPOLLIN | select.EPOLLPRI)

      while self.poll() is None:
        # rd, _, _ = select.select([e_no], [], [], 0)
        #if e_no in rd:
        rd = pool_obj.poll(0)
        if rd and any(fd == e_no for fd, _ in rd):
          err = stderr.read()
          err_out += err
          last_eline = err_out.splitlines()[-1]
          if (
            # [23:01:17 16:56:24] - Start.  (Processing files.)
              last_eline.startswith(b'[') and
              last_eline.endswith(b'] - Start.  (Processing files.)')
          ):
            break
      else:
        if self.poll() is not None:
          raise ErrorTomitaInit(self.returncode, self.args, stderr=err_out)
      self.err_lines = b''
      #rd, _, _ = select.select([o_no], [], [], 0)
      #if o_no in rd:
      rd = pool_obj.poll(0)
      if rd and any(fd == o_no for fd, _ in rd):
        out_dat = stdout.read()

  def text2facts(self, text: str):
    if self.poll() is not None:
      raise ErrorTomitaInit(self.returncode, self.args)

    stdin, stderr, stdout = self.stdin, self.stderr, self.stdout
    stderr_no, stdout_no = self._stderr_no, self._stdout_no
    with select.epoll() as pool_obj:
      pool_obj.register(stderr_no, select.EPOLLIN | select.EPOLLPRI)
      pool_obj.register(stdout_no, select.EPOLLIN | select.EPOLLPRI)

      #rd, _, _ = select.select([stdout_no], [], [], 0)
      rd = pool_obj.poll(0)
      if rd and any(fd == stdout_no for fd, _ in rd):
        out_dat = stdout.read()

      stdin.write(text.replace('\n', ' ').encode('utf-8') + b'\n')
      stdin.flush()

      data = b''
      self.err_lines = b''
      empty_timeout = self.empty_timeout
      while self.poll() is None:
        #rd, _, _ = select.select([stderr_no, stdout_no], [], [], empty_timeout)
        rd = pool_obj.poll(empty_timeout)
        if not rd:
          return ()
        rd = tuple(fd for fd, _ in rd)
        if stderr_no in rd:
          self._read_err(stderr)
        if stdout_no in rd:
          try:
            data += stdout.read()
            data = data.replace(b'<fdo_objects>', b'')
            xml = etree.XML(data)
            return xml
          except etree.XMLSyntaxError:
            #print('!!! ', data)
            #raise
            continue
    return

  def text2facts_iter(self, doc_iter, doc2text=None, *, skip_empty_doc=True):
    if self.poll() is not None:
      raise ErrorTomitaInit(self.returncode, self.args)

    if doc2text is None:
      doc2text = lambda t: t

    stdin, stderr, stdout = self.stdin, self.stderr, self.stdout
    stderr_no, stdout_no = self._stderr_no, self._stdout_no

    with select.epoll() as pool_obj:
      pool_obj.register(stderr_no, select.EPOLLIN | select.EPOLLPRI)
      pool_obj.register(stdout_no, select.EPOLLIN | select.EPOLLPRI)

      #rd, _, _ = select.select([stdout_no], [], [], 0)
      #if stdout_no in rd:
      #rd = pool_obj.poll(0)
      #if rd and any(fd == stdout_no for fd, _ in rd):
      out_dat = stdout.read()

      id2doc = {}
      data = b''
      self.err_lines = b''
      read_data = self._read_data
      read_err = self._read_err
      for i, doc in enumerate(doc_iter, 1):
        text = doc2text(doc)
        id2doc[str(i)] = doc
        stdin.write(text.replace('\n', ' ').encode('utf-8') + b'\n')
        stdin.flush()
        if self.poll() is not None:
          raise ErrorTomitaInit(self.returncode, self.args, stderr=self.err_lines)
        step = 0
        while self.poll() is None and step < 5:
          #rd, _, _ = select.select([stderr_no, stdout_no], [], [], .01)
          rd = tuple(fd for fd, _ in pool_obj.poll(.01))
          if stderr_no in rd:
            read_err(stderr)
          if stdout_no in rd:
            data, odoc, xml = read_data(data, id2doc, stdout)
            if odoc is None:
              step = 0
              continue
            while odoc is not None:
              yield odoc, xml
              data, odoc, xml = read_data(data, id2doc, stdout)
            break
          step += 1

      empty_timeout = self.empty_timeout
      while self.poll() is None and id2doc:
        #rd, _, _ = select.select([stderr_no, stdout_no], [], [], empty_timeout)
        rd = tuple(fd for fd, _ in pool_obj.poll(empty_timeout))
        if stderr_no in rd:
          read_err(stderr)
        if stdout_no in rd:
          data, odoc, xml = read_data(data, id2doc, stdout)
          if odoc is None:
            continue
          while odoc is not None:
            yield odoc, xml
            data, odoc, xml = read_data(data, id2doc, stdout)
          continue
        if not rd:
          if skip_empty_doc:
            break
          while id2doc:
            _, odoc = id2doc.popitem()
            yield odoc, None
      if self.poll() is not None:
        raise ErrorTomitaInit(self.returncode, self.args, stderr=self.err_lines)

  def _read_data(self, data:bytes, id2doc, stdout):
    data += stdout.read() or b''
    data = data.replace(b'<fdo_objects>', b'')
    pos = data.find(b'</document>')
    doc_tag_len = 11 # len(b'</document>')
    if pos == -1:
      return data, None, None
    xml = etree.XML(data[:pos+doc_tag_len])
    data = data[pos+doc_tag_len:].lstrip()
    did = xml.get('di')
    odoc = id2doc.pop(did)
    return data, odoc, xml

  def _read_err(self, stderr):
    err = stderr.read()
    self.err_lines += err
    sys.stderr.write(err.decode('utf-8'))

def _set_non_blocking(fd):
  """
  Set the file description of the given file descriptor to non-blocking.
  """
  import fcntl
  flags = fcntl.fcntl(fd, fcntl.F_GETFL)
  flags = flags | os.O_NONBLOCK
  fcntl.fcntl(fd, fcntl.F_SETFL, flags)