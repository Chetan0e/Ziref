import os
import sys
import argparse
import getpass
import zipfile
import tempfile
import time
from typing import List, Optional

from packages.cli.config import cli_config
from packages.cli.client import ZirefApiClient, ZirefCliError

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", ".next",
    "dist", "build", "coverage", ".turbo", ".cache",
    ".pytest_cache", "__pycache__"
}

def create_archive_from_dir(source_dir: str) -> str:
    """Packages directory into a temporary ZIP archive, omitting node_modules and version control."""
    temp_zip = os.path.join(tempfile.gettempdir(), f"ziref_deploy_{int(time.time())}.zip")
    with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                if file.endswith((".pyc", ".DS_Store")):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, source_dir)
                zf.write(full_path, rel_path)
    return temp_zip

def cmd_login(args):
    client = ZirefApiClient()
    email = args.email or input("Email: ")
    password = args.password or getpass.getpass("Password: ")
    try:
        data = client.login(email.strip(), password)
        print(f"{GREEN}✓ Successfully authenticated as {data['user']['email']}{RESET}")
    except ZirefCliError as e:
        print(f"{RED}✗ Authentication failed: {e}{RESET}")
        sys.exit(1)

def cmd_whoami(args):
    client = ZirefApiClient()
    try:
        user = client.get_me()
        print(f"{BOLD}Authenticated user:{RESET}")
        print(f"  Name:  {user.get('name')}")
        print(f"  Email: {user.get('email')}")
        print(f"  ID:    {user.get('id')}")
    except ZirefCliError as e:
        print(f"{RED}✗ Not logged in or session expired: {e}{RESET}")
        print(f"Run {CYAN}ziref login{RESET} to authenticate.")
        sys.exit(1)

def cmd_logout(args):
    cli_config.clear()
    print(f"{GREEN}✓ Logged out successfully.{RESET}")

def cmd_list(args):
    client = ZirefApiClient()
    try:
        projects = client.list_projects()
        if not projects:
            print(f"{DIM}No projects found in this account.{RESET}")
            return

        print(f"{BOLD}{'NAME':<24} {'SLUG':<20} {'STATUS':<16} {'URL'}{RESET}")
        print("-" * 80)
        for p in projects:
            status = p.get("status", "UNKNOWN")
            status_color = GREEN if status in ("DEPLOYED", "READY") else (RED if "FAILED" in status else YELLOW)
            active_url = p.get("active_url") or "-"
            print(f"{p['name']:<24} {p['slug']:<20} {status_color}{status:<16}{RESET} {active_url}")
    except ZirefCliError as e:
        print(f"{RED}✗ Failed to list projects: {e}{RESET}")
        sys.exit(1)

def cmd_deploy(args):
    client = ZirefApiClient()
    target_dir = os.path.abspath(args.path or ".")
    if not os.path.isdir(target_dir):
        print(f"{RED}✗ Directory not found: {target_dir}{RESET}")
        sys.exit(1)

    print(f"{CYAN}==> Packaging local workspace at {target_dir}...{RESET}")
    zip_path = create_archive_from_dir(target_dir)

    try:
        # Resolve or create project
        project_id = None
        project_slug = None
        project_name = args.project

        if project_name:
            try:
                p = client.get_project(project_name)
                project_id = p["id"]
                project_slug = p["slug"]
                print(f"Deploying to existing project: {BOLD}{p['name']}{RESET} ({project_slug})")
            except Exception:
                pass

        if not project_id:
            dir_name = os.path.basename(target_dir) or "my-app"
            print(f"Creating new project: {BOLD}{dir_name}{RESET}...")
            p = client.create_project(name=dir_name)
            project_id = p["id"]
            project_slug = p["slug"]
            print(f"{GREEN}✓ Project created with slug: {project_slug}{RESET}")

        # Upload ZIP
        print(f"{CYAN}==> Uploading and analyzing archive...{RESET}")
        upload_res = client.upload_zip(project_id, zip_path)
        upload_id = upload_res["id"]
        analysis = upload_res.get("analysis")
        if analysis:
            print(f"  Detected Framework: {BOLD}{analysis.get('framework')}{RESET} ({analysis.get('language')})")
            print(f"  Package Manager:    {analysis.get('packageManager')}")
            print(f"  Build Command:      {analysis.get('buildCommand')}")

        # Trigger Build
        build_cmd = args.build_command or (analysis.get("buildCommand") if analysis else None)
        out_dir = args.output_dir or (analysis.get("outputDirectory") if analysis else None)
        print(f"{CYAN}==> Triggering isolated container sandbox build...{RESET}")
        build = client.trigger_build(project_id, upload_id, build_cmd, out_dir)
        build_id = build["id"]

        # Stream / Poll build logs
        seen_count = 0
        final_status = None
        while True:
            time.sleep(1)
            b = client.get_build(build_id)
            logs = client.get_build_logs(build_id).get("events", [])
            for event in logs[seen_count:]:
                stage = event.get("stage", "")
                level = event.get("level", "")
                msg = event.get("message", "")
                prefix = f"[{stage.upper()}]" if stage else ""
                if level == "error":
                    print(f"{RED}{prefix} {msg}{RESET}")
                elif level == "warn":
                    print(f"{YELLOW}{prefix} {msg}{RESET}")
                else:
                    print(f"{DIM}{prefix}{RESET} {msg}")
            seen_count = len(logs)

            if b.get("status") in ("BUILT", "FAILED", "CANCELLED"):
                final_status = b.get("status")
                break

        if final_status == "BUILT":
            print(f"\n{GREEN}{BOLD}✓ Build succeeded! Waiting for deployment cutover...{RESET}")
            # Poll for deployment ready
            for _ in range(30):
                time.sleep(1)
                p = client.get_project(project_id)
                if p.get("active_url"):
                    print(f"\n{GREEN}{BOLD}🚀 Successfully deployed!{RESET}")
                    print(f"  Production URL: {CYAN}{BOLD}{p['active_url']}{RESET}")
                    print(f"  Dashboard:      http://localhost:3000/dashboard/projects/{project_id}\n")
                    return
            print(f"{YELLOW}Deployment is active at: http://localhost:8080/sites/{project_slug}/{RESET}")
        else:
            print(f"\n{RED}{BOLD}✗ Build failed.{RESET}")
            diag = b.get("diagnosis")
            if diag:
                print(f"{YELLOW}Diagnosis: {diag.get('summary')}{RESET}")
                print(f"Suggestion: {diag.get('actionable_fix')}")
            sys.exit(1)

    except ZirefCliError as e:
        print(f"{RED}✗ Deployment error: {e}{RESET}")
        sys.exit(1)
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

def cmd_appify(args):
    client = ZirefApiClient()
    try:
        p = client.get_project(args.project)
        project_id = p["id"]
        app_name = args.name or p["name"]
        package_id = args.package or f"com.ziref.{p['slug'].replace('-', '').lower()}"

        print(f"{CYAN}==> Initializing Android application for {p['name']}...{RESET}")
        app = client.create_mobile_app(project_id, app_name, package_id)

        print(f"{CYAN}==> Triggering mobile compilation pipeline...{RESET}")
        mobile_build = client.trigger_mobile_build(app["id"])
        mb_id = mobile_build["id"]

        for _ in range(60):
            time.sleep(1)
            mb = client.get_mobile_build(mb_id)
            if mb.get("status") == "APP_READY":
                print(f"{GREEN}✓ Android APK generated successfully!{RESET}")
                out_apk = args.output or f"app-debug-{p['slug']}.apk"
                print(f"Downloading APK to {BOLD}{out_apk}{RESET}...")
                client.download_apk(mb_id, out_apk)
                print(f"{GREEN}✓ Download complete: {out_apk}{RESET}")
                return
            elif mb.get("status") == "APP_FAILED":
                print(f"{RED}✗ Mobile build failed: {mb.get('error_message')}{RESET}")
                sys.exit(1)

        print(f"{YELLOW}Build still in progress. Check dashboard.{RESET}")

    except ZirefCliError as e:
        print(f"{RED}✗ Appify error: {e}{RESET}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        prog="ziref",
        description="Ziref Developer CLI — Cloud deployments and mobile packaging from your terminal."
    )
    subparsers = parser.add_subparsers(dest="command")

    # login
    p_login = subparsers.add_parser("login", help="Authenticate with your Ziref account")
    p_login.add_argument("--email", help="Account email")
    p_login.add_argument("--password", help="Account password")

    # whoami
    subparsers.add_parser("whoami", help="Display authenticated user information")

    # logout
    subparsers.add_parser("logout", help="Log out from your Ziref session")

    # list
    subparsers.add_parser("list", help="List all projects and deployments")
    subparsers.add_parser("projects", help="Alias for 'list'")

    # deploy
    p_deploy = subparsers.add_parser("deploy", help="Deploy the current directory or specified path")
    p_deploy.add_argument("path", nargs="?", default=".", help="Directory to deploy (default: .)")
    p_deploy.add_argument("--project", "-p", help="Target existing project name or ID")
    p_deploy.add_argument("--build-command", help="Custom build command (e.g. 'npm run build')")
    p_deploy.add_argument("--output-dir", help="Custom output directory (e.g. 'dist')")

    # appify
    p_app = subparsers.add_parser("appify", help="Transform project into a native Android APK")
    p_app.add_argument("project", help="Project ID or slug")
    p_app.add_argument("--name", help="Custom Android App Name")
    p_app.add_argument("--package", help="Custom Android Package ID (e.g. com.myorg.app)")
    p_app.add_argument("--output", "-o", help="Output file path for the .apk file")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "login": cmd_login,
        "whoami": cmd_whoami,
        "logout": cmd_logout,
        "list": cmd_list,
        "projects": cmd_list,
        "deploy": cmd_deploy,
        "appify": cmd_appify
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
