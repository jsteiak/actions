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
            column_name = column["name"]
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
        "progress": get_progress_label(issue["labels"]),
    }


def fix_mismatches(columns, cards, issue):
    progress_column = PROJECT_PROGRESS_COLUMNS.get(
        issue["progress"]
    ) or PROJECT_PROGRESS_COLUMNS_ALT.get(issue["progress"])

    for project_name, card_info in cards.get(issue["number"], {}).items():
        if card_info["column"] != progress_column:
            print(
                f"{issue['html_url']} is {progress_column} but "
                f"appears as {card_info['column']} in {project_name}."
            )

            column_id = (
                columns.get(project_name, {}).get(progress_column, {}).get("id")
            )
            if not column_id:
                print(f"{progress_column} not found in {project_name}.")
                continue
            url = f"{card_info['url']}/moves"
            data = dumps({"column_id": column_id, "position": "top"})
            http_post(url, headers=PROJECT_HEADERS, data=data)
            print(
                f"Moved {issue['html_url']} to {progress_column} "
                f"in {project_name}."
            )

    for team in issue["teams"]:
        team_project = TEAM_PROJECTS.get(team)
        if not team_project:
            continue

        card = cards.get(issue["number"], {}).get(team_project)
        if not card:
            print(f"{issue['html_url']} not found in {team}.")
            column_url = (
                columns.get(team_project, {})
                .get(progress_column, {})
                .get("url")
            )
            if not column_url:
                print(f"{progress_column} not in found team {team_project}.")
                continue
            url = f"{column_url}/cards"
            data = dumps({"content_id": issue["id"], "content_type": "Issue"})
            http_post(url, headers=PROJECT_HEADERS, data=data)
            print(f"Assigned {issue['html_url']} to {team}.")


def main():
    context = loads(getenv("GITHUB_CONTEXT"))

    repository_url = context["event"]["repository"]["url"]
    issue_url = context["event"]["issue"]["url"]

    columns, cards = get_projects_info(repository_url)
    issues = get_issue_info(issue_url)

    fix_mismatches(columns, cards, issues)

    return 0


if __name__ == "__main__":
    exit(main())
