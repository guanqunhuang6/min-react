import subprocess
import os
import sys
import re
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def run_command(command_parts):
    print(f"\nExecuting: {' '.join(command_parts)}")
    try:
        process = subprocess.run(command_parts, capture_output=True, text=True, check=False)

        if process.stdout:
            print(f"--- Stdout ---\n{process.stdout.strip()}")
        if process.stderr:
            # Vercel CLI 经常将重要信息（包括成功时的 URL）输出到 stderr
            print(f"--- Stderr ---\n{process.stderr.strip()}")

        if process.returncode != 0:
            error_message = f"Command failed: {' '.join(command_parts)}\nReturn code: {process.returncode}"
            # 优先显示 stderr 的错误信息
            if process.stderr.strip():
                error_message += f"\nError Details (from stderr):\n{process.stderr.strip()}"
            elif process.stdout.strip():
                error_message += f"\nError Details (from stdout):\n{process.stdout.strip()}"
            raise Exception(error_message)
        
        # 对于部署命令，我们需要从输出中提取部署 URL
        # Vercel CLI 通常将最终的部署 URL (类似 project-name-uniquehash.vercel.app) 打印到 stderr
        # 并标记为 "(Copied to clipboard)"
        # 也可能直接在 stdout 或 stderr 中作为最后一行输出
        combined_output = process.stderr + "\n" + process.stdout
        
        # 优先查找带有 "(Copied to clipboard)" 标记的 URL
        # 例: Production: https://project-name-xxxx.vercel.app (Copied to clipboard) [global]
        # 例: https://project-name-xxxx.vercel.app (Copied to clipboard)
        match = re.search(r'(https://[^\s]+vercel\.app) \(Copied to clipboard\)', combined_output)
        if match:
            return match.group(1)

        # 备用方案：查找最后一行以 https:// 开头的 vercel.app URL
        lines = combined_output.strip().split('\n')
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("https://") and "vercel.app" in line and not "inspect.vercel.com" in line:
                return line
        
        # 如果是 alias 命令或其他不需要特定输出的命令，返回 True 表示成功
        return True
            
    except FileNotFoundError:
        print(f"Error: Command 'npx' (或 'vercel' CLI) not found. Make sure Node.js is installed and Vercel CLI is globally available or in your project's node_modules.")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("\nPlease check:")
        print("1. If the domain is properly configured in Vercel")
        print("2. If your Vercel API token has the correct permissions")
        print("3. If the domain ownership is verified in Vercel")
        print("4. If the domain has been added to the webcoding organization")
        print("\nCurrent deployment status:")
        print(f"Project Name: {vercel_project_name if 'vercel_project_name' in locals() else 'Unknown'}")
        # print(f"Target Subdomain: {custom_subdomain if 'custom_subdomain' in locals() else 'Unknown'}")
        # print(f"Deployment URL: {deployment_url if deployment_url else 'Not available'}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/deploy.py <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    vercel_token = os.getenv("VERCEL_TOKEN")

    if not vercel_token:
        print("Error: VERCEL_TOKEN not found in environment variables (.env file).")
        sys.exit(1)

    vercel_project_name = f"user-{user_id}"
    custom_subdomain = f"{user_id}.consciousness.systems"

    print(f"--- Starting Vercel Deployment --- ")
    print(f"User ID: {user_id}")
    print(f"Vercel Project Name: {vercel_project_name}")
    print(f"Target Custom Subdomain: {custom_subdomain}")

    # Step 1: Add subdomain to the project (domains add)
    domain_add_command = [
        "npx", "vercel", "domains", "add",
        custom_subdomain,
        "--scope", "webcoding",
        "--token", vercel_token
    ]
    print(f"\nExecuting: {' '.join(domain_add_command)}")
    run_command(domain_add_command)

    # Step 2: Deploy to Vercel using the project name.
    deploy_command = [
        "npx", "vercel", "deploy",
        "--prod",
        "--name", vercel_project_name,
        "--confirm",
        "--token", vercel_token,
        "--scope", "webcoding"
    ]
    print(f"\nExecuting: {' '.join(deploy_command)}")
    deployment_url = run_command(deploy_command)

    if not deployment_url or not deployment_url.startswith("https://"):
        print(f"Error: Could not reliably determine deployment URL from 'vercel deploy' output. Last output was: {deployment_url}")
        print("\nPlease make sure:")
        print("1. Your Vercel API token has the correct permissions")
        print("2. The domain has been properly configured in Vercel")
        sys.exit(1)
    
    print(f"\nSuccessfully deployed. Unique Deployment URL: {deployment_url}")

    # Step 2: Alias the unique deployment URL to your custom subdomain.
    alias_command = [
        "npx", "vercel", "alias", "set",
        deployment_url,                      # The unique URL from the deploy step
        custom_subdomain,                    # Your desired custom subdomain
        "--token", vercel_token
    ]

    run_command(alias_command)

    print(f"\n--- Deployment and Aliasing Complete ---")
    print(f"Your project should be available at: https://{custom_subdomain}")
    print(f"The specific deployment instance is: {deployment_url}")

if __name__ == "__main__":
    main() 