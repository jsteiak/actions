from collections import defaultdict
from json import loads, dumps
from os import getenv

from actions.teams.const import (
    MEMBERS,
    PROGRESS_LABELS,
    PROJECT_PROGRESS_COLUMNS,
    PROJECT_PROGRESS_COLUMNS_ALT,
    TEAM_PROJECTS,
)
from actions.utils.github import (
    ISSUE_HEADERS,
    PROJECT_HEADERS,
    http_get,
    http_list,
    http_post,
)


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


def get_projects_info(repository_url):
    columns = defaultdict(dict)
    cards = defaultdict(dict)

    for project in http_list(
        f"{repository_url}/projects", headers=PROJECT_HEADERS
    ):
        project_name = project["name"]
        for column in http_list(
            project.get("columns_url"), headers=PROJECT_HEADERS
        ):
            column_name = column["name"].lower()
            columns[project_name][column_name] = {
                "url": column["url"],
                "id": column["id"],
            }
            for card in http_list(
                column.get("cards_url"), headers=PROJECT_HEADERS
            ):
                content_url = card.get("content_url")
                if not content_url:
                    continue
                issue_nr = int(card.get("content_url").split("/")[-1])
                cards[issue_nr][project_name] = {
                    "url": card["url"],
                    "column": column_name,
                }

    return columns, cards


def get_issue_info(issue_url):
    """ Retrieve up-to-date issue information """
    issue = http_get(issue_url, headers=ISSUE_HEADERS)
    progress_label = get_progress_label(issue["labels"])
    if not progress_label:
        print(f"{issue['html_url']} has no progress label.")
        return None

    return {
        "number": issue["number"],
        "teams": {
            MEMBERS[assignee["login"]]
            for assignee in issue["assignees"]
            if assignee["login"] in MEMBERS
        },
        "url": issue["url"],
        "html_url": issue["html_url"],
        "id": issue["id"],
        "progress": progress_label,
    }


def get_progress_column(prj_columns, progress_label):
    if not prj_columns or not progress_label:
        return None

    prj_column_name = PROJECT_PROGRESS_COLUMNS.get(progress_label)
    if prj_column_name in prj_columns:
        return prj_column_name, prj_columns[prj_column_name]

    prj_column_name_alt = PROJECT_PROGRESS_COLUMNS_ALT.get(progress_label)
    if prj_column_name_alt in prj_columns:
        return prj_column_name_alt, prj_columns[prj_column_name_alt]

    return None, None


def fix_progress_column(columns, cards, issue):
    progress_label = issue['progress']

    for prj_name, card_info in cards.get(issue["number"], {}).items():
        prj_col_name, prj_col = get_progress_column(columns[prj_name], progress_label)
        if not prj_col:
            print(f"No match found for {progress_label} in {prj_name}.")
            continue

        if card_info["column"] != prj_col_name:
            url = f"{card_info['url']}/moves"
            data = dumps({"column_id": prj_col["id"], "position": "top"})
            http_post(url, headers=PROJECT_HEADERS, data=data)
            print(f"Moved {issue['html_url']} to {prj_col_name} in {prj_name}.")


def fix_team_assignment(columns, cards, issue):
    progress_label = issue['progress']
    for team in issue["teams"]:
        prj_name = TEAM_PROJECTS.get(team)
        if not prj_name:
            continue

        _, prj_col = get_progress_column(columns.get(prj_name), progress_label)
        if not prj_col:
            print(f"No match found for {progress_label} in {prj_name}.")
            continue

        card = cards.get(issue["number"], {}).get(prj_name)
        if not card:
            url = f"{prj_col['url']}/cards"
            data = dumps({"content_id": issue["id"], "content_type": "Issue"})
            http_post(url, headers=PROJECT_HEADERS, data=data)
            print(f"Assigned {issue['html_url']} to {team}.")


def main():
    context = loads(getenv("GITHUB_CONTEXT"))

    repository_url = context["event"]["repository"]["url"]
    issue_url = context["event"]["issue"]["url"]

    columns, cards = get_projects_info(repository_url)
    issue = get_issue_info(issue_url)

    if issue:
        fix_progress_column(columns, cards, issue)
        fix_team_assignment(columns, cards, issue)

    return 0


if __name__ == "__main__":
    exit(main())
