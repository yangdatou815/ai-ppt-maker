# Makefile — 开发环境快捷命令
.PHONY: setup lint test check

## 首次安装（克隆后运行一次）
setup:
	pip install pre-commit
	pre-commit install
	pip install -e backend/.[dev]
	cd frontend && npm install --legacy-peer-deps
	@echo "\n✅ 开发环境就绪。每次 git commit 会自动运行代码检查。"

## 运行所有检查（等同于 commit 时的检查）
check:
	pre-commit run --all-files

## 仅 lint
lint:
	cd backend && ruff check app tests
	cd backend && ruff format --check app tests

## 运行测试
test:
	cd backend && python -m pytest tests/ -q
	cd frontend && npx vitest run --reporter=verbose

## 重新生成 .bat 脚本
bat:
	python scripts/build_scripts.py
