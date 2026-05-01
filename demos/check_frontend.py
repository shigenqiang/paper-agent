"""
前端诊断脚本 - 检查前端配置和依赖

帮助诊断前端空白页面的问题
"""
import os
import json

def check_frontend():
    """检查前端配置"""
    print("=" * 60)
    print("前端诊断报告")
    print("=" * 60)

    frontend_dir = "frontend"

    # 1. 检查目录结构
    print("\n1. 检查目录结构:")
    required_files = [
        "package.json",
        "index.html",
        "vite.config.js",
        "src/main.jsx",
        "src/App.jsx",
    ]

    for file in required_files:
        path = os.path.join(frontend_dir, file)
        exists = "✅" if os.path.exists(path) else "❌"
        print(f"   {exists} {file}")

    # 2. 检查 package.json
    print("\n2. 检查 package.json:")
    package_json_path = os.path.join(frontend_dir, "package.json")
    if os.path.exists(package_json_path):
        with open(package_json_path, 'r', encoding='utf-8') as f:
            package = json.load(f)
            print(f"   名称: {package.get('name')}")
            print(f"   版本: {package.get('version')}")
            print(f"   脚本:")
            for script, cmd in package.get('scripts', {}).items():
                print(f"      {script}: {cmd}")
    else:
        print("   ❌ package.json 不存在")

    # 3. 检查 node_modules
    print("\n3. 检查依赖安装:")
    node_modules = os.path.join(frontend_dir, "node_modules")
    if os.path.exists(node_modules):
        count = len(os.listdir(node_modules))
        print(f"   ✅ node_modules 存在 ({count} 个包)")
    else:
        print("   ❌ node_modules 不存在 - 需要运行 npm install")

    # 4. 检查构建输出
    print("\n4. 检查构建输出:")
    dist_dir = os.path.join(frontend_dir, "dist")
    if os.path.exists(dist_dir):
        files = os.listdir(dist_dir)
        print(f"   ✅ dist 目录存在 ({len(files)} 个文件)")
    else:
        print("   ⚠️  dist 目录不存在 - 需要运行 npm run build")

    # 5. 诊断建议
    print("\n" + "=" * 60)
    print("诊断建议:")
    print("=" * 60)

    if not os.path.exists(node_modules):
        print("\n❌ 问题: 依赖未安装")
        print("   解决方案:")
        print("   1. 安装 Node.js (https://nodejs.org)")
        print("   2. cd frontend")
        print("   3. npm install")
        print("   4. npm run dev")

    elif not os.path.exists(dist_dir):
        print("\n⚠️  提示: 未构建生产版本")
        print("   开发模式:")
        print("   cd frontend && npm run dev")
        print("   ")
        print("   生产模式:")
        print("   cd frontend && npm run build")

    else:
        print("\n✅ 前端配置正常")
        print("   启动方式:")
        print("   ")
        print("   方式 1: 开发模式")
        print("   cd frontend && npm run dev")
        print("   ")
        print("   方式 2: Docker")
        print("   docker-compose up -d frontend")

    print("\n" + "=" * 60)
    print("后端 API 状态:")
    print("=" * 60)
    print("   地址: http://localhost:8000")
    print("   健康检查: curl http://localhost:8000/health")
    print("   API Key: dev-api-key")

if __name__ == "__main__":
    check_frontend()
