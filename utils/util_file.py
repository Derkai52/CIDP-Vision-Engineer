"""
用于常用文件读写的库(json格式、二进制、文本文件)
"""

import json
import os


def read_file(file, encoding='utf-8'):
    """
    doc: 读取文本文件
    :param file: 文件路径
    :param encoding: 默认utf-8
    :return: 从字符串中读取的字符串
    """
    try:
        with open(file, 'r', encoding=encoding) as f:
            return f.read()
    except Exception:
        pass


def read_json_file(file, encoding='utf-8'):
    """
    doc: 读取json格式文件
    :param file: 文件路径
    :param encoding: 默认utf-8
    :return: str对象
    """
    contents = read_file(file, encoding)
    if not contents:
        return {}
    try:
        return json.loads(contents)
    except Exception:
        return {}


def read_binary_file(file, mode='rb+'):
    """
    doc: 读取二进制文件
    :param file: 文件路径
    :param mode: 默认 rb+
    :return: 从字符串中读取的字符串
    """
    try:
        with open(file, mode) as f:
            return f.read()
    except Exception:
        pass


def write_file(file, contents, encoding='utf-8'):
    """
    doc: 写入文本文件
    :param file: 文件路径
    :param contents: 写入内容(str对象)
    :param encoding: 默认 utf-8
    :return: None
    """
    try:
        with open(file, 'w', encoding=encoding) as f:
            f.write(contents)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        return str(e)


def write_json_file(file, js, encoding='utf-8'):
    """
    doc: 写入json文件
    :param file: 文件路径
    :param js: json对象
    :param encoding: 默认 utf-8
    :return: None
    """
    return write_file(file, json.dumps(js, sort_keys=False, indent=4, separators=(",", ": ")), encoding)


def write_binary_file(file, contents, mode='wb+'):
    """
    doc: 写入二进制文件
    :param file: 文件路径
    :param contents: 写入内容
    :param mode: 默认 wb+
    :return: None
    """
    try:
        with open(file, mode) as f:
            f.write(contents)
    except Exception as e:
        return str(e)