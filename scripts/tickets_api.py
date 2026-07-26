#!/usr/bin/env python3
"""Fetch, search, create, close, and edit GitHub issues via the REST API."""

import argparse
import os
import sys

import requests

API_ROOT = "https://api.github.com"


EXAMPLES = """\
examples:
  # List open issues
  tickets_api.py list owner/repo

  # List all issues (open and closed) with a given label
  tickets_api.py list owner/repo --state all --labels bug

  # Search issue titles/descriptions for text
  tickets_api.py list owner/repo --search "login fails"

  # Close an issue
  tickets_api.py close owner/repo 42

  # Replace an issue's description
  tickets_api.py edit owner/repo 42 --body "Updated description"
  tickets_api.py edit owner/repo 42 --body-file new_description.txt

  # Create a new issue
  tickets_api.py create owner/repo --title "Bug: crash on save" --body "Steps to reproduce..."

  # Show an issue's full description
  tickets_api.py show owner/repo 42

Set GITHUB_TOKEN in the environment to authenticate (required for close/edit/create).
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage GitHub issues for a repo.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list",
        help="List/search issues",
        epilog=(
            "examples:\n"
            "  tickets_api.py list owner/repo\n"
            "  tickets_api.py list owner/repo --state all --labels bug\n"
            '  tickets_api.py list owner/repo --search "login fails"\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    list_parser.add_argument("repo", help="Repository in owner/repo format")
    list_parser.add_argument(
        "--state",
        choices=["open", "closed", "all"],
        default=None,
        help="Issue state to filter by (default: open, or all when --search is used)",
    )
    list_parser.add_argument(
        "--labels",
        help="Comma-separated list of labels to filter by",
    )
    list_parser.add_argument(
        "--search",
        help="Case-insensitive text to search for in issue titles/descriptions",
    )

    show_parser = subparsers.add_parser(
        "show",
        help="Show an issue's full description",
        epilog="examples:\n  tickets_api.py show owner/repo 42\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    show_parser.add_argument("repo", help="Repository in owner/repo format")
    show_parser.add_argument("issue_number", type=int, help="Issue number to show")

    close_parser = subparsers.add_parser(
        "close",
        help="Close an issue",
        epilog="examples:\n  tickets_api.py close owner/repo 42\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    close_parser.add_argument("repo", help="Repository in owner/repo format")
    close_parser.add_argument("issue_number", type=int, help="Issue number to close")

    edit_parser = subparsers.add_parser(
        "edit",
        help="Edit an issue's title and/or description",
        epilog=(
            "examples:\n"
            '  tickets_api.py edit owner/repo 42 --body "Updated description"\n'
            "  tickets_api.py edit owner/repo 42 --body-file new_description.txt\n"
            '  tickets_api.py edit owner/repo 42 --title "New title"\n'
            '  tickets_api.py edit owner/repo 42 --title "New title" --body "New body"\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    edit_parser.add_argument("repo", help="Repository in owner/repo format")
    edit_parser.add_argument("issue_number", type=int, help="Issue number to edit")
    edit_parser.add_argument("--title", help="New issue title")
    edit_body_group = edit_parser.add_mutually_exclusive_group()
    edit_body_group.add_argument("--body", help="New issue description text")
    edit_body_group.add_argument(
        "--body-file", help="Path to a file containing the new issue description"
    )

    create_parser = subparsers.add_parser(
        "create",
        help="Create a new issue",
        epilog=(
            "examples:\n"
            "  tickets_api.py create owner/repo --title \"Bug: crash on save\"\n"
            "  tickets_api.py create owner/repo --title \"Bug: crash on save\" "
            "--body-file description.txt\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    create_parser.add_argument("repo", help="Repository in owner/repo format")
    create_parser.add_argument("--title", required=True, help="Issue title")
    create_body_group = create_parser.add_mutually_exclusive_group()
    create_body_group.add_argument("--body", help="Issue description text")
    create_body_group.add_argument(
        "--body-file", help="Path to a file containing the issue description"
    )

    return parser.parse_args()


def require_token(token):
    if not token:
        print(
            "Error: GITHUB_TOKEN must be set to modify issues.",
            file=sys.stderr,
        )
        sys.exit(1)


def auth_headers(token):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        print(
            "Warning: GITHUB_TOKEN not set, using unauthenticated requests "
            "(rate limit: 60/hr)",
            file=sys.stderr,
        )
    return headers


def check_response(response, url):
    if response.status_code // 100 != 2:
        print(
            f"Error: GitHub API returned {response.status_code} for {url}\n"
            f"{response.text}",
            file=sys.stderr,
        )
        sys.exit(1)


def fetch_issues(repo, state, labels, token):
    headers = auth_headers(token)

    params = {"state": state, "per_page": 100}
    if labels:
        params["labels"] = labels

    url = f"{API_ROOT}/repos/{repo}/issues"
    issues = []
    while url:
        response = requests.get(url, headers=headers, params=params)
        check_response(response, url)

        for item in response.json():
            if "pull_request" not in item:
                issues.append(item)

        url = response.links.get("next", {}).get("url")
        params = None  # pagination URL already includes query params

    return issues


def get_issue(repo, issue_number, token):
    headers = auth_headers(token)
    url = f"{API_ROOT}/repos/{repo}/issues/{issue_number}"
    response = requests.get(url, headers=headers)
    check_response(response, url)
    return response.json()


def close_issue(repo, issue_number, token):
    require_token(token)
    headers = auth_headers(token)
    url = f"{API_ROOT}/repos/{repo}/issues/{issue_number}"
    response = requests.patch(url, headers=headers, json={"state": "closed"})
    check_response(response, url)
    return response.json()


def edit_issue(repo, issue_number, title, body, token):
    require_token(token)
    headers = auth_headers(token)
    url = f"{API_ROOT}/repos/{repo}/issues/{issue_number}"
    payload = {}
    if title is not None:
        payload["title"] = title
    if body is not None:
        payload["body"] = body
    response = requests.patch(url, headers=headers, json=payload)
    check_response(response, url)
    return response.json()


def create_issue(repo, title, body, token):
    require_token(token)
    headers = auth_headers(token)
    url = f"{API_ROOT}/repos/{repo}/issues"
    payload = {"title": title}
    if body:
        payload["body"] = body
    response = requests.post(url, headers=headers, json=payload)
    check_response(response, url)
    return response.json()


def matches_search(issue, query):
    query = query.lower()
    if query in issue["title"].lower():
        return True
    body = issue.get("body") or ""
    return query in body.lower()


def snippet(text, query, context=40):
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return ""
    start = max(0, idx - context)
    end = min(len(text), idx + len(query) + context)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def run_list(args, token):
    state = args.state or ("all" if args.search else "open")
    issues = fetch_issues(args.repo, state, args.labels, token)

    if args.search:
        issues = [issue for issue in issues if matches_search(issue, args.search)]

    for issue in issues:
        print(f"#{issue['number']}  {issue['title']}  [{issue['state']}]  {issue['html_url']}")
        if args.search:
            body = issue.get("body") or ""
            match_text = snippet(body, args.search) or snippet(issue["title"], args.search)
            if match_text:
                print(f"    {match_text}")

    print(f"\n{len(issues)} issue(s) found.", file=sys.stderr)


def run_show(args, token):
    issue = get_issue(args.repo, args.issue_number, token)
    print(f"#{issue['number']}  {issue['title']}  [{issue['state']}]  {issue['html_url']}")
    print()
    print(issue.get("body") or "(no description)")


def run_close(args, token):
    issue = close_issue(args.repo, args.issue_number, token)
    print(f"Closed #{issue['number']}  {issue['title']}  {issue['html_url']}")


def run_edit(args, token):
    body = args.body
    if args.body_file:
        with open(args.body_file) as f:
            body = f.read()
    if args.title is None and body is None:
        print("Error: provide --title, --body, or --body-file", file=sys.stderr)
        sys.exit(1)
    issue = edit_issue(args.repo, args.issue_number, args.title, body, token)
    print(f"Updated #{issue['number']}  {issue['title']}  {issue['html_url']}")


def run_create(args, token):
    body = args.body
    if args.body_file:
        with open(args.body_file) as f:
            body = f.read()
    issue = create_issue(args.repo, args.title, body, token)
    print(f"Created #{issue['number']}  {issue['title']}  {issue['html_url']}")


def main():
    args = parse_args()
    token = os.environ.get("GITHUB_TOKEN")

    if args.command == "list":
        run_list(args, token)
    elif args.command == "show":
        run_show(args, token)
    elif args.command == "close":
        run_close(args, token)
    elif args.command == "edit":
        run_edit(args, token)
    elif args.command == "create":
        run_create(args, token)


if __name__ == "__main__":
    main()
