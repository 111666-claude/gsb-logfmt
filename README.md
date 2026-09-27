# logfmt

logfmt 编解码（`key=value` 序列、引号与转义、裸键），只用 Python 标准库。

```
python3 -m logfmtkit.cli --encode "msg=hello world"
python3 -m logfmtkit.cli --decode 'msg="hello world" x=1'
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **值里有空白或引号，编码时必须加引号并转义**：`msg=hello world` 按口径是 `msg="hello world"`，
  现在是原样输出（再解码会断成两段）；值里的 `"` 与 `\` 要写成 `\"` 与 `\\`。
- **解码要按引号感知分词**：`msg="hello world" x=1` 按口径是两对 `("msg","hello world")` 与 `("x","1")`，
  现在按空白切成三段（`("msg","hello")`、`("world\"", True)`、`("x","1")`）。
- 没有 `=` 的 token 是**裸键**，值为 `True`；`key=` 的值是空串；值里的 `=` 属于值（`a=b=c` 是 `("a","b=c")`）。
- 重复键按出现顺序**全部保留**（不覆盖），`--flatten` 时才按最后一次取值。
- 不变量：`decode(encode(pairs)) == pairs`（任意键值对）；空输入给空结果；同一输入重复编解码结果相同。
- 错误要带位置：未闭合的引号、非法转义（`\x`）、键里出现空白的 token 都要报错并给出第几个字符。
- 规模：100 MB 单遍流式编解码，内存 O(一行)。

## 现在的行为

- `encode` 按口径加引号与转义：`msg=hello world` 输出 `msg="hello world"`；
  值里的 `"` 与 `\` 写成 `\"` 与 `\\`；裸键（值为 `True`）只写键名。
- `decode` 按引号感知分词：`msg="hello world" x=1` 解出 `("msg","hello world")` 与 `("x","1")` 两对；
  引号内的转义会还原。
- 重复键按出现顺序全部保留；`--flatten` 时按最后一次取值。
- 错误带 0 起始的字符位置（`LogfmtError.position`）：未闭合引号、非法转义、键里含空白/控制字符等。
- 流式接口 `encode_lines` / `decode_lines` 单遍逐行处理，内存 O(一行)。
- `logfmtkit/reference.py` 是逐字符状态机的参考实现，`tests/test_reference_compare.py`
  对样例与随机 1 万组键值对逐字节比对两个实现的编码结果、解码结果与错误位置。

## 计划新增的能力

```
--encode key=value   可重复，编成一行
--decode 行          解码并打印键值对
--flatten            重复键取最后一次（对照用）
```

## 输出

```
msg="hello world"
[["msg", "hello world"], ["x", "1"]]
```

## 目录

```
logfmtkit/codec.py   编解码与转义
logfmtkit/cli.py     命令行入口
tests/               unittest 用例
```
