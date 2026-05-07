# `.workflow.disabled/` — 暂时禁用的 Gitee Go 流水线

> **状态**: 暂停 — 等待在 Gitee Go 网页上用「图形化编辑」重新配出能被 schema 校验通过的 YAML。

## 为什么禁用

`.workflow/` 是 Gitee Go 的约定目录。我们手写的三条流水线（branch / pr / master）符合 Gitee Go 1.x 文档的 schema，但 2026 年 Gitee Go 改版后控制台报「流水线配置有误，请检查您的配置」，提交也不再触发构建。Gitee 官方的 YAML schema 参考页很多 404，无法对照修。

为了不让 push 反复触发解析失败的告警噪音，把目录改名成 `.workflow.disabled/`，Gitee Go 不会再扫到。文件保留在仓库里，方便：

- 之后用图形化编辑器重新配通后，把生成的 YAML 和这里的内容做 diff，回填我们已经验证过的步骤（清华源、npmmirror、coverage 阈值、artifact 路径）。
- 给 GitHub Actions / GitLab CI / Jenkins 做参考。

## 这些 yaml 里包含的"经验"

不要丢，迁移到任何 CI 平台都用得上：

- **后端 DoD**: `pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple` → `pip3 install --user -e "./backend[dev]"` → `ruff check backend` → `pytest --cov=app --cov-fail-under=70` → `python3 scripts/build_scripts.py --check`（脚本漂移检查）
- **前端 DoD**: `npm config set registry https://registry.npmmirror.com` → `npm ci` → `npm test`（vue-tsc + vitest）→ `npm run build`
- **触发**: master/main push → 完整 DoD + artifact 上传；其他分支 push → 后端 DoD only；PR → 后端 + 前端 DoD（不上传）

## 重启流水线的步骤

1. 在 Gitee 仓库 → 流水线 → 新建 → **图形化编辑**（不要选「导入 YAML」）
2. 用 Gitee 的「Python 项目」+「Node.js 项目」模板，把上面"经验"里那些命令逐条粘进去
3. 保存后让 Gitee 自动生成 YAML，再「同步到代码仓库」（一般是写到 `.workflow/`）
4. 把目录改回 `.workflow/`（删除这个 README，把三个 yml 挪回去）
5. 验证 push 触发
