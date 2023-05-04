#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@File        : parse_input_file.py
@Contact     : zhouxihong
@Version     : 1.0
@Modify Time : 2023/4/25 14:09
@Author      : zhouxihong
@Desciption  : None
@License     : (C)Copyright 2021-Inf, zhouxihong
"""
import json
import os
import sys

from typing import List

import chardet


class ParseDiffMap:
    """
    实现行号标记的关键类:
    1. 通过定制的git diff 命令生成包含代码所有上下文的patch
    >> 1.1 通过添加 -U指令,实现生成未修改代码的上下文
    >> 1.2 可生成任意工程目录下的patch文件, 且输出路径自定义
    2. 实现一套解析算法,将diff patch中旧版本到新版本的代码行号映射关系进行标记:
    >> 2.1 记录信息包括:
    >> 2.1.1 代码文件名记录: 检查 diff生成的文件名, old_name 映射 new_name
    >> 2.1.2 代码checkSum记录: 记录该文件的checkSum值 old -> new
    >> 2.1.3 代码行新增: 新增一行代码, type为 ins, 行号映射为 0 -> new
    >> 2.1.4 代码行删除: 删除一行代码, type 为 del, 行号映射为 old -> 0
    >> 2.1.5 旧代码被修改: -> 旧代码被删除,行号映射为 old -> 0, 新增一行, 映射为 0 -> new
    >> 2.1.6 旧代码的上下文被增加N行: 实现旧代码新代码的全映射, type为cntx, 行号映射为 old -> old+N=new
    >> 2.1.7 旧代码的上下文被删除N行: 旧->新, 行号映射为 old -> old-N=new (M<old)
    >> 2.1.8 旧代码的上下文增加了N行,同时删除了M行, 旧->新 old -> old+N-M=new (M<old)
    >> 2.1.9 旧代码的每一行都可能发生如上情况: 遍历单个 diff文件时,读取添加每一行,特征算法动态累计, 实现旧->新行号全映射
    >> 2.1.10 Patch文件存在N个,通过累计遍历的方式,持续解析每一组diff映射,实现git diff记录的所有文件的行号映射
    """

    @staticmethod
    def generate_git_diff_patch(code_path, output_path, old_commit_id, new_commit_id, is_full_code=True):
        """
        指定路径生成 git diff patch文件
        :param code_path: 代码路径,要求是git仓库
        :param output_path: 输出的patch路径
        :param old_commit_id: 基线commit_id, 也为待对比的commit_id
        :param new_commit_id: 当前commit_id
        :param is_full_code: 是否包含完整code, 默认包含(做行号平移算法时必须包含)
        :return:
        """
        if is_full_code:
            lines = "-U9999999"
        else:
            lines = "-U0"
        git_cmd = f"cd {code_path} && git diff {lines} {old_commit_id} {new_commit_id} > {output_path}"
        print(git_cmd)
        os.system(git_cmd)

    @staticmethod
    def parse_input_file(diff_output_path, encoding="utf-8"):
        """
        解析diff输入文件, 支持动态检测编码格式
        :param encoding: 切换为动态编码检测,此参数保留,实际不需要传递
        :param diff_output_path: 输入diff文件内容或者路径
        :return:
        """
        print(encoding)
        if diff_output_path[0:4] != "diff":
            print("输入为路径")
            # try:
            #     with open(diff_output_path, "r+", encoding=encoding) as f:
            #         diff_output = f.read()
            # except Exception as e:
            #     print(e)
            #     print("diff文件中存在非{}字符,尝试gb2312编码".format(encoding))
            #     try:
            #         with open(diff_output_path, "r+", encoding="gb2312") as f:
            #             diff_output = f.read()
            #     except Exception as e:
            #         print("diff文件中存在非{}字符,将尝试{}忽略错误模式".format("gb2312", "utf-8"))
            #         print(e)
            #         with open(diff_output_path, "r+", encoding="utf-8", errors="ignore") as f:
            #             diff_output = f.read()

            # 自动猜测编码格式,去掉encoding
            with open(diff_output_path, 'rb') as f:
                content = f.read()
                encoding = chardet.detect(content)['encoding']
                print(f"检测的编码格式为 {encoding}")
                diff_output = content.decode(encoding)
        else:
            print("输入为diff文件")
            diff_output = diff_output_path
        return diff_output

    def parse_diff(self, diff_out_path, out_json_path=None, encoding="utf-8", is_contain_content=False) -> List[dict]:
        """
        通过输入git diff的任意两个版本的解析diff文件,
        实现将原始版本映射到新版本的行号
        :param encoding: diff文件的编码格式,一般不需要更改,utf-8
        :param diff_out_path: diff patch输入路径
        :param out_json_path: 输出的json路径, 如果不填写,也可以通过return获取到json文件,填写后会输出到文件,但不影响返回值
        :param is_contain_content: 是否包含行的代码信息 (默认关闭, 无特殊情况不建议开启,开启后会导致json文件巨大)
        :return:
        """
        files = []
        current_file = None
        current_block = None
        # 读取diff 文件
        diff_output = self.parse_input_file(diff_output_path=diff_out_path, encoding=encoding)

        for line in diff_output.splitlines():  # 解析 diff文件的每一行
            if line.startswith("diff --git"):
                # Start of a new file
                _, _, old_file, new_file = line.split()
                old_file = old_file.split("a/")[-1]
                new_file = new_file.split("b/")[-1]
                current_file = {
                    "type": "changed",
                    "oldName": old_file,
                    "newName": new_file,
                    "checksumBefore": None,
                    "checksumAfter": None,
                    "mode": None,
                    "isBinary": False,
                    "blocks": []
                }
                files.append(current_file)
                # print(files)
            # elif line.startswith("old mode"):
            #     current_file["mode"] = int(line.split()[-1], 8)
            # elif line.startswith("new mode"):
            #     current_file["mode"] = int(line.split()[-1], 8)
            elif line.startswith("index"):  # index xxx..xxx mode
                # Parse checksums
                temp_list = line.split()
                temp, mode = temp_list[1], temp_list[-1]
                checksum_before, checksum_after = temp.split("..")
                current_file["checksumBefore"] = checksum_before
                current_file["checksumAfter"] = checksum_after
                current_file["mode"] = mode
            elif line.startswith("Binary files"):
                # File is binary
                current_file["isBinary"] = True
            elif line.startswith("@@"):
                # Start of a new block
                current_block = {
                    "header": line,
                    "ln_old": None,
                    "ln_new": None,
                    "lines": []
                }
                current_file["blocks"].append(current_block)
                _, old_range, new_range, _ = line.split()
                ln_old, cnt_old = old_range[1:].split(",")
                ln_new, cnt_new = new_range[1:].split(",")
                current_block["ln_old"] = int(ln_old)
                current_block["ln_new"] = int(ln_new)

            elif line.startswith("---") or line.startswith("+++"):  # 过滤文件头信息
                continue

            elif line.startswith("-"):
                # Deleted line
                del_dict = {
                    "type": "del",
                    "prefix": line[0],
                    # "content": line[1:].strip(),
                    "new_line": 0,
                    "old_line": current_block["ln_old"],
                    # "diff": [{"tag": "del", "content": line[1:].strip()}]
                    "diff": [{"tag": "del"}]
                }
                if is_contain_content:
                    del_dict.update({"diff": [{"tag": "del", "content": line[1:].strip()}]})
                current_block["lines"].append(del_dict)
                current_block["ln_old"] += 1
            elif line.startswith("+"):
                # Added line
                add_dict = {
                    "type": "ins",
                    "prefix": line[0],
                    # "content": line[1:].strip(),
                    "new_line": current_block["ln_new"],
                    "old_line": 0,
                    "diff": [{"tag": "ins"}]
                }
                if is_contain_content:
                    add_dict.update({"diff": [{"tag": "ins", "content": line[1:].strip()}]})
                current_block["lines"].append(add_dict)
                current_block["ln_new"] += 1
            elif line.startswith(" "):
                # Context line
                context_dict = {
                    "type": "cntx",  # 上下文
                    "prefix": line[0],
                    # "content": line[1:].strip(),
                    "new_line": current_block["ln_new"],
                    "old_line": current_block["ln_old"]
                }
                if is_contain_content:
                    context_dict.update({"content": line[1:].strip()})
                current_block["lines"].append(context_dict)
                current_block["ln_old"] += 1
                current_block["ln_new"] += 1
        if out_json_path:
            with open(out_json_path, "w+", encoding="utf-8") as f:
                f.write(json.dumps(files, ensure_ascii=False))
            print(f"完成diff map {out_json_path} 写入")
        return files


if __name__ == '__main__':
    pass

    # ParseDiffMap().generate_git_diff_patch(code_path="D:/uws/increase/uws", output_path=os.getcwd() + "/e.patch",
    #                                        old_commit_id="8c606ca", new_commit_id="568be6c", is_full_code=True)
    # parsed_diff = ParseDiffMap().parse_diff("e.patch", "e.json", is_contain_content=False)

    # print(parsed_diff)

    # python3 parse_diff_map.py "D:/uws/increase/uws" "e.patch" "8c606ca" "568be6c" "e.json"
    pdm = ParseDiffMap()
    print(sys.argv)
    pdm.generate_git_diff_patch(code_path=sys.argv[1], output_path=os.getcwd()+"/"+sys.argv[2], old_commit_id=sys.argv[3], new_commit_id=sys.argv[4])
    pdm.parse_diff(diff_out_path=sys.argv[2], out_json_path=sys.argv[5])
