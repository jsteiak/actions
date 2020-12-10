from json import loads, dumps
from os import getenv
import requests

GITHUB_TOKEN = getenv("GITHUB_TOKEN")

AUTHORIZATION_HEADER = f"token {GITHUB_TOKEN}"
ISSUES_ACCEPT_HEADER = "application/vnd.github.v3.full+json"
PROJECTS_ACCEPT_HEADER = "application/vnd.github.inertia-preview+json"

ISSUE_HEADERS = {
    "accept": ISSUES_ACCEPT_HEADER,
    "authorization": AUTHORIZATION_HEADER,
}

PROJECT_HEADERS = {
    "accept": PROJECTS_ACCEPT_HEADER,
    "authorization": AUTHORIZATION_HEADER,
}


TEAMS = {
    "YNS": [
        "jsteiak",
    ],
}
MEMBERS = {member: team for team, members in TEAMS.items() for member in members}

TEAM_PROJECTS = {
    "istiakog": "YNS",
}

PROGRESS_LABELS = {
    "0 - Backlog": 0,
    "1 - Ready": 1,
    "2 - Working": 2,
    "3 - Complete": 3,
}
PROJECT_COLUMNS = {label: label.split(" - ")[1] for label in PROGRESS_LABELS}


def http_get_one(url, headers):
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def http_get_many(url, headers):
    while url:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        yield from resp.json()
        url = resp.links.get("next", {}).get("url")
    return


def http_post_one(url, headers, data):
    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()


def get_progress_label(labels):
    max_progress = -1
    progress_label = None
    for label in labels:
        name = label["name"]
        progress = PROGRESS_LABELS.get(name, -1)
        if progress > max_progress:
            max_progress = progress
            progress_label = name

    return progress_label


def get_projects(repository_url):
    headers = {
        "accept": PROJECTS_ACCEPT_HEADER,
        "authorization": AUTHORIZATION_HEADER,
    }

    projects = {}
    for project in http_get_many(f"{repository_url}/projects", headers=headers):
        team = TEAM_PROJECTS.get(project.get("name"))
        if team is not None:
            projects[team] = project.get("url")

    return projects


def get_project_info(team_projects_url):
    project_headers = {
        "accept": PROJECTS_ACCEPT_HEADER,
        "authorization": AUTHORIZATION_HEADER,
    }

    columns = {}
    cards = {}

    for team, project_url in team_projects_url.items():
        project = http_get_one(project_url, headers=project_headers)
        for column in http_get_many(
            project.get("columns_url"), headers=project_headers
        ):
            columns[(team, column["name"])] = {
                "url": column["url"],
                "id": column["id"],
            }
            card_url = column.get("cards_url")
            for card in http_get_many(card_url, headers=project_headers):
                content_url = card.get("content_url")
                if not content_url:
                    continue
                issue_nr = int(card.get("content_url").split("/")[-1])
                cards[(team, issue_nr)] = {
                    "url": card["url"],
                    "column": column["name"],
                }

    return columns, cards


def get_issue_info(issue_url):
    issues = {}

    issue = http_get_one(issue_url)

    issue_nr = issue["number"]
    progress_label = get_progress_label(issue["labels"])
    for assignee in issue["assignees"]:
        team = MEMBERS.get(assignee["login"])
        if not team:
            continue

        issues[(team, issue_nr)] = {
            "url": issue["url"],
            "html_url": issue["html_url"],
            "id": issue["id"],
            "column": PROJECT_COLUMNS.get(progress_label),
        }

    return issues


def fix_mismatches(columns, cards, issues):
    for (team, issue_nr), issue_info in issues.items():
        card_info = cards.get((team, issue_nr))
        if not card_info:
            print(f"{issue_info['html_url']} not found in {team}.")
            column_url = columns.get((team, issue_info["column"]), {}).get("url")
            if not column_url:
                print("[ERROR] Column URL not found.")
                continue
            url = f"{column_url}/cards"
            data = dumps({"content_id": issue_info["id"], "content_type": "Issue"})
            http_post_one(url, headers=PROJECT_HEADERS, data=data)
            print(f"Assigned {issue_info['html_url']} to {team}.")
            continue

        if issue_info["column"] != card_info["column"]:
            print(
                f"{issue_info['html_url']} is {issue_info['column']} but "
                f"appears as {card_info['column']} in {team}."
            )

            column_id = columns.get((team, issue_info["column"]), {}).get("id")
            if not column_id:
                print("[ERROR] Column ID not found.")
                continue
            url = f"{card_info['url']}/moves"
            data = dumps({"column_id": column_id, "position": "top"})
            http_post_one(url, headers=PROJECT_HEADERS, data=data)
            print(
                f"Moved {issue_info['html_url']} to {card_info['column']} "
                f"in {team}."
            )


def main():
    context = loads(getenv("GITHUB_CONTEXT"))

    repository_url = context["event"]["repository"]["url"]
    issue_url = context["event"]["issue"]["url"]

    team_projects_url = get_projects(repository_url)
    columns, cards = get_project_info(team_projects_url)
    issues = get_issue_info(issue_url)

    fix_mismatches(columns, cards, issues)

    return 0


if __name__ == "__main__":
    exit(main())
