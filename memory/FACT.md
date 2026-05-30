# 持久事实

- 用户要求：不要保存任何文件到 C 盘；项目相关文件应保存在 `F:\kelaode\quanzidong` 或用户指定的 F 盘路径。
- 用户要求：开始/继续项目前先核对项目情况，尤其是 `git status`。
- 用户要求：每完成一个阶段就提交并推送到仓库 `https://github.com/zz9744813-lab/wudixeixaioshuo.git`。
- 工具使用经验：Read 工具读取普通文本/代码文件时不要传 `pages: ""`，空字符串会报 `Invalid pages parameter`；只有读取 PDF 且需要页码时才传合法页码。