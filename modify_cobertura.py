#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File        : modify_cobertura.py    
@Contact     : zhouxihong
@Version     : 1.0
@Modify Time : 2023/4/25 16:21
@Author      : zhouxihong
@Desciption  : None
@License     : (C)Copyright 2021-Inf, zhouxihong
"""
import json
# import os.path
import sys
import traceback
import xml.etree.ElementTree as Et

# import pathlib
# from parse_diff_map import ParseDiffMap


def modify_coverage_file(file_path, class_name, file_name, line_number, new_hits):
    """
    修改指定Cobertura文件中特定类、文件、行号的覆盖率
    """
    tree = Et.parse(file_path)
    root = tree.getroot()
    for package in root.iter('package'):
        for clazz in package.iter('class'):
            if clazz.attrib.get('name') == class_name and clazz.attrib.get('filename') == file_name:
                for lines in clazz.iter('lines'):
                    for line in lines.iter('line'):
                        if line.attrib.get('number') == line_number:
                            line.attrib['number'] = str(new_hits)
    tree.write(file_path, encoding='utf-8', xml_declaration=True)


# def modify_coverage(file_path, class_name, file_name, num_dict):
def modify_coverage(file_path, diff_dict):
    """
    修改指定Cobertura文件中特定类、文件、行号的覆盖率
    """
    tree = Et.parse(file_path)
    root = tree.getroot()
    try:
        for key in diff_dict.keys():
            for package in root.iter('package'):
                for clazz in package.iter('class'):
                    # if clazz.attrib.get('name') == class_name and clazz.attrib.get('filename') == file_name:
                    if clazz.attrib.get('filename').lower() == key.lower():
                        clazz.attrib["filename"] = diff_dict[key]["filename"]
                        for lines in clazz.iter('lines'):
                            for line in lines.iter('line'):
                                old_num = line.attrib.get('number')
                                # old_num 为0时,表示该行映射不需要处理, 因为是新增的行,原始文件不存在映射;采用key:value,该行不被映射
                                # new_num 为0时,表示该行1映射是删除行,对于原始内容而言,其覆盖率信息已随之删除
                                new_num = diff_dict[key]["lines_dict"][old_num]
                                if int(new_num) == 0:
                                    lines.remove(line)
                                    continue
                                line.attrib["number"] = str(new_num)

        tree.write(file_path, encoding='utf-8', xml_declaration=True)
    except Exception as e:
        print(e)
        traceback.print_exc()
        print("当前映射关系发生变更, 请检查是否是重复生成xml")


def list_filename(file_path):
    """
    修改指定Cobertura文件中特定类、文件、行号的覆盖率
    """
    tree = Et.parse(file_path)
    root = tree.getroot()
    for package in root.iter('package'):
        for clazz in package.iter('class'):
            print(clazz.attrib.get("filename"))
            # if clazz.attrib.get('name'):
            #     for lines in clazz.iter('lines'):
            #         for line in lines.iter('line'):
            #             old_num = line.attrib.get('number')
            #             line.attrib['number'] = num_dict[old_num]


def remove_common_prefix(file_path, common_prefix=r"build\src\uws-windows-app", is_write=True):
    """
    移除通用前缀, 适用于Cobertura
    :param file_path:
    :param common_prefix:
    :param is_write:
    :return:
    """
    tree = Et.parse(file_path)
    root = tree.getroot()
    common_prefix = common_prefix.replace(r"\\", "\\").replace("\\", "/")
    for source in root.iter("source"):
        source.text = "."

    for package in root.iter('package'):
        for clazz in package.iter('class'):
            old_file_name = clazz.attrib.get("filename").replace(r"\\", "\\").replace("\\", "/")
            # print(old_file_name, common_prefix)
            clazz.attrib["filename"] = old_file_name.replace(common_prefix, "", 1).lstrip("/")
            print("replace {} -> {}".format(old_file_name, clazz.attrib.get("filename")))
    if is_write:
        tree.write(file_path, encoding='utf-8', xml_declaration=True)


def git_diff_line_map(line_map, lower_case=False):
    with open(line_map, "r+", encoding="utf-8") as f:
        data = f.read()
    json_dict = json.loads(data)
    file_name_dict = {}

    for item in json_dict:
        old_name = item.get("oldName")
        new_name = item.get("newName")
        lines_list = item.get("blocks")[0].get("lines")
        lines_dict = {}  # 从json中取出行号映射关系
        value_zero = []  # 添加新增代码映射的列表记录 old -> new ，0:list
        for lines_item in lines_list:
            old_line = str(lines_item.get("old_line"))
            if old_line == "0":
                value_zero.append(lines_item.get("new_line"))
                lines_dict[old_line] = value_zero
                continue
            new_line = str(lines_item.get("new_line"))
            lines_dict[old_line] = new_line
        if lower_case:
            file_name_dict[old_name.lower()] = {"filename": new_name.lower(), "lines_dict": lines_dict}
        else:
            file_name_dict[old_name] = {"filename": new_name, "lines_dict": lines_dict}
    return file_name_dict


if __name__ == '__main__':
    pass

    # # # 用法示例
    # r = git_diff_line_map("demo.json")
    # # print(r)
    # remove_common_prefix("demo.xml", "c:/build/src/uws-windows-app")
    # modify_coverage('demo.xml', r)
    #
    # # list_filename('demo.xml')

    print(sys.argv)
    # python3 modify_cobertura.py e.json e.xml
    r = git_diff_line_map(sys.argv[1])

    modify_coverage(sys.argv[2], r)

