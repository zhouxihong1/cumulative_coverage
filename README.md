# cumulative_coverage
cumulative coverage, base on git diff and cobertura；累计覆盖率,基于git diff 和 Cobertura XML

### parse_diff_map.py

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

### modify_cobertura.py

    支持Java -> Jacoco -> Cobertura
    Python -> CoveragePy -> Cobertura
    Go -> goc -> Cobertura
    C/C++/MSVC -> OpenCppCoverage -> Cobertura
    C/C++/GCC/Clang -> GCOV => Cobertura
    覆盖率信息转换成 Cobertura格式后，即可完成累计覆盖率的实施
